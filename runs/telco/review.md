# Review: $2M contract campaign (runs/telco)

## Verdict
**pass with fixes.** All numbers I checked in `recommendation.md` match my own code from the raw file. The decision rule gives `do_not_fund` correctly. The must-fix items are about the rerun command, number labels, and one invented fact. These items do not change the recommendation.

Context from the user: the user excluded the 9 `MonthlyCharges` rows that failed the 10% check. The user continued after the "gap after controls is less than half the raw gap" stop rule. I accept both decisions. I do not flag them.

The decision does not depend on the size of the gap. At a 20% switch rate and a 100 pp churn effect, the revenue saved is $617,161 (**derived**: 3,870 × 20% × $66.4472 × 12). Net value is then -$1,382,839. The campaign breaks even only at a 64.8% switch rate with a 100 pp effect.

## Must fix
1. **File:** `recommendation.md`, lines 218–225 ("Run the analysis again"). **Problem:** `python3 runs/telco/analysis.py` stops, because a stop-and-ask rule fires (gap after controls is 45% of the raw gap). Without `--force`, the script writes no deliverables. The command in the report does not make the report again. **Fix:** Change the command to `python3 runs/telco/analysis.py --force`. Say that `--force` records the user decision to continue after the stop rule.
2. **File:** `recommendation.md`, Summary and Appendix. **Problem:** Many numbers have no **data** / **derived** / **assumption** label, as `CLAUDE.md` requires. Examples:
   - Line 8: 44.3% and 14.6% (rates are derived).
   - Line 9: "45% of the raw gap" (no formula). The 95% range has no label.
   - Line 15: the value range and the second-run values.
   - Line 17: 211, 200, 191, 9, 11 (data counts).
   - Line 20: 45% and 49% (no formula).
   - Line 21: "86% of loyalty app users are month-to-month". It has no label and no table in the Appendix.
   - Line 31: chart sentence rates.
   - Line 46: 7,034 rows after cleaning.
   - Lines 129–134, 162–166, 184–188, 194–202: table columns for rates, gaps, churn effect, customers switched, customers saved, and revenue saved.
   - Line 156: "$257,150 total (**data**)". It is a sum of values after the fix, so label it **derived** (sum of `MonthlyCharges` for MTM customers).

   **Fix:** Add a label and a formula to each number or table column. Add a small table for the 86% figure (main run: 85.75%).
3. **File:** `recommendation.md`, line 53 (data dictionary). **Problem:** "SeniorCitizen: 1 = age 65 or older". The data, the brief, and `README.md` do not give the age of 65. This is an invented fact. **Fix:** Write "1 = senior citizen (age limit unknown)".

## Should fix
1. **File:** `cleaning_log.md`, duplicate rows (main run and second run). **Problem:** The log gives the line of the removed row. It does not give the line of the kept row. **Fix:** Add the `csv_line` of the kept row for each of the 211 IDs.
2. **File:** `recommendation.md`, line 212 (Assumptions table). **Problem:** The table says the analyst set the tenure bands, for "equal-ish groups". The brief (section 4, step 3) sets the bands. The groups are not equal: 342 to 1,989 MTM customers per band. **Fix:** Write "Set by: the brief". Remove "Equal-ish groups".
3. **File:** `findings.json`, `drivers`, `tenure`. **Problem:** `"direction_overall": "higher"` means "tenure 0–12 months churns more". A reader can think "higher tenure churns more", which is the opposite. **Fix:** Use a field value that is not ambiguous. Or add a sentence in `recommendation.md` that says each driver compares one named group (for tenure, 0–12 months).
4. **File:** `findings.json`, `data_issues`. **Problem:** The 384 normal rows where `MonthlyCharges` is more than 10% from `TotalCharges` / `tenure` are not in the list. `cleaning_log.md` mentions them (5.5%). **Fix:** Add one entry: column `MonthlyCharges`, rows_affected 384, action "No change. Normal price change".
5. **File:** `findings.json` and `recommendation.md` line 107. **Problem:** `findings.json` gives rows_affected 422 for `customerID`. The report says "211 rows removed". Both are correct, but the reader can think they conflict. **Fix:** In `findings.json`, write "422 rows (211 IDs × 2); 211 rows removed" in the `issue` text.
6. **File:** `recommendation.md`, Summary "How sure we are" (line 13). **Problem:** The best argument for the decision is missing. Even with a 100 pp churn effect, the high case loses money. **Fix:** Add: "At a 20% switch rate and a 100 pp effect, net value is -$1,382,839 (**derived**)."
7. **File:** `recommendation.md`, line 140. **Problem:** The bootstrap range uses only 200 samples, so it changes with the seed. My run (300 samples, other seed) gives 10.05 to 16.77 pp. The report gives 10.08 to 17.10 pp. **Fix:** Use 1,000 or more samples. Say that the range is approximate.
8. **File:** `recommendation.md`, line 20. **Problem:** The report gives a reason for the user decision ("because no gap size in the range changes the decision"). I cannot confirm that the user gave this reason. **Fix:** Confirm the reason with the user, or write only "The user decided to continue."
9. **File:** `chart2_gap_by_tenure_band.png`. **Problem:** All bars use the accent color. `CLAUDE.md` says to gray out the rest. **Fix:** Optional. One insight is "the gap is positive in every band", so this is minor. Keep the chart, or highlight the smallest band (49–72).
10. **File:** `recommendation.md`, line 29. **Problem:** The markdown title ("Month-to-month customers churn more than 1-year customers") is different from the PNG title ("...churn 29.8 points more than 1-year customers"). **Fix:** Use the same title in both places.

