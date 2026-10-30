"""$2M contract campaign analysis. Follows CLAUDE.md and briefs/2m-campaign.md.

Run from the repo root:  python3 runs/telco/analysis.py
Reads data/raw/telco_v2.csv (never changes it). Writes every deliverable to runs/telco/.
If a stop-and-ask rule fires, the script stops before it writes deliverables. Use --force to write them anyway.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

RAW = Path("data/raw/telco_v2.csv")
OUT = Path("runs/telco")
COST = 2_000_000          # assumption: campaign cost, set by the VP of Marketing (case)
HORIZON = 12              # assumption: months, set by the user
SWITCH = {"low": 0.05, "mid": 0.10, "high": 0.20}   # assumption: set by the user
BIG_CHARGE = 200          # normal MonthlyCharges max is 118.75; flagged values start at 1,870
TOLERANCE = 0.10          # assumption: set by the analyst for the charges check
BANDS = [-1, 12, 24, 48, 72]
BAND_LABELS = ["0-12", "13-24", "25-48", "49-72"]
N_BOOT = 200
SEED = 42

GRAY, ACCENT, RED = "#B0B0B0", "#1F5FAD", "#C0392B"


# ---------- cleaning ----------
def clean(raw, keep_churn):
    """Return one cleaned dataset and its log rows. keep_churn: which duplicate row to keep ("Yes" or "No")."""
    df = raw.copy()
    df["row_number"] = np.arange(2, len(df) + 2)   # line number in the CSV file (header is line 1)
    log = []

    # 1. Duplicate customerIDs: keep the row with Churn == keep_churn
    dup = df["customerID"].duplicated(keep=False)
    drop = df[dup & (df["Churn"] != keep_churn)]
    for _, r in drop.iterrows():
        log.append(("duplicate", r.row_number, r.customerID, "row removed",
                    f"customerID has 2 rows with different Churn; kept the Churn = {keep_churn} row"))
    df = df.drop(drop.index)

    # 2. MonthlyCharges 100 times too large: check value / 100 against TotalCharges / tenure
    tc = pd.to_numeric(df["TotalCharges"], errors="coerce")
    big = df["MonthlyCharges"] > BIG_CHARGE
    ratio = (df["MonthlyCharges"] / 100) / (tc / df["tenure"])
    match = big & ((ratio - 1).abs() <= TOLERANCE)
    fail = big & ~match
    for i in df.index[match]:
        r = df.loc[i]
        log.append(("MonthlyCharges", r.row_number, r.customerID, f"{r.MonthlyCharges:g} -> {r.MonthlyCharges / 100:g}",
                    f"value / 100 is within {TOLERANCE:.0%} of TotalCharges / tenure (ratio {ratio[i]:.3f})"))
    for i in df.index[fail]:
        r = df.loc[i]
        log.append(("MonthlyCharges", r.row_number, r.customerID, "row removed",
                    f"value / 100 is not within {TOLERANCE:.0%} of TotalCharges / tenure (ratio {ratio[i]:.3f}); "
                    "user decided to exclude these rows"))
    df.loc[match, "MonthlyCharges"] = df.loc[match, "MonthlyCharges"] / 100
    df = df.drop(df.index[fail])

    # 3. Blank TotalCharges with tenure 0: set to 0
    tc = pd.to_numeric(df["TotalCharges"], errors="coerce")
    blank = tc.isna()
    for _, r in df[blank].iterrows():
        log.append(("TotalCharges", r.row_number, r.customerID, "blank -> 0", f"tenure is {r.tenure}; no charges yet"))
    df["TotalCharges"] = tc.fillna(0.0)

    # 4. Leakage column: filled only for churners
    df = df.drop(columns=["RetentionOfferAccepted"])

    df["churn"] = (df["Churn"] == "Yes").astype(int)
    df["tenure_band"] = pd.cut(df["tenure"], BANDS, labels=BAND_LABELS)
    log = pd.DataFrame(log, columns=["issue", "csv_line", "customerID", "change", "reason"])
    return df, log, int(fail.sum())


# ---------- analysis ----------
FORMULA = ("churn ~ C(Contract, Treatment('One year')) + tenure + C(InternetService) + C(PaymentMethod)")


def adjusted_gap(df):
    """Gap after controls: mean over month-to-month customers of P(churn | MTM) - P(churn | 1-year)."""
    model = smf.logit(FORMULA, data=df).fit(disp=0)
    mtm = df[df["Contract"] == "Month-to-month"]
    p_mtm = model.predict(mtm)
    p_one = model.predict(mtm.assign(Contract="One year"))
    return float((p_mtm - p_one).mean()), model


def analyse(df, boot=True):
    res = {}
    by_contract = df.groupby("Contract")["churn"].agg(customers="size", churned="sum", churn_rate="mean")
    res["by_contract"] = by_contract
    res["raw_gap"] = by_contract.loc["Month-to-month", "churn_rate"] - by_contract.loc["One year", "churn_rate"]

    band = (df[df["Contract"].isin(["Month-to-month", "One year"])]
            .groupby(["tenure_band", "Contract"], observed=True)["churn"].agg(["size", "mean"]).unstack())
    band.columns = [f"{a}_{b}" for a, b in band.columns]
    band["gap"] = band["mean_Month-to-month"] - band["mean_One year"]
    res["by_band"] = band

    res["adj_gap"], res["model"] = adjusted_gap(df)
    if boot:
        rng = np.random.default_rng(SEED)
        draws = [adjusted_gap(df.sample(len(df), replace=True, random_state=rng.integers(1e9)))[0]
                 for _ in range(N_BOOT)]
        res["adj_ci"] = (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)))

    mtm = df[df["Contract"] == "Month-to-month"]
    res["mtm_n"] = len(mtm)
    res["mtm_rev_sum"] = float(mtm["MonthlyCharges"].sum())
    res["mtm_rev_avg"] = float(mtm["MonthlyCharges"].mean())

    effect = {"low": res["adj_gap"] / 2, "mid": res["adj_gap"], "high": res["raw_gap"]}
    rows = []
    for k in ["low", "mid", "high"]:
        saved = res["mtm_n"] * SWITCH[k] * effect[k] * res["mtm_rev_avg"] * HORIZON
        rows.append({"case": k, "switch_rate": SWITCH[k], "churn_effect": effect[k],
                     "customers_switched": res["mtm_n"] * SWITCH[k],
                     "customers_saved": res["mtm_n"] * SWITCH[k] * effect[k],
                     "revenue_saved": saved, "net_value": saved - COST})
    res["value"] = pd.DataFrame(rows).set_index("case")
    v = res["value"]["net_value"]
    res["decision"] = "fund" if v["low"] > 0 else ("do_not_fund" if v["high"] < 0 else "test_first")
    # Revenue saved needed to break even, shown as churn effect at mid switch rate
    res["breakeven_effect_mid_switch"] = COST / (res["mtm_n"] * SWITCH["mid"] * res["mtm_rev_avg"] * HORIZON)
    res["breakeven_switch_high_effect"] = COST / (res["mtm_n"] * res["raw_gap"] * res["mtm_rev_avg"] * HORIZON)
    return res


DRIVERS = {  # variable -> (group compared with the rest, label)
    "Contract": (lambda d: d["Contract"] == "Month-to-month", "Month-to-month"),
    "tenure": (lambda d: d["tenure"] <= 12, "tenure 0-12 months"),
    "InternetService": (lambda d: d["InternetService"] == "Fiber optic", "Fiber optic"),
    "PaymentMethod": (lambda d: d["PaymentMethod"] == "Electronic check", "Electronic check"),
    "PaperlessBilling": (lambda d: d["PaperlessBilling"] == "Yes", "Paperless billing = Yes"),
    "SeniorCitizen": (lambda d: d["SeniorCitizen"] == 1, "SeniorCitizen = 1"),
    "LoyaltyAppUser": (lambda d: d["LoyaltyAppUser"] == "Yes", "LoyaltyAppUser = Yes"),
}


def direction(diff, eps=0.005):
    return "higher" if diff > eps else ("lower" if diff < -eps else "none")


def drivers(df):
    rows = []
    for var, (fn, label) in DRIVERS.items():
        g = fn(df)
        overall = df.loc[g, "churn"].mean() - df.loc[~g, "churn"].mean()
        within, within_dirs = {}, []
        if var != "Contract":
            for c, sub in df.groupby("Contract"):
                gs = fn(sub)
                if gs.sum() >= 30 and (~gs).sum() >= 30:
                    within[c] = sub.loc[gs, "churn"].mean() - sub.loc[~gs, "churn"].mean()
                    within_dirs.append(direction(within[c]))
            wd = within_dirs[0] if len(set(within_dirs)) == 1 else "mixed"
        else:
            wd = "not_checked"
        rows.append({"variable": var, "group": label, "n_group": int(g.sum()),
                     "rate_group": df.loc[g, "churn"].mean(), "rate_rest": df.loc[~g, "churn"].mean(),
                     "diff_overall": overall, "direction_overall": direction(overall),
                     "within": within, "direction_within_contract": wd})
    return rows


# ---------- helpers for writing ----------
def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def pp(x, d=1):
    return f"{x * 100:.{d}f} pp"


def money(x):
    s = f"${abs(x):,.0f}"
    return f"-{s}" if x < 0 else s


def md_table(df, cols=None):
    cols = cols or list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, r in df[cols].iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


# ---------- charts ----------
def style(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(colors="#444")


def chart_contract(res, path):
    bc = res["by_contract"].loc[["Month-to-month", "One year", "Two year"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [ACCENT, GRAY, GRAY]
    bars = ax.bar(bc.index, bc["churn_rate"] * 100, color=colors)
    for b, (_, r) in zip(bars, bc.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.8,
                f"{r.churn_rate * 100:.1f}%\n(n={int(r.customers):,})", ha="center", fontsize=9, color="#333")
    ax.set_title(f"Month-to-month customers churn {res['raw_gap'] * 100:.1f} points more than 1-year customers",
                 fontsize=11, loc="left")
    ax.set_ylabel("Churn rate (%)")
    ax.set_ylim(0, bc["churn_rate"].max() * 100 + 12)
    style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_bands(res, path):
    b = res["by_band"]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(b.index.astype(str), b["gap"] * 100, color=ACCENT)
    for bar, (_, r) in zip(bars, b.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6, f"{r.gap * 100:.1f}",
                ha="center", fontsize=9, color="#333")
    ax.axhline(res["raw_gap"] * 100, color=GRAY, ls="--", lw=1)
    ax.text(len(b) - 0.5, res["raw_gap"] * 100 + 0.8, f"raw gap {res['raw_gap'] * 100:.1f}",
            ha="right", fontsize=8, color="#777")
    lo, hi = b["gap"].min() * 100, b["gap"].max() * 100
    ax.set_title(f"The contract gap remains in every tenure band ({lo:.1f} to {hi:.1f} points)",
                 fontsize=11, loc="left")
    ax.set_xlabel("Tenure band (months)")
    ax.set_ylabel("Churn gap, month-to-month minus 1-year (points)")
    ax.set_ylim(0, max(hi, res["raw_gap"] * 100) + 8)
    style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_value(res, path):
    v = res["value"]
    fig, ax = plt.subplots(figsize=(7, 4))
    vals = v["net_value"] / 1e6
    bars = ax.bar([c.capitalize() for c in v.index], vals, color=[RED if x < 0 else ACCENT for x in vals])
    for bar, x in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, x - 0.08, (f"-\\${-x:.2f}M" if x < 0 else f"\\${x:.2f}M"), ha="center", va="top",
                fontsize=9, color="#333")
    ax.axhline(0, color="#333", lw=1)
    ax.text(2.45, 0.05, "\\$0 (break-even)", ha="right", fontsize=8, color="#333")
    ax.set_title(f"Net value is below \\$0 in all three cases (high: -\\${-vals['high']:.2f}M)"
                 if vals.max() < 0 else "Net value range compared with $0", fontsize=11, loc="left")
    ax.set_ylabel("Net value over 12 months ($M)")
    ax.set_ylim(min(vals.min() - 0.4, -0.3), max(vals.max(), 0) + 0.3)
    style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------- main ----------
def main():
    force = "--force" in sys.argv
    raw = pd.read_csv(RAW)

    # Profile (CLAUDE.md)
    tc_num = pd.to_numeric(raw["TotalCharges"], errors="coerce")
    profile = {
        "rows": len(raw), "unique_ids": raw["customerID"].nunique(),
        "dup_ids": int(raw["customerID"].duplicated(keep=False).sum() // 2),
        "dup_ids_churn_differs": int((raw[raw["customerID"].duplicated(keep=False)]
                                      .groupby("customerID")["Churn"].nunique() == 2).sum()),
        "big_charges": int((raw["MonthlyCharges"] > BIG_CHARGE).sum()),
        "big_min": raw.loc[raw["MonthlyCharges"] > BIG_CHARGE, "MonthlyCharges"].min(),
        "big_max": raw.loc[raw["MonthlyCharges"] > BIG_CHARGE, "MonthlyCharges"].max(),
        "blank_tc": int(tc_num.isna().sum()),
        "retention_filled": int(raw["RetentionOfferAccepted"].notna().sum()),
        "retention_filled_churners": int((raw["RetentionOfferAccepted"].notna() & (raw["Churn"] == "Yes")).sum()),
    }
    col_profile = pd.DataFrame({
        "type": raw.dtypes.astype(str),
        "blanks": raw.isna().sum() + (raw.astype(str).apply(lambda s: s.str.strip()) == "").sum(),
        "min": [raw[c].min() if raw[c].dtype != object else "" for c in raw.columns],
        "max": [raw[c].max() if raw[c].dtype != object else "" for c in raw.columns],
    })
    col_profile.loc["TotalCharges", ["min", "max"]] = [tc_num.min(), tc_num.max()]

    main_df, main_log, n_fail = clean(raw, "Yes")
    alt_df, alt_log, _ = clean(raw, "No")
    main_df.to_csv(OUT / "clean_main_keep_yes.csv", index=False)
    alt_df.to_csv(OUT / "clean_alt_keep_no.csv", index=False)

    m = analyse(main_df)
    a = analyse(alt_df)

    # Stop-and-ask rules (brief section 5)
    stops = []
    if m["decision"] != a["decision"]:
        stops.append(f"Decision differs: main run {m['decision']}, second run {a['decision']}")
    for name, r in [("main", m), ("second", a)]:
        if r["adj_gap"] <= 0:
            stops.append(f"{name} run: gap after controls reverses ({pp(r['adj_gap'])})")
        elif r["adj_gap"] < r["raw_gap"] / 2:
            stops.append(f"{name} run: gap after controls {pp(r['adj_gap'])} is less than half the raw gap {pp(r['raw_gap'])}")

    print(f"Rows: raw {len(raw):,}; main {len(main_df):,}; second {len(alt_df):,}")
    for name, r in [("MAIN (keep Yes)", m), ("SECOND (keep No)", a)]:
        print(f"\n{name}: raw gap {pp(r['raw_gap'])}, gap after controls {pp(r['adj_gap'])} "
              f"(95% CI {pp(r['adj_ci'][0])} to {pp(r['adj_ci'][1])})")
        print(f"  MTM customers {r['mtm_n']:,}; monthly revenue {money(r['mtm_rev_sum'])}; avg {money(r['mtm_rev_avg'])}")
        print(r["value"].round(4).to_string())
        print(f"  decision: {r['decision']}")
    if stops:
        print("\nSTOP AND ASK THE USER:\n- " + "\n- ".join(stops))
        if not force:
            sys.exit(1)

    drv = drivers(main_df)
    chart_contract(m, OUT / "chart1_churn_by_contract.png")
    chart_bands(m, OUT / "chart2_gap_by_tenure_band.png")
    chart_value(m, OUT / "chart3_net_value.png")

    write_findings(m, drv, main_log, raw)
    write_cleaning_log(raw, main_df, alt_df, main_log, alt_log)
    write_report(raw, profile, col_profile, main_df, alt_df, m, a, drv, main_log, n_fail)
    print("\nWrote deliverables to", OUT)


def write_findings(m, drv, log, raw):
    counts = log["issue"].value_counts()
    big = log[log["issue"] == "MonthlyCharges"]
    n_div = int((big["change"] != "row removed").sum())
    n_rm = int((big["change"] == "row removed").sum())
    findings = {
        "recommendation": m["decision"],
        "data_issues": [
            {"column": "customerID", "issue": f"{int(counts['duplicate'])} customerIDs have 2 rows each with different Churn values",
             "rows_affected": int(counts["duplicate"]) * 2,
             "action": "Main run kept the Churn = Yes row; second run kept the Churn = No row; both runs reported"},
            {"column": "MonthlyCharges", "issue": f"{n_div + n_rm} values are 100 times too large (1,870 to 11,515)",
             "rows_affected": n_div + n_rm,
             "action": f"Divided {n_div} by 100 where value / 100 is within 10% of TotalCharges / tenure; "
                       f"removed {n_rm} rows that failed the check (user decision)"},
            {"column": "TotalCharges", "issue": "Blank for customers with tenure 0",
             "rows_affected": int(counts["TotalCharges"]), "action": "Set to 0"},
            {"column": "RetentionOfferAccepted", "issue": "Filled only for churners (leaks the churn result)",
             "rows_affected": int(raw["RetentionOfferAccepted"].notna().sum()), "action": "Column excluded from the analysis"},
        ],
        "drivers": [{"variable": d["variable"], "direction_overall": d["direction_overall"],
                     "direction_within_contract": d["direction_within_contract"]} for d in drv],
    }
    (OUT / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")


def write_cleaning_log(raw, main_df, alt_df, main_log, alt_log):
    def summary(log):
        return log.groupby(["issue", "change"]).size().reset_index(name="rows") \
                  .assign(change=lambda d: d["change"].where(~d["change"].str.contains("->") | d["change"].str.startswith("blank"),
                                                             "divided by 100")) \
                  .groupby(["issue", "change"], as_index=False)["rows"].sum()
    alt_dups = alt_log[alt_log["issue"] == "duplicate"]
    text = f"""# Cleaning log

