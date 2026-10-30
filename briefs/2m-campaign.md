# Brief: $2M contract campaign

## 1. Decision
Should we fund a $2M campaign that moves month-to-month customers to 1-year contracts?

Use this decision rule. Net value = revenue saved in 12 months − $2M.

| Result | Recommendation |
| --- | --- |
| Low net value is above $0 | `fund` |
| The low-to-high range crosses $0 | `test_first` |
| High net value is below $0 | `do_not_fund` |

## 2. Questions to answer
1. Does the churn gap between month-to-month and 1-year customers remain after controls for tenure, internet type, and payment method?
2. How many month-to-month customers are there, and what is their monthly revenue?
3. What are the low, mid, and high net values?

## 3. Data checks
Do these checks before the analysis. Log each change in `runs/telco/cleaning_log.md`.

| Issue | Rows | Action |
| --- | --- | --- |
| Duplicate `customerID`: 2 rows each, with different `Churn` | 211 IDs | Main run: keep the "Yes" row. Second run: keep the "No" row. Report both runs. |
| `MonthlyCharges` 100 times too large (1,870 to 11,515) | 200 | For each row, compare value / 100 with `TotalCharges` / `tenure`. If they match, divide by 100. Log each row. |
| `TotalCharges` blank, `tenure` is 0 | 11 | Set to 0. Log each row. |
| `RetentionOfferAccepted` is filled only for churners | all | Exclude the column from the analysis. It leaks the churn result. |

"Match" in the charges check: value / 100 is within 10% of `TotalCharges` / `tenure`. This tolerance is an **assumption** set by the analyst. Report it in the appendix.

## 4. Analysis
1. Profile the data, as `CLAUDE.md` says.
2. Calculate the churn rate by contract type. The raw gap = month-to-month churn rate − 1-year churn rate.
3. Calculate the gap after controls:
   - Compare month-to-month and 1-year churn within each tenure band (0–12, 13–24, 25–48, 49+ months).
   - Fit a logistic regression: churn on contract type, tenure, internet type, and payment method. A logistic regression is a model that estimates the chance of a yes/no result. Report the contract gap in percentage points.
4. Count the month-to-month customers. Sum and average their `MonthlyCharges`.
5. Calculate the net value for low, mid, and high:

   Revenue saved = month-to-month customers × switch rate × churn effect × average monthly charge × 12 months.

   Net value = revenue saved − $2,000,000.

| Assumption | Low | Mid | High | Set by |
| --- | --- | --- | --- | --- |
| Switch rate (share of month-to-month customers who move to 1-year) | 5% | 10% | 20% | the user |
| Churn effect | half the gap after controls | gap after controls | raw gap | the user |
| Horizon | 12 months | 12 months | 12 months | the user |
| Campaign cost | $2M | $2M | $2M | the VP of Marketing (case) |

6. Run steps 2 to 5 again with the "No" duplicate rows. Report both results side by side.
7. Apply the decision rule in section 1.

Say "associated with", never "causes". The data is not from an experiment.

## 5. Stop and ask the user
Stop the work and ask the user before you continue when:
- The recommendation is different between the "Yes" run and the "No" run.
- The charges check fails for any of the 200 rows.
- The gap after controls is less than half the raw gap, or it reverses.
- A new data issue appears that this brief does not cover.

## 6. Deliverables
Write all files to `runs/telco/`, as `CLAUDE.md` says:
- `recommendation.md`: Summary, Charts, and Appendix.
- `cleaning_log.md`
- `findings.json`, in the exact format in `CLAUDE.md`.
- These 3 charts, as PNG files. Each title states the finding:
  1. Churn rate by contract type.
  2. The month-to-month vs 1-year churn gap within each tenure band.
  3. Net value for low, mid, and high, with a line at $0.
- The command to run the analysis again.