## Number check table
Main run = keep the "Yes" duplicate row. Second run = keep the "No" row. Both runs exclude the 9 failed rows.

| # | Number in report | Where | My value | Match (yes/no) | Note |
| --- | --- | --- | --- | --- | --- |
| 1 | 7,254 raw rows | rec. line 45 | 7,254 | yes | |
| 2 | 7,043 unique `customerID` | rec. line 45 | 7,043 | yes | |
| 3 | 23 columns | rec. line 45 | 23 | yes | |
| 4 | 211 duplicate IDs, 2 rows each, different Churn | rec. line 17 | 211 IDs, 422 rows, all with Yes and No | yes | Pairs are the same in every other column except `RetentionOfferAccepted` |
| 5 | 200 `MonthlyCharges` rows 100 times too large | rec. line 17 | 200 (1,870 to 11,515) | yes | Normal max is 118.75 |
| 6 | 191 fixed, 9 removed | rec. lines 17, 108–109 | 191, 9 | yes | |
| 7 | 11 blank `TotalCharges`, tenure 0 | rec. line 17 | 11, all tenure 0 | yes | |
| 8 | `RetentionOfferAccepted` blanks 5,221 | rec. line 100 | 5,221 (all Churn = No) | yes | 2,033 filled, all Churn = Yes |
| 9 | 7,034 rows after cleaning, both runs | rec. line 46 | 7,034 and 7,034 | yes | |
| 10 | MTM 3,870 / 1,716 churned / 44.3% | rec. line 121 | 3,870 / 1,716 / 44.34% | yes | |
| 11 | 1-year 1,470 / 214 / 14.6% | rec. line 122 | 1,470 / 214 / 14.56% | yes | |
| 12 | 2-year 1,694 / 101 / 6.0% | rec. line 123 | 1,694 / 101 / 5.96% | yes | |
| 13 | Raw gap 29.8 pp | rec. lines 8, 125 | 29.78 pp | yes | |
| 14 | Band gaps 39.2 / 28.6 / 20.3 / 11.7 pp | rec. lines 131–134 | 39.16 / 28.60 / 20.31 / 11.69 pp | yes | Band counts also match |
| 15 | Gap after controls 13.27 pp | rec. lines 9, 140 | 13.27 pp | yes | Same coefficients as line 144–152 |
| 16 | 95% range 10.08 to 17.10 pp | rec. line 140 | 10.05 to 16.77 pp | no | Bootstrap noise (different seed and sample count). Not a real error |
| 17 | 45% of raw gap | rec. lines 9, 20 | 44.6% | yes | |
| 18 | MTM revenue $257,150 total, $66.45 average | rec. lines 10, 156 | $257,150.50, $66.4472 | yes | |
| 19 | Net value low / mid / high: -$1,989,762 / -$1,959,048 / -$1,816,189 | rec. lines 11, 164–166 | -$1,989,762 / -$1,959,048 / -$1,816,189 | yes | |
| 20 | Revenue saved $10,238 / $40,952 / $183,811 | rec. lines 164–166 | $10,238 / $40,952 / $183,811 | yes | |
| 21 | Customers switched 194 / 387 / 774 | rec. lines 164–166 | 193.5 / 387.0 / 774.0 | yes | 194 is rounded |
| 22 | Customers saved 13 / 51 / 231 | rec. lines 164–166 | 12.84 / 51.36 / 230.52 | yes | |
| 23 | Second run raw gap 30.8 pp, gap after controls 15.0 pp | rec. lines 173–174 | 30.75 pp, 15.04 pp | yes | |
| 24 | Second run 49% of raw gap | rec. line 20 | 48.9% | yes | |
| 25 | Second run net value -$1,988,395 / -$1,953,580 / -$1,810,204 | rec. lines 15, 177–179 | -$1,988,395 / -$1,953,580 / -$1,810,204 | yes | |
| 26 | Break-even effect 648.1 pp at 10% switch | rec. lines 13, 215 | 648.1 pp | yes | |
| 27 | Break-even switch 217.6% at raw gap | rec. line 216 | 217.6% | yes | |
| 28 | 86% of app users are MTM | rec. line 21 | 85.75% | yes | |
| 29 | Driver rates (7 rows: n, group churn, rest churn) | rec. lines 196–202 | Same n and rates for all 7 rows | yes | |
| 30 | Driver directions in `findings.json` | `findings.json` | Within-contract: tenure +18.0 / -0.7 / -3.1 (mixed); Senior +14.0 / +3.2 / -1.2 (mixed); App -22.7 / -5.3 / -2.9 (lower) | yes | |
| 31 | Normal rows more than 10% from `TotalCharges` / `tenure`: 5.5% | `cleaning_log.md` | 384 of 7,043 = 5.45% | yes | |
| 32 | Decision `do_not_fund` | rec. line 5, `findings.json` | High net value is below $0 in both runs | yes | Decision rule applied correctly |