Source: `data/raw/telco_v2.csv` ({len(raw):,} rows). The raw file is not changed.
Code: `runs/telco/analysis.py`. `csv_line` is the line number in the raw file (line 1 is the header).

## Summary
| Run | Rows before | Rows after | Cleaned file |
| --- | --- | --- | --- |
| Main (keep the Churn = Yes duplicate row) | {len(raw):,} | {len(main_df):,} | `clean_main_keep_yes.csv` |
| Second (keep the Churn = No duplicate row) | {len(raw):,} | {len(alt_df):,} | `clean_alt_keep_no.csv` |

Main run changes:

{md_table(summary(main_log))}

Column change (all rows, both runs): `RetentionOfferAccepted` removed. It is filled only for churners, so it leaks the churn result.

## Decisions
- **Duplicates:** each of the 211 duplicate IDs has one Churn = Yes row and one Churn = No row. Nothing in the data says which row is correct. The main run keeps the Yes row (set by the user). The second run keeps the No row, to show how much the choice matters.
- **MonthlyCharges:** the user set the rule: divide by 100 only when value / 100 matches TotalCharges / tenure. "Match" means within 10% (an assumption set by the analyst). 9 rows failed. The user decided to remove them. Note: 5.5% of normal rows are also more than 10% from TotalCharges / tenure, so the 9 rows may be correct after division.
- **TotalCharges:** 11 blanks, all with tenure 0. Set to 0, because a new customer has no charges yet.

