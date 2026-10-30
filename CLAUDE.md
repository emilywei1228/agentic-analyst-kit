# Telco Analytics Team: Standards

These rules apply to every analysis in this repo. The question for each task is in a brief in `briefs/`.

## How to write (every reply and every file)
Write in ASD-STE100 Simplified Technical English. The reader may not be a data expert or a native English speaker.
- Be brief. Give the answer first. Do not repeat what the user said.
- One idea per sentence. Maximum 20 words per sentence.
- Maximum 4 sentences per paragraph. Use tables and short lists, not long text.
- Use active voice and common words. Use one word for one meaning.
- Write instructions as commands: "Remove the duplicates", not "The duplicates should be removed".
- Explain a technical term in plain words the first time you use it.
- When you ask the user a question, ask one question. Give 2 or 3 choices and say which one you recommend.

## Data
- Raw data is in `data/raw/`. Never change it. Write cleaned data to `runs/`.
- Before any analysis, profile the data: row count, unique IDs, column types, min and max of number columns, blanks per column.
- Log every row you remove or change, with the reason, in `cleaning_log.md`.

## Definitions
- Churn: the `Churn` column is "Yes" (the customer left in the last month).
- Customer: one unique `customerID`.
- Churn rate: churned customers divided by all customers in the group.

## Analysis rules
- Say "associated with", never "causes", unless the data comes from an experiment.
- Show the plan before you run code.
- Every number in a deliverable must come from code that can be run again.
- Never invent a number, fact, or source. If the data cannot answer, write "unknown" and say what data is needed.
- Label each number: **data** (counted directly from the file), **derived** (calculated from data numbers; show the formula), or **assumption** (not in the data; say who set it and why).
- Opportunity sizes: show low, mid, and high, with every assumption stated.

## Charts
- One insight per chart. The title states the finding. Gray out the rest. No clutter.

## Deliverables for every analysis (always in `runs/telco/`, never another folder)
- `recommendation.md`: a complete report. A reader must understand it without opening any other file. It has 3 parts:
  1. **Summary** (1 page maximum): the recommendation, what we found, how sure we are, the value range, data issues, risks, and the next step.
  2. **Charts**: show every chart in the report with `![chart title](chart_file.png)`. Under each chart, write one sentence that says what it shows.
  3. **Appendix**: the data source and size; a data dictionary (column, meaning, type); a cleaning summary (rows before and after, each fix); the key result tables; every assumption with its low, mid, and high values; and the command to run the analysis again.
- Charts as PNG files, in the same folder as `recommendation.md`.
- `cleaning_log.md`
- `findings.json` in exactly this format:

```json
{
  "recommendation": "fund | do_not_fund | test_first",
  "data_issues": [
    {"column": "<column name>", "issue": "<what is wrong>", "rows_affected": 0, "action": "<what was done>"}
  ],
  "drivers": [
    {"variable": "<column name>", "direction_overall": "higher | lower | none",
     "direction_within_contract": "higher | lower | mixed | not_checked"}
  ]
}
```
`direction` means: does this group churn more (higher) or less (lower) than the rest?