## Causal language
No "causes", "drives", "leads to", "because of", "results in", "impact of", or "effect of" in `recommendation.md` or `findings.json`. These items are borderline:

| Quote | File and line | Suggested words |
| --- | --- | --- |
| "the campaign must cut churn by 648 pp for each switched customer" | `recommendation.md` line 13 | "the churn gap for each switched customer must be 648 pp". It is a hypothetical, so this change is optional |
| "Churn effect" (column and assumption name) | `recommendation.md` lines 160–166, 208 | The brief uses this term. Add once: "churn effect is an assumption, not a measured effect" |
| "Churn drivers (main run)" | `recommendation.md` line 190 | "Groups associated with higher churn (main run)" |

## Missed data problems
| Column | Problem | Rows affected | Effect on result |
| --- | --- | --- | --- |
| `MonthlyCharges` | 384 normal rows (5.45% of 7,043 with tenure above 0) differ by more than 10% from `TotalCharges` / `tenure`. The ratio range is 0.636 to 1.451. The 9 removed rows have ratios 0.693 to 1.335, so they are inside the normal range. The analysis mentions this only in `cleaning_log.md` | 384 (plus the 9 removed) | None on the decision. If you keep the 9 rows (divided by 100), MTM customers are 3,875 and the average is $66.40 |
| `Churn` | `CLAUDE.md` says churn means "left in the last month". The MTM churn rate is 44.3%, which is not a likely monthly rate. The revenue formula counts the gap one time over 12 months. The real time period of the `Churn` column is unknown | all 7,034 | None on the decision. The upper bound (20% switch, 100 pp effect) is $617,161 saved, which is below $2M |
| `Churn` (duplicates) | The 211 duplicate pairs are the same in all columns except `Churn` and `RetentionOfferAccepted`. So the churn label is unknown for 211 customers (3.0%) | 422 rows | Covered by the two runs. Raw gap is 29.8 pp or 30.8 pp. Decision is the same |
| Other columns | I checked for leakage: no other column has a value that occurs only for one `Churn` value. No values are out of range (tenure 0 to 72, `SeniorCitizen` 0 or 1, no charges at 0 or below) | 0 | None |

## How to rerun
The check code is outside the repo. Run from any folder:

```bash
R=/private/tmp/claude-503/-Users-emily-Documents-agentic-analyst-kit/3b843a63-a625-4c83-a07a-ccd3317dcac0/scratchpad/review
python3 -I $R/check.py /Users/emily/Documents/agentic-analyst-kit
python3 -I $R/boot.py /Users/emily/Documents/agentic-analyst-kit
```

- `check.py`: profile, leakage, duplicates, charges check, both runs, model, net values, drivers.
- `boot.py`: bootstrap range (300 samples, seed 7) and the upper bound.
- Needs Python 3 with pandas, numpy, and statsmodels.