## Every changed row: main run
{md_table(main_log)}

## Rows removed in the second run (duplicates only; other changes are the same as the main run)
{md_table(alt_dups)}
"""
    (OUT / "cleaning_log.md").write_text(text)


def write_report(raw, profile, col_profile, main_df, alt_df, m, a, drv, main_log, n_fail):
    v, va = m["value"], a["value"]
    bc = m["by_contract"].loc[["Month-to-month", "One year", "Two year"]]
    lo_ci, hi_ci = m["adj_ci"]
    n_div = int(((main_log["issue"] == "MonthlyCharges") & (main_log["change"] != "row removed")).sum())
    n_dup = int((main_log["issue"] == "duplicate").sum())
    n_tc = int((main_log["issue"] == "TotalCharges").sum())
    gap_kept = m["adj_gap"] / m["raw_gap"]
    rec_word = {"fund": "Fund", "do_not_fund": "Do not fund", "test_first": "Test first"}[m["decision"]]
    loyalty = next(d for d in drv if d["variable"] == "LoyaltyAppUser")
    loyalty_mtm_share = (main_df.loc[main_df["LoyaltyAppUser"] == "Yes", "Contract"] == "Month-to-month").mean()

    lt = pd.crosstab(main_df["Contract"], main_df["LoyaltyAppUser"])
    loyalty_tbl = pd.DataFrame({
        "Contract": lt.index,
        "App users (data)": [f"{x:,}" for x in lt["Yes"]],
        "Share of app users": [pct(x) for x in lt["Yes"] / lt["Yes"].sum()],
        "Non-users (data)": [f"{x:,}" for x in lt["No"]],
        "Share of non-users": [pct(x) for x in lt["No"] / lt["No"].sum()]})

    contract_tbl = pd.DataFrame({
        "Contract": bc.index, "Customers (data)": [f"{x:,}" for x in bc["customers"]],
        "Churned (data)": [f"{x:,}" for x in bc["churned"]],
        "Churn rate (derived)": [pct(x) for x in bc["churn_rate"]]})
    b = m["by_band"]
    band_tbl = pd.DataFrame({
        "Tenure band (months)": b.index.astype(str),
        "MTM customers (data)": [f"{int(x):,}" for x in b["size_Month-to-month"]],
        "MTM churn (derived: churned / customers)": [pct(x) for x in b["mean_Month-to-month"]],
        "1-year customers (data)": [f"{int(x):,}" for x in b["size_One year"]],
        "1-year churn (derived: churned / customers)": [pct(x) for x in b["mean_One year"]],
        "Gap (derived: MTM churn − 1-year churn)": [pp(x) for x in b["gap"]]})

    def value_tbl(r):
        t = r["value"]
        return pd.DataFrame({
            "Case": t.index, "Switch rate (assumption)": [pct(x, 0) for x in t["switch_rate"]],
            "Churn effect (assumption, from the gaps)": [pp(x) for x in t["churn_effect"]],
            "Customers switched (derived: MTM customers × switch rate)": [f"{x:,.0f}" for x in t["customers_switched"]],
            "Customers saved (derived: switched × churn effect)": [f"{x:,.0f}" for x in t["customers_saved"]],
            "Revenue saved, 12 mo (derived: saved × average charge × 12)": [money(x) for x in t["revenue_saved"]],
            "Net value (derived: revenue saved − $2M)": [money(x) for x in t["net_value"]]})

    both_tbl = pd.DataFrame({
        "Result": ["Customers (data)", "Raw gap (derived)", "Gap after controls (derived)", "MTM customers (data)",
                   "MTM monthly revenue (derived: sum)", "Net value: low (derived)", "Net value: mid (derived)",
                   "Net value: high (derived)", "Decision (derived: decision rule)"],
        "Main run (keep Yes)": [f"{len(main_df):,}", pp(m["raw_gap"]), pp(m["adj_gap"]), f"{m['mtm_n']:,}",
                                money(m["mtm_rev_sum"]), money(v.loc["low", "net_value"]), money(v.loc["mid", "net_value"]),
                                money(v.loc["high", "net_value"]), m["decision"]],
        "Second run (keep No)": [f"{len(alt_df):,}", pp(a["raw_gap"]), pp(a["adj_gap"]), f"{a['mtm_n']:,}",
                                 money(a["mtm_rev_sum"]), money(va.loc["low", "net_value"]), money(va.loc["mid", "net_value"]),
                                 money(va.loc["high", "net_value"]), a["decision"]]})

    drv_tbl = pd.DataFrame({
        "Variable": [d["variable"] for d in drv], "Group compared with the rest": [d["group"] for d in drv],
        "Group n (data)": [f"{d['n_group']:,}" for d in drv], "Group churn (derived)": [pct(d["rate_group"]) for d in drv],
        "Rest churn (derived)": [pct(d["rate_rest"]) for d in drv], "Overall (derived)": [d["direction_overall"] for d in drv],
        "Within each contract (derived)": [d["direction_within_contract"] for d in drv]})

    coefs = m["model"].summary2().tables[1][["Coef.", "Std.Err.", "P>|z|"]].round(4)
    coefs.insert(0, "Term", coefs.index)

    dictionary = [
        ("customerID", "Customer ID. One ID = one customer", "text"),
        ("gender", "Customer gender", "text"), ("SeniorCitizen", "1 = senior citizen (age limit unknown)", "integer 0/1"),
        ("Partner", "Has a partner", "Yes/No"), ("Dependents", "Has dependents", "Yes/No"),
        ("tenure", "Months as a customer", "integer"), ("PhoneService", "Has phone service", "Yes/No"),
        ("MultipleLines", "Has more than one phone line", "text"),
        ("InternetService", "Internet type: DSL, Fiber optic, No", "text"),
        ("OnlineSecurity", "Has online security add-on", "text"), ("OnlineBackup", "Has online backup add-on", "text"),
        ("DeviceProtection", "Has device protection add-on", "text"), ("TechSupport", "Has tech support add-on", "text"),
        ("StreamingTV", "Has streaming TV", "text"), ("StreamingMovies", "Has streaming movies", "text"),
        ("Contract", "Contract type: Month-to-month, One year, Two year", "text"),
        ("PaperlessBilling", "Gets paperless bills", "Yes/No"), ("PaymentMethod", "How the customer pays", "text"),
        ("MonthlyCharges", "Current monthly bill ($)", "number"),
        ("TotalCharges", "Total billed to date ($). Stored as text in the raw file", "number (text in raw)"),
        ("Churn", "Yes = the customer left in the last month", "Yes/No"),
        ("LoyaltyAppUser", "Uses the loyalty app", "Yes/No"),
        ("RetentionOfferAccepted", "Accepted a retention offer. Filled only for churners. Excluded", "Yes/No/blank"),
    ]
    dict_tbl = pd.DataFrame(dictionary, columns=["Column", "Meaning", "Type"])
    prof = col_profile.reset_index().rename(columns={"index": "Column", "type": "Raw type", "blanks": "Blanks"})
    prof["min"] = prof["min"].astype(str).replace("nan", "")
    prof["max"] = prof["max"].astype(str).replace("nan", "")
    prof = prof.rename(columns={"min": "Min", "max": "Max"})

    text = f"""# $2M contract campaign: recommendation

