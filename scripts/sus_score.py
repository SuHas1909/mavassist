"""Score the usability study recorded in docs/usability-results.csv (see docs/SUS_STUDY.md).

Prints the number of participants, mean and median SUS, and the median time to the correct office.
Exits with an error when there is no participant data; it never invents or fills in results.
"""
import argparse
import csv
import statistics
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--csv', default=str(Path(__file__).parents[1] / 'docs' / 'usability-results.csv'))
args = parser.parse_args()
SUS = [f'sus_{i}' for i in range(1, 11)]


def sus_score(answers):
    """Standard SUS: odd items (answer - 1), even items (5 - answer), sum x 2.5."""
    if len(answers) != 10 or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError('SUS needs ten answers from 1 to 5')
    return 2.5 * sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers))


rows = list(csv.DictReader(open(args.csv, newline='', encoding='utf-8-sig')))
if not rows:
    sys.exit(f'No participant rows in {args.csv}: run the study in docs/SUS_STUDY.md first.')
scores, times, tasks, ok = {}, [], 0, 0
for r in rows:
    pid = (r.get('participant_id') or '').strip()
    if not pid:
        continue
    if all((r.get(k) or '').strip() for k in SUS):
        scores[pid] = sus_score([int(r[k]) for k in SUS])
    if (r.get('task') or '').strip():
        tasks += 1
        if (r.get('success') or '').strip() == '1':
            ok += 1
            times.append(float(r['time_seconds']))
participants = sorted({(r.get('participant_id') or '').strip() for r in rows} - {''})
print(f'Participants: {len(participants)} (target >= 10)')
if scores:
    vals = list(scores.values())
    print(f'SUS: mean {statistics.mean(vals):.1f}, median {statistics.median(vals):.1f} from {len(vals)} questionnaires (target >= 70)')
else:
    print('SUS: no complete questionnaires')
if times:
    print(f'Tasks: {ok}/{tasks} found the correct office; median time {statistics.median(times):.0f} s (target <= 60 s)')
else:
    print(f'Tasks: {ok}/{tasks} found the correct office; no timed successes')
