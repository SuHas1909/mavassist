# Usability study (SUS and time to find an office)

Checks NFR-04: **SUS score >= 70** and **median time to the correct office <= 60 seconds**, with at least
**10 consenting students** (tests USAB-001 and USAB-002, defect D-13, Azure DevOps task 148 and story 89).

**Status: not run.** `docs/usability-results.csv` contains only its header; no participant data exists. Owner: Krisha Patel.

## Protocol

1. Recruit at least 10 students who agree to take part. Use participant IDs only (P01, P02, ...); never record names,
   student IDs or anything personal. Use fictional needs only.
2. Prepare the app on the local Docker stack and a fresh student account per participant.
3. Give each participant these tasks one at a time, and time each one from the moment they start until they name the
   office they would go to:
   * pay tuition (expected: Student Accounts)
   * get tutoring (expected: the tutoring / learning centre office in the directory)
   * an international visa question (expected: International Students and Scholars)
   * borrow or fix a laptop (expected: the technology help office in the directory)
   Confirm the expected office for each task against the directory before the first session.
4. Record one row per task in `docs/usability-results.csv`: `participant_id, task, expected_service, returned_service,
   success (1/0), time_seconds`. Leave the SUS columns empty on task rows except one row per participant.
5. After the tasks, ask the ten standard SUS statements on a 1-5 scale (1 = strongly disagree, 5 = strongly agree) and
   enter them as `sus_1` ... `sus_10` on that participant's first row. Add notes about keyboard, mobile or screen-reader
   problems in `notes`.
6. Score with `python scripts/sus_score.py` (prints the number of participants, the mean and median SUS, and the median
   time to the correct office). Report the real numbers, including when they miss the targets.

## SUS statements

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Scoring: odd items score (answer - 1), even items score (5 - answer); the sum times 2.5 gives 0-100 per participant.