## 1. Summary

**Recommendation: {rec_word} (`{m['decision']}`).** Even with the most favorable assumptions, the campaign saves less revenue than it costs.

**What we found**
- Month-to-month customers churn more than 1-year customers: {pct(bc.loc['Month-to-month', 'churn_rate'])} vs {pct(bc.loc['One year', 'churn_rate'])} (**derived**: churned / customers). The raw gap is {pp(m['raw_gap'])} (**derived**).
- The gap remains after controls for tenure, internet type, and payment method: {pp(m['adj_gap'])} (**derived**; 95% range {pp(lo_ci)} to {pp(hi_ci)}, **derived** by bootstrap). This is {gap_kept:.0%} of the raw gap (**derived**: {pp(m['adj_gap'])} / {pp(m['raw_gap'])}). The gap is positive in every tenure band.
- There are {m['mtm_n']:,} month-to-month customers (**data**). They pay {money(m['mtm_rev_sum'])} per month in total (**derived**: sum of `MonthlyCharges`), or ${m['mtm_rev_avg']:.2f} on average (**derived**: total / customers).
- Net value over 12 months is {money(v.loc['low', 'net_value'])} (low), {money(v.loc['mid', 'net_value'])} (mid), and {money(v.loc['high', 'net_value'])} (high) (**derived**). The high case is below $0, so the decision rule says `do_not_fund`.

