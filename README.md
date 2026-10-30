# Agentic Analyst Kit

Business analysis with an AI agent: a brief, a reviewer agent, and checks you can trust.
Built in the AI Fluency Sprint (BAX 462, UC Davis).

## The case: the $2M decision
The VP of Marketing wants to spend $2M to move month-to-month customers to 1-year contracts.
Should we fund it?

## How this repo works
| File | What it is |
| --- | --- |
| `CLAUDE.md` | Team standards. The agent reads them in every session |
| `briefs/` | One brief per business question |
| `.claude/agents/` | Specialist agents, for example a reviewer |
| `.claude/hooks/` | Guardrails the agent cannot skip (raw data is read-only) |
| `data/raw/` | Raw data. Read-only |
| `runs/` | Outputs: recommendation, charts, logs |

## Steps (prompts only, no code)
Copy-paste prompts for every step: **[PROMPTS.md](PROMPTS.md)**. Use **claude.ai/code**, not the normal Claude chat.

0. **Know the data:** profile the data, record 3 data issues, and add 1 rule to `CLAUDE.md`.
1. **Brief:** let the agent interview you and write `briefs/2m-campaign.md`.
2. **Reviewer:** create a reviewer agent. Compare its checks with 2 of your own.
3. **Run:** in Plan mode, read the plan, change 1 step, approve.
4. **Verify and decide:** ask for evidence. Compare it with your 3 data issues. Write your own recommendation.
5. **Deliver:** fix what the review found, push, then merge to `main`.

## Results
- **My recommendation:**
- **Full report with charts:** [runs/telco/recommendation.md](runs/telco/recommendation.md)
- **The brief I wrote:** [briefs/2m-campaign.md](briefs/2m-campaign.md)
- **My team rule:** see "Analysis rules" in [CLAUDE.md](CLAUDE.md)
- **The reviewer agent:** [.claude/agents/reviewer.md](.claude/agents/reviewer.md) and its review: [runs/telco/review.md](runs/telco/review.md)

## Data
**Source:** IBM Telco Customer Churn sample dataset (IBM Sample Data Sets), a fictional phone and internet company with 7,043 customers. Public copy: [kaggle.com/datasets/blastchar/telco-customer-churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn).

`data/raw/telco_v2.csv` is a modified version made for teaching. Some rows and columns were changed or added, so results differ from the original dataset.
