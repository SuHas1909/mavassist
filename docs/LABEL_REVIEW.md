# Evaluation label review

The routing evaluation compares MavAssist's recommended office with an expected office for each question in
`docs/ai-evaluation-100.json` (100 questions) and `docs/ai-evaluation-holdout-50.json` (50 questions). Both files are
marked as drafts: the labels must be reviewed independently before the results count as acceptance evidence (FR-04,
test LABEL-001, Azure DevOps task 134).

**Status: not reviewed yet.** No reviewer decisions have been recorded. Owners: Harmanpreet Kaur and Suhas S.

## How to review

1. Each reviewer works alone and does not look at MavAssist's answers first.
2. For every question, read it and decide which single UTA office should handle it, using the directory details.
3. Record the decision in the table below (or a copy of it): agree with the label, or propose a different office with
   a one-line reason. Mark questions that are genuinely ambiguous.
4. When both reviewers are done, compare. Where they disagree with the label or with each other, discuss and record
   the final label. Change the dataset only through a pull request that links this file.
5. Fill in the sign-off section and bump the dataset `status` (for example "Reviewed v3, date").

## Sign-off

| Field | Reviewer 1 | Reviewer 2 |
|---|---|---|
| Name | | |
| Date | | |
| Dataset version reviewed | | |
| Questions reviewed | | |
| Labels agreed | | |
| Labels changed | | |

## Decisions

| Question ID | Current expected office | Reviewer 1 | Reviewer 2 | Final label | Reason |
|---|---|---|---|---|---|
| | | | | | |