**How sure we are:** high for the decision, medium for the size of the gap. The high case uses the largest values for every assumption and still loses {money(-v.loc['high', 'net_value'])} (**derived**). To break even at a 10% switch rate, the campaign must cut churn by {pp(m['breakeven_effect_mid_switch'], 0)} for each switched customer (**derived**). That is not possible, because a churn rate cannot fall by more than 100 points. The data is observational, so the gap is "associated with" contract type. It may not be caused by it.

**Value range:** net value from {money(v.loc['low', 'net_value'])} to {money(v.loc['high', 'net_value'])} (**derived**). Both duplicate runs give `{a['decision']}` (second run: {money(va.loc['low', 'net_value'])} to {money(va.loc['high', 'net_value'])}, **derived**).

**Data issues:** {profile['dup_ids']} duplicate IDs with conflicting Churn (two runs). {profile['big_charges']} `MonthlyCharges` values 100 times too large ({n_div} fixed, {n_fail} rows removed by user decision). {profile['blank_tc']} blank `TotalCharges` set to 0. `RetentionOfferAccepted` excluded (leakage). All counts are **data**.

**Risks**
- The gap after controls is {gap_kept:.0%} of the raw gap (second run: {a['adj_gap'] / a['raw_gap']:.0%}; **derived**: gap after controls / raw gap). This fired a stop-and-ask rule in the brief. The user decided to continue, because no gap size in the range changes the decision.
- Other variables may explain part of the gap. Example: {pct(loyalty_mtm_share, 0)} of loyalty app users are month-to-month (**derived**; see "Loyalty app users by contract" in the Appendix). We did not control for this column. App users churn more overall, but less than non-users within each contract type.
- Customers who accept an offer may be the ones least likely to churn. Then the real churn effect is smaller than our estimates.
- The model counts only 12 months of revenue from saved customers. It ignores campaign effects on customers who do not switch.

