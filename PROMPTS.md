# Lab prompts

Copy each prompt with the copy button on the right of the box. Paste it into **claude.ai/code** (not the normal Claude chat).

## Setup check
```
List the files in data/raw.
```
Expected: `telco_v2.csv`.

## Step 0. Know the data
Start with exploratory data analysis. Read only: change nothing.
```
Profile data/raw/telco_v2.csv. Show me: row count, unique customer IDs, each column's type, min and max of every number column, blanks per column, and churn rate by every column. Do not clean or change anything.
```
Review the output: counts, value ranges, blanks, and churn by group. Record 3 data issues. You will check them against the agent's work in Step 4.

### Add one rule to CLAUDE.md
Use this pattern: **When [situation], always [action], and [show or log what].**
A good rule is specific, can be checked, and works for any analysis.
- Good: "Report every churn rate with its group size (n)."
- Good: "Show the formula next to every derived number."
- Weak: "Be accurate." (Too vague to check.)
```
Add this rule to CLAUDE.md under "Analysis rules": <your rule>. Then tell me in one line how you will follow it in this analysis.
```

## Step 1. Brief by interview
```
Interview me one question at a time to write briefs/2m-campaign.md for this decision: should we fund a $2M campaign to move month-to-month customers to 1-year contracts? Cover: the decision, the questions to answer, data checks, analysis, when to stop and ask me, and what to deliver. Push back if my answer is vague. Then write the file.
```
Give specific answers. The gray text in the prompt box is only a suggestion.

## Step 2. Reviewer agent
While the agent works, write 2 things *you* would check as a reviewer.
```
Create a subagent called reviewer. It acts like a senior analyst who did not do the work. It checks every number in recommendation.md against the raw data, flags any causal claim, flags any data problem the analysis missed, and writes its review to runs/telco/review.md. It can read files and run code, but it cannot edit the analysis. Create only the agent file. No hooks or other files.
```
Open `.claude/agents/reviewer.md`. Did it include your 2 checks?

## Step 3. Run in Plan mode
First click **Auto** under the prompt box and choose **Plan** (or press `3`). Check that it says **Plan**.
```
Follow CLAUDE.md and briefs/2m-campaign.md. Do the analysis and write all deliverables. When done, ask the reviewer agent to review it. Report its verdict. Do not fix anything yet.
```
Read the plan. Find one step you would do differently, and type the change as a normal message. Then approve.

While it runs, open `briefs/2m-campaign.md`. Which "stop and ask" rule do you expect to fire?

## Step 4. Verify and decide
The evidence prompt is on the slide. After it:
- Compare the evidence with the 3 data issues you recorded in Step 0.
- Write **your own** recommendation in 2 lines. You can disagree with the agent.

## Step 5. Deliver
```
Fix only the must-fix items the review flagged. In README.md, after "My recommendation:", write: <your 2 lines>. Then commit everything with the message "Session 1 run" and push to GitHub.
```
Push failed with a 403 error? The Claude GitHub app has no access to your repo. Ask for help.

Then:
1. Click **Create PR** in Claude Code, then **Merge** on GitHub. Your repo page now shows your work.
2. Submit your name and repo link: https://forms.gle/CzgbPNLwc2AJMQLXA