**Next step:** do not fund the $2M campaign. If the business still wants contract migration, test a small, low-cost offer on a random sample of month-to-month customers. Measure the switch rate and churn against a control group.

## 2. Charts

![Month-to-month customers churn more than 1-year customers](chart1_churn_by_contract.png)

Month-to-month customers churn at {pct(bc.loc['Month-to-month', 'churn_rate'])}, compared with {pct(bc.loc['One year', 'churn_rate'])} for 1-year and {pct(bc.loc['Two year', 'churn_rate'])} for 2-year customers (**derived**: churned / customers).

![The contract gap remains in every tenure band](chart2_gap_by_tenure_band.png)

In every tenure band, month-to-month customers churn more than 1-year customers, so tenure alone does not explain the gap.

![Net value is below $0 in all three cases](chart3_net_value.png)

All three net values are below the $0 break-even line, so the campaign does not pay back its $2M cost in 12 months.

## 3. Appendix

### Data source and size
- File: `data/raw/telco_v2.csv`. A teaching version of the IBM Telco Customer Churn sample (fictional company).
- Raw: {profile['rows']:,} rows, {profile['unique_ids']:,} unique `customerID`, {raw.shape[1]} columns (**data**).
- After cleaning: {len(main_df):,} rows in the main run, {len(alt_df):,} in the second run (**data**). One row per customer.

### Data dictionary
{md_table(dict_tbl)}

### Raw data profile
{md_table(prof)}

`TotalCharges` blanks are single-space text values. `MonthlyCharges` max is the 100-times error.

### Cleaning summary
| Fix | Rows (main run) | Action |
| --- | --- | --- |
| Duplicate `customerID` with different Churn | {n_dup} rows removed | Kept the Churn = Yes row. Second run kept the No row |
| `MonthlyCharges` 100 times too large, check passed | {n_div} | Divided by 100 |
| `MonthlyCharges` 100 times too large, check failed | {n_fail} rows removed | User decision |
| Blank `TotalCharges` (tenure 0) | {n_tc} | Set to 0 |
| `RetentionOfferAccepted` | column | Excluded (leakage) |
| **Rows** | {profile['rows']:,} → {len(main_df):,} | |

Full row-by-row list: `cleaning_log.md`.

### Key results: main run
**Churn by contract**

{md_table(contract_tbl)}

Raw gap = month-to-month churn rate − 1-year churn rate = {pct(bc.loc['Month-to-month', 'churn_rate'])} − {pct(bc.loc['One year', 'churn_rate'])} = {pp(m['raw_gap'])} (**derived**).

**Gap within tenure bands**

{md_table(band_tbl)}

**Gap after controls (logistic regression)**

A logistic regression estimates the chance of churn from several variables at the same time. Model: `{FORMULA}`. All {len(main_df):,} customers, including 2-year customers.

Gap after controls = average over month-to-month customers of (predicted churn as month-to-month − predicted churn as 1-year) = {pp(m['adj_gap'], 2)} (**derived**). 95% range from {N_BOOT} bootstrap samples (resampling the customers with replacement, seed {SEED}): {pp(lo_ci, 2)} to {pp(hi_ci, 2)}.

{md_table(coefs)}

**Month-to-month revenue**
- Customers: {m['mtm_n']:,} (**data**).
- Monthly revenue: {money(m['mtm_rev_sum'])} total (**derived**: sum of `MonthlyCharges` for MTM customers, after the fix), ${m['mtm_rev_avg']:.2f} average (**derived**: total / customers).

**Net value (main run)**

Revenue saved = MTM customers × switch rate × churn effect × average monthly charge × 12. Net value = revenue saved − $2,000,000 (**derived**).

{md_table(value_tbl(m))}

**Both duplicate runs**

{md_table(both_tbl)}

**Second run net value**

{md_table(value_tbl(a))}

**Churn drivers (main run)**

"Overall" compares the group with all other customers. "Within each contract" repeats the comparison inside each contract type (groups of 30 or more customers). "higher" means the group churns more. Differences under 0.5 points count as "none".

{md_table(drv_tbl)}

**Loyalty app users by contract**

{md_table(loyalty_tbl)}

Share = customers in the row / all customers with that `LoyaltyAppUser` value (**derived**).

### Assumptions
| Assumption | Low | Mid | High | Set by | Why |
| --- | --- | --- | --- | --- | --- |
| Switch rate | 5% | 10% | 20% | The user | Share of MTM customers who accept a 1-year contract; no data in the file |
| Churn effect | {pp(m['adj_gap'] / 2)} (half the gap after controls) | {pp(m['adj_gap'])} (gap after controls) | {pp(m['raw_gap'])} (raw gap) | The user | The gap after controls may still include other differences, so low is half of it |
| Horizon | 12 months | 12 months | 12 months | The user | One year of revenue from saved customers |
| Campaign cost | $2,000,000 | $2,000,000 | $2,000,000 | VP of Marketing (case) | Given in the case |
| Charges match tolerance | 10% | 10% | 10% | The analyst | Allows for price changes over the customer's tenure |
| Tenure bands | 0–12, 13–24, 25–48, 49–72 | | | The analyst | Equal-ish groups for the within-band check |

Break-even checks (**derived**):
- At a 10% switch rate, break-even churn effect = $2,000,000 / ({m['mtm_n']:,} × 10% × ${m['mtm_rev_avg']:.2f} × 12) = {pp(m['breakeven_effect_mid_switch'])}.
- At the raw gap, break-even switch rate = $2,000,000 / ({m['mtm_n']:,} × {pp(m['raw_gap'])} × ${m['mtm_rev_avg']:.2f} × 12) = {pct(m['breakeven_switch_high_effect'])}.

### Run the analysis again
From the repo root:

```bash
python3 runs/telco/analysis.py --force
```

Needs Python 3 with pandas, numpy, statsmodels, and matplotlib. The script writes every file in `runs/telco/`.

Use `--force`. Without it, the script stops when a stop-and-ask rule from the brief fires, and it writes no files. In this analysis, the rule "gap after controls is less than half the raw gap" fires. The user decided to continue, so `--force` records that decision.
"""
    (OUT / "recommendation.md").write_text(text)


if __name__ == "__main__":
    main()
