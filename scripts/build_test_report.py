"""Build the MavAssist test deliverables from raw results only.

Outputs (written to docs/ and to the final evidence folder):
  MavAssist_Test_Cases.xlsx                      sheets: All Test Cases, AI Routing Cases, Summary, Defects, Traceability
  MavAssist_Test_Summary_and_Defect_Report.docx

Every status comes from a raw file: JUnit XML (backend, Vitest), Playwright JSON, k6 summary-export JSON, ZAP JSON,
evaluation JSON, smoke logs, or the Nov 9 workbook for rows that were not re-run (each backed by its log).
Tests without raw evidence stay "Not run" (or "Descoped") with the reason. After writing, both files are re-opened
and their totals are checked against each other and against the raw results; any mismatch stops the build.

Usage:  python scripts/build_test_report.py [--final test-evidence-final-2026-11-10] [--pdf]
Needs:  pip install -r scripts/requirements-report.txt   (--pdf also needs Microsoft Word for docx2pdf)
"""
import argparse
import collections
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import docx
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
NOV9 = ROOT / 'test-evidence-2026-11-09'
NOV10 = ROOT / 'test-evidence-2026-11-10'
XLSX_NAME = 'MavAssist_Test_Cases.xlsx'
DOCX_NAME = 'MavAssist_Test_Summary_and_Defect_Report.docx'
STATUSES = ['Pass', 'Fail', 'Blocked', 'Descoped', 'Not run']
NAVY, INK, MUTED, ZEBRA = '1F466E', '13243B', '5B6B7D', 'F4F7FA'
STATUS_FILL = {'Pass': 'C6EFCE', 'Fail': 'FFC7CE', 'Blocked': 'FFEB9C', 'Descoped': 'D9D9D9', 'Not run': 'EDEDED',
               'Met': 'C6EFCE', 'Partial': 'FFEB9C', 'Not met': 'FFC7CE', 'Fixed': 'C6EFCE', 'Open': 'FFEB9C'}
HARMANPREET, ASHWINDER = 'Harmanpreet Kaur', 'Ashwinder Singh'
REQUIREMENTS = {
    'FR-01': 'Student registration and login; administrator role gate',
    'FR-02': 'Service directory and detail (location, hours, contact, source date)',
    'FR-03': 'Keyword search and category filtering',
    'FR-04': 'Assistant recommends the right office with reason, cited steps and clarification',
    'FR-05': 'Administrator create, update, archive and restore services',
    'FR-06': 'Categories and date-bounded notices',
    'FR-07': 'Bookmarks', 'FR-08': 'Recently viewed (ten most recent)',
    'FR-09': 'Usage analytics by date range', 'FR-10': 'Helpful / not-helpful answer ratings',
    'NFR-01': 'Performance: 50 users, non-AI p95 < 1 s, AI p95 < 5 s, errors < 1%',
    'NFR-02': 'Security: password hashing, token expiry, role checks, headers, HTTPS',
    'NFR-03': 'Privacy: no raw questions or identifiers stored; redaction; retention',
    'NFR-04': 'Usability and accessibility: WCAG AA, responsive 360 px, SUS >= 70',
    'NFR-05': 'Reliability: fallback when the hosted model fails; coverage >= 70%',
}
# Sprint dates from the Azure DevOps project iterations.
SPRINTS = [('Sprint 1', '2026-09-28', '2026-10-11'), ('Sprint 2', '2026-10-12', '2026-10-25'),
           ('Sprint 3', '2026-10-26', '2026-11-08'), ('Sprint 4', '2026-11-09', '2026-11-22'),
           ('Release and Hardening', '2026-11-23', '2026-12-04')]


class BuildError(SystemExit):
    pass


def fail(msg):
    raise BuildError(f'BUILD FAILED: {msg}')


def check(cond, msg):
    if not cond:
        fail(msg)


def read(path):
    check(path.exists(), f'missing raw result {path.relative_to(ROOT)}')
    return path.read_text(encoding='utf-8-sig', errors='replace')


def rel(path):
    return str(Path(path).relative_to(ROOT)).replace('\\', '/')


# ----------------------------------------------------------------------------------------------- raw results
def junit_cases(path):
    root = ET.fromstring(read(path))
    out = []
    for c in root.iter('testcase'):
        failure = c.find('failure') if c.find('failure') is not None else c.find('error')
        status = 'Fail' if failure is not None else ('Not run' if c.find('skipped') is not None else 'Pass')
        msg = (failure.get('message') or '').splitlines()[0][:200] if failure is not None else ''
        out.append({'classname': c.get('classname') or '', 'name': c.get('name'), 'status': status,
                    'time': float(c.get('time') or 0), 'message': msg})
    check(out, f'no test cases in {rel(path)}')
    return out


def playwright_results(path):
    data = json.loads(read(path))
    out = []

    def walk(suite):
        for spec in suite.get('specs', []):
            for t in spec['tests']:
                status = {'expected': 'Pass', 'unexpected': 'Fail', 'flaky': 'Fail', 'skipped': 'Not run'}[t['status']]
                out.append({'project': t['projectName'], 'file': spec['file'], 'title': spec['title'], 'status': status,
                            'duration': sum(r.get('duration', 0) for r in t['results']) / 1000})
        for s in suite.get('suites', []):
            walk(s)
    for s in data['suites']:
        walk(s)
    st = data['stats']
    check(len(out) == st['expected'] + st['unexpected'] + st['flaky'] + st['skipped'], 'Playwright stats disagree with specs')
    return out, st


def k6_summary(path):
    data = json.loads(read(path))
    m = data['metrics']
    crossed = sorted(f'{name} {expr}' for name, v in m.items() for expr, bad in (v.get('thresholds') or {}).items() if bad)
    return {'errors_pct': round(100 * m['http_req_failed']['value'], 2), 'requests': m['http_reqs']['count'],
            'iterations': m['iterations']['count'], 'non_ai_p95': round(m['non_ai_latency']['p(95)']),
            'chat_p95': round(m['chat_latency']['p(95)']), 'crossed': crossed, 'ok': not crossed}


def zap_alerts(path):
    data = json.loads(read(path))
    alerts = [{'risk': a['riskdesc'].split()[0], 'name': a['alert'], 'plugin': a['pluginid'], 'count': int(a['count'])}
              for s in data['site'] for a in s['alerts']]
    return alerts


def coverage_percent(log):
    m = re.search(r'^TOTAL\s+\d+\s+\d+\s+(\d+)%', log, re.M)
    check(m, 'coverage TOTAL line missing from backend log')
    return int(m.group(1))


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def commit_date(sha):
    try:
        return git('show', '-s', '--format=%ad', '--date=short', sha)
    except subprocess.CalledProcessError:
        fail(f'commit {sha} not found in git history')


def sprint_for(date):
    for name, start, end in SPRINTS:
        if start <= date <= end:
            return name
    fail(f'no sprint covers {date}')


# ----------------------------------------------------------------------------------------------- test inventory
OLD_TO_CURRENT = {  # Nov 9 rows whose test was renamed or replaced by the safety-routing change (commit a8c1032)
    'test_classification[I was sexually assaulted last week-None]': ('test_classification[I was sexually assaulted last week-victim_sexual]', 'expectation changed: now handled as a victim report'),
    'test_evaluation_questions_never_hit_guardrails': ('test_evaluation_questions_only_hit_victim_support', 'renamed; evaluation questions may now reach victim support only'),
    'test_openrouter_request_shape_and_triage_routes_unmatched_question': ('test_model_routes_by_meaning_not_keywords', 'replaced by model-first routing test'),
    'test_model_can_mark_retrieved_match_out_of_scope': ('test_model_intents_map_to_tested_responses[off_topic-out_of_scope]', 'replaced by intent mapping test'),
    'test_abuse_gets_a_calm_boundary': ('test_model_intents_map_to_tested_responses[abuse-boundary]', 'replaced by intent mapping test'),
    'test_valid_generated_answer_and_prompt_carries_context': ('test_valid_routed_answer_and_prompt_carries_context', 'renamed'),
    'test_malformed_generation_rejected[result0]': ('test_malformed_router_output_rejected[bad0]', 'renamed'),
    'test_malformed_generation_rejected[result1]': ('test_malformed_router_output_rejected[bad1]', 'renamed'),
    'test_malformed_generation_rejected[result2]': ('test_malformed_router_output_rejected[bad2]', 'renamed'),
    'test_malformed_generation_rejected[result3]': ('test_malformed_router_output_rejected[bad3]', 'renamed'),
}
SECURITY_TESTS = {'test_authentication_and_security', 'test_every_admin_route_denies_student', 'test_rate_limit_and_headers'}
BACKEND_REQ = [  # (substring of test name, requirements)
    ('authentication_and_security', 'FR-01, NFR-02'), ('every_admin_route_denies', 'FR-01, NFR-02'),
    ('rate_limit_and_headers', 'NFR-02'), ('directory_search_filters', 'FR-03'), ('seeded_directory', 'FR-02'),
    ('admin_service_crud', 'FR-05, FR-06'), ('category_validation', 'FR-06'), ('bookmarks_and_recent', 'FR-07, FR-08'),
    ('chat_clarification_feedback_analytics_retention', 'FR-04, FR-09, FR-10, NFR-03'),
    ('ai_timeout_fallback', 'FR-04, NFR-05'), ('llm_payload_privacy', 'FR-04, NFR-03'),
    ('analytics_totals', 'FR-09'), ('circuit_breaker', 'NFR-05'), ('archiving_excludes', 'FR-04, FR-05'),
    ('knowledge_import', 'FR-02'), ('bounded_history', 'NFR-03'), ('never_contains_model_output', 'NFR-03'),
    ('falls_back', 'FR-04, NFR-05'), ('slow_provider', 'NFR-01, NFR-05'), ('fast_provider', 'NFR-01'),
    ('limit_zero', 'NFR-01'),
]


def backend_requirement(name):
    for key, req in BACKEND_REQ:
        if key in name:
            return req
    return 'FR-04'  # remaining backend tests exercise the assistant (routing, safety, citations, parsing)


def humanise(name):
    base = re.sub(r'^test_', '', re.sub(r'\[.*', '', name)).replace('_', ' ')
    param = re.search(r'\[(.*)\]$', name)
    return base.capitalize() + (f' ({param.group(1)})' if param else '')


def build_inventory(final):
    logs = final / 'logs'
    rows = []
    raw = {}
    old_wb = openpyxl.load_workbook(NOV9 / 'test-cases.xlsx')['All Test Cases']
    old = {r[0]: dict(zip(['id', 'type', 'name', 'steps', 'expected', 'actual', 'status', 'evidence'], r))
           for r in old_wb.iter_rows(min_row=2, values_only=True) if r[0]}
    check(len(old) == 94, f'expected 94 rows in the Nov 9 workbook, found {len(old)}')

    # Backend (pytest JUnit)
    be = junit_cases(logs / 'backend-tests.xml')
    raw['backend'] = be
    raw['coverage'] = coverage_percent(read(logs / 'backend-tests.log'))
    by_name = {c['name']: c for c in be}
    check(len(by_name) == len(be), 'duplicate backend test names in JUnit XML')
    used = set()
    for oid in sorted((k for k in old if k.startswith('BE-')), key=lambda k: int(k[3:])):
        o = old[oid]
        current, note = OLD_TO_CURRENT.get(o['name'], (o['name'], ''))
        check(current in by_name, f'{oid} ({o["name"]}) has no matching test in the current run')
        used.add(current)
        rows.append(backend_row(oid, current, by_name[current], o, note))
    n = max(int(k[3:]) for k in old if k.startswith('BE-'))
    for c in be:
        if c['name'] not in used:
            n += 1
            rows.append(backend_row(f'BE-{n:03d}', c['name'], c, None, 'new since Nov 9'))
    # Frontend unit (Vitest JUnit) and build
    fe = junit_cases(logs / 'frontend-unit-junit.xml')
    raw['unit'] = fe
    fe_map = {'registration form uses labels and submits only student fields': 'FE-UNIT-001',
              'authenticated requests attach the session token and JSON body': 'FE-UNIT-002',
              'expired sessions clear credentials and notify the app': 'FE-UNIT-003'}
    check(sorted(c['name'] for c in fe) == sorted(fe_map), 'Vitest test names changed; update the FE-UNIT mapping')
    for c in fe:
        o = old[fe_map[c['name']]]
        rows.append(row(fe_map[c['name']], o['type'], 'NFR-04' if 'form' in c['name'] else 'FR-01, NFR-02', o['name'],
                        'Frontend dependencies installed (npm ci)', o['steps'], o['expected'],
                        'All assertions passed.' if c['status'] == 'Pass' else c['message'], c['status'],
                        rel(logs / 'frontend-unit-junit.xml'), '2026-11-10', ASHWINDER))
    build_log = read(logs / 'frontend-build.log')
    build_ok = '✓ built in' in build_log and 'error TS' not in build_log
    raw['build'] = build_ok
    o = old['FE-BUILD-001']
    rows.append(row('FE-BUILD-001', o['type'], 'NFR-05', o['name'], 'Frontend dependencies installed', o['steps'], o['expected'],
                    'tsc -b and vite build completed; production assets emitted.' if build_ok else 'Build failed (see log).',
                    'Pass' if build_ok else 'Fail', rel(logs / 'frontend-build.log'), '2026-11-10', ASHWINDER))
    # Browser end-to-end (Playwright JSON), three engines
    pw, pw_stats = playwright_results(logs / 'playwright-results.json')
    raw['e2e'], raw['e2e_stats'] = pw, pw_stats
    e2e_defs = [('student: registration', 'E2E-001', 'FR-01, FR-02, FR-03, FR-04, FR-07, FR-08, FR-10, NFR-04'),
                ('primary student pages', 'E2E-002', 'NFR-04'), ('assistant says not found', 'E2E-003', 'FR-04'),
                ('admin: resource lifecycle', 'E2E-004', 'FR-05, FR-06, FR-09, NFR-02'), ('360 px student flow', 'E2E-005', 'NFR-04')]
    engines = ['chromium', 'firefox', 'webkit']
    check(sorted({r['project'] for r in pw}) == engines, 'Playwright did not run on all three browser engines')
    for e, engine in enumerate(engines):
        for k, (prefix, base_id, req) in enumerate(e2e_defs):
            hits = [r for r in pw if r['project'] == engine and r['title'].startswith(prefix)]
            check(len(hits) == 1, f'expected one {engine} result for "{prefix}", found {len(hits)}')
            r = hits[0]
            o = old[base_id]
            tid = base_id if engine == 'chromium' else f'E2E-{5 * e + k + 1:03d}'
            rows.append(row(tid, o['type'], req, f'{o["name"]} [{engine}]',
                            'API in offline mode (rate limit off for the test server), web on 127.0.0.1:5173, test administrator provisioned',
                            o['steps'], o['expected'],
                            f'Passed in {r["duration"]:.1f} s.' if r['status'] == 'Pass' else 'Failed (see log).', r['status'],
                            rel(logs / 'playwright-results.json'), '2026-11-10', ASHWINDER))
    # Smoke and Docker
    smoke = read(NOV9 / 'logs' / 'local-smoke.log')
    for sid, pat in (('SMOKE-001', r'Frontend: HTTP 200'), ('SMOKE-002', r'Backend health: HTTP 200')):
        o = old[sid]
        ok = re.search(pat, smoke) is not None
        rows.append(row(sid, o['type'], 'FR-02' if sid == 'SMOKE-001' else 'NFR-05', o['name'], 'Local API and web started',
                        o['steps'], o['expected'], o['actual'], 'Pass' if ok else 'Fail', rel(NOV9 / 'logs' / 'local-smoke.log'),
                        '2026-11-09', HARMANPREET))
    dsmoke = read(NOV10 / 'logs' / 'docker-smoke.log')
    d_ok = 'API /health 200: True' in dsmoke and 'Web :8080 200: True' in dsmoke
    raw['docker'] = d_ok
    o = old['DOCKER-001']
    rows.append(row('DOCKER-001', o['type'], 'NFR-05', o['name'], 'Docker Desktop running; root .env present',
                    o['steps'], o['expected'], 'db, api and web healthy; API /health and web :8080 returned 200.' if d_ok else 'Not healthy (see log).',
                    'Pass' if d_ok else 'Fail', rel(NOV10 / 'logs' / 'docker-smoke.log'), '2026-11-10', ASHWINDER))
    dlive = read(NOV9 / 'logs' / 'docker-live-e2e.log')
    o = old['DOCKER-002']
    rows.append(row('DOCKER-002', o['type'], 'FR-01, FR-04, FR-05, NFR-04', o['name'], 'Docker stack running on :8080 / :8000',
                    o['steps'], o['expected'], o['actual'], 'Pass' if re.search(r'\b5 passed', dlive) else 'Fail',
                    rel(NOV9 / 'logs' / 'docker-live-e2e.log'), '2026-11-09; retest 2026-11-10', HARMANPREET))
    # Performance (k6 summaries)
    k_sql = k6_summary(NOV10 / 'logs' / 'k6-50vu-summary.json')
    k_pg = k6_summary(NOV10 / 'logs' / 'k6-50vu-docker-postgres-summary.json')
    raw['k6_sqlite'], raw['k6_postgres'] = k_sql, k_pg
    o = old['PERF-001']
    rows.append(row('PERF-001', o['type'], 'NFR-01', '50 users for 60 s - local API, SQLite, offline mode',
                    'Rate limit off and AI keys blank for the test server only', o['steps'],
                    'errors < 1%; non-AI p95 < 1,000 ms; chat p95 < 5,000 ms', k6_text(k_sql), 'Pass' if k_sql['ok'] else 'Fail',
                    rel(NOV10 / 'logs' / 'k6-50vu-summary.json'), '2026-11-10', ASHWINDER))
    p10 = json.loads(read(NOV9 / 'logs' / 'performance-load-10vu.log').split('EXIT_CODE')[0])
    o = old['PERF-002']
    rows.append(row('PERF-002', o['type'], 'NFR-01', o['name'], 'Local API, SQLite', o['steps'], o['expected'], o['actual'],
                    'Pass' if p10['failed'] == 0 and p10['requests'] == 600 else 'Fail',
                    rel(NOV9 / 'logs' / 'performance-load-10vu.log'), '2026-11-09', HARMANPREET))
    rows.append(row('PERF-003', 'Performance', 'NFR-01', '50 users for 60 s - Docker stack with PostgreSQL',
                    'Docker stack; rate limit off and AI keys blank through a temporary override (not committed)',
                    '1. Start the Docker stack. 2. Register a student. 3. Run scripts/load-test.js with 50 users for 60 s.',
                    'errors < 1%; non-AI p95 < 1,000 ms; chat p95 < 5,000 ms', k6_text(k_pg), 'Pass' if k_pg['ok'] else 'Fail',
                    rel(NOV10 / 'logs' / 'k6-50vu-docker-postgres-summary.json'), '2026-11-10', ASHWINDER))
    # Security scan (ZAP baseline)
    zap = {n: zap_alerts(final / 'zap' / f'zap-baseline-{n}.json') for n in ('web', 'api')}
    zap['web-before'] = zap_alerts(final / 'zap' / 'zap-baseline-web-before-fix.json')
    raw['zap'] = zap
    for sid, n, target in (('SEC-001', 'web', 'web app (nginx, port 8080)'), ('SEC-002', 'api', 'API (port 8000)')):
        counts = collections.Counter(a['risk'] for a in zap[n])
        hm = counts['High'] + counts['Medium']
        rows.append(row(sid, 'Security scan', 'NFR-02', f'OWASP ZAP baseline scan - {target}',
                        'Docker stack running; scanner on the stack network; AI keys blank',
                        f'1. Run zap-baseline.py against the {target}. 2. Review alerts by risk.',
                        'No high or medium risk alerts; low alerts documented',
                        f"High {counts['High']}, Medium {counts['Medium']}, Low {counts['Low']}, Informational {counts['Informational']}."
                        + (' Medium CSP finding fixed (form-action added) and re-scanned.' if n == 'web' else ''),
                        'Pass' if hm == 0 else 'Fail', rel(final / 'zap' / f'zap-baseline-{n}.json'), '2026-11-10', ASHWINDER))
    # AI routing evaluations
    off100 = json.loads(read(NOV10 / 'ai-eval-offline-100.json'))
    off50 = json.loads(read(NOV10 / 'ai-eval-offline-holdout-50.json'))
    diag = json.loads(read(NOV10 / 'ai-eval-hosted-diagnostic-gpt-4o-mini.json'))
    raw['eval'] = {'offline100': off100, 'offline50': off50, 'diag': diag}
    for sid, ev, label in (('AI-001', off100, '100-question set'), ('AI-002', off50, '50-question holdout')):
        t1, t3 = ev['all_answers_top1_accuracy'], ev['all_answers_top3_accuracy']
        ok = t1 >= .8 and t3 >= .95 and ev['unknown_offices'] == 0 and ev['errors'] == 0 and ev['cases'] == ev['cases_planned']
        rows.append(row(sid, 'AI routing (offline)', 'FR-04', f'Offline routing accuracy - {label}',
                        'API with AI keys blank (keyword and semantic retrieval with cited sources)',
                        '1. Run scripts/evaluate_ai.py against the offline API. 2. Compare the returned office with the label.',
                        'top-1 >= 80%, top-3 >= 95%, 0 unknown offices',
                        f"{ev['cases']} questions: top-1 {100 * t1:.0f}%, top-3 {100 * t3:.0f}%, unknown offices {ev['unknown_offices']}.",
                        'Pass' if ok else 'Fail', rel(NOV10 / ('ai-eval-offline-100.json' if sid == 'AI-001' else 'ai-eval-offline-holdout-50.json')),
                        '2026-11-10', ASHWINDER))
    rows.append(row('AI-003', 'AI routing (hosted)', 'FR-04', 'Hosted routing accuracy - full 100 + 50 questions with --require-rag',
                    'Hosted model reachable with enough quota for 150 requests',
                    '1. Run scripts/evaluate_ai.py --require-rag on both sets.', 'All answers hosted; top-1 >= 80%, top-3 >= 95%',
                    'Blocked: the paid account has no credit (HTTP 402) and the free tier allows 50 requests/day; free models tried so far were rate limited or replied with JSON the parser rejected.',
                    'Blocked', rel(NOV10 / 'test-report.md'), '2026-11-10', ASHWINDER))
    hosted = [r for r in diag['results'] if r['mode'] == 'rag']
    d_ok = len(hosted) == diag['hosted_answers'] and all(r['top1'] for r in hosted)
    rows.append(row('AI-004', 'AI routing (hosted)', 'FR-04', 'Hosted diagnostic sample before the account credit ran out',
                    'Paid hosted model; timing script; 100-question set', '1. Ask each question. 2. Record mode, top-1 and top-3.',
                    'Hosted answers route to the labelled office (diagnostic, not acceptance)',
                    f"{len(hosted)} hosted answers, {sum(r['top1'] for r in hosted)} correct top-1; the remaining {diag['fallback_answers']} were fallback after a provider error.",
                    'Pass' if d_ok else 'Fail', rel(NOV10 / 'ai-eval-hosted-diagnostic-gpt-4o-mini.json'), '2026-11-10', ASHWINDER))
    p95 = diag['hosted_latency_s']['p95']
    rows.append(row('AI-005', 'Performance', 'NFR-01', 'Hosted answer latency p95 < 5 s',
                    'Paid hosted model; per-question timing', '1. Time each hosted answer. 2. Compute p95.', 'p95 < 5 s',
                    f"p50 {diag['hosted_latency_s']['p50']} s, p95 {p95} s, max {diag['hosted_latency_s']['max']} s ({len(hosted)} hosted answers).",
                    'Pass' if p95 < 5 else 'Fail', rel(NOV10 / 'ai-eval-hosted-diagnostic-gpt-4o-mini.json'), '2026-11-10', ASHWINDER))
    # Tests without evidence
    for sid, typ, req, name, reason in (
        ('USAB-001', 'Usability study', 'NFR-04', 'SUS score >= 70 with 10 or more students', 'Not run: usability study not yet conducted (owner: Krisha Patel); docs/usability-results.csv has no participant rows.'),
        ('USAB-002', 'Usability study', 'NFR-04', 'Median time to find the right office <= 60 s', 'Not run: needs the same usability study sessions.'),
        ('LABEL-001', 'AI dataset review', 'FR-04', 'Independent review of the 150 evaluation labels', 'Not run: independent label review not yet recorded (owners: Harmanpreet Kaur / Suhas S); see docs/LABEL_REVIEW.md.'),
        ('STAGE-001', 'Deployment', 'NFR-02, NFR-05', 'Cloud staging deployment smoke test over HTTPS', 'Not run: the demo runs on the local Docker stack (see docs/SCOPE_CHANGES.md); decision owner: Ashwinder Singh.'),
        ('STAGE-002', 'Performance', 'NFR-01', '50-user load test on cloud staging', 'Not run: no staging deployment (see docs/SCOPE_CHANGES.md).'),
    ):
        rows.append(row(sid, typ, req, name, '', '', '', reason, 'Not run', '', '', ''))
    rows.append(row('XB-001', 'Cross-browser (cloud)', 'NFR-04', 'BrowserStack cloud browser run', '', '', '',
                    'Descoped: replaced by the browser suite on three engines (E2E-001 to E2E-015); see docs/SCOPE_CHANGES.md.',
                    'Descoped', '', '', ''))
    ids = [r['Test ID'] for r in rows]
    check(len(ids) == len(set(ids)), 'duplicate test IDs')
    for r in rows:
        check(r['Status'] in STATUSES, f"{r['Test ID']} has invalid status {r['Status']}")
        check(r['Status'] in ('Not run', 'Descoped') or r['Evidence file'], f"{r['Test ID']} has a status but no evidence file")
        if r['Evidence file']:
            check((ROOT / r['Evidence file']).exists(), f"{r['Test ID']} evidence {r['Evidence file']} does not exist")
    return rows, raw


def k6_text(k):
    return (f"{k['requests']} requests, {k['iterations']} iterations; errors {k['errors_pct']}%; non-AI p95 {k['non_ai_p95']:,} ms; "
            f"chat p95 {k['chat_p95']:,} ms." + (f" Thresholds crossed: {', '.join(k['crossed'])}." if k['crossed'] else ''))


def row(tid, typ, req, name, pre, steps, expected, actual, status, evidence, date, by):
    return {'Test ID': tid, 'Test Type': typ, 'Requirement (FR/NFR)': req, 'Test Name': name, 'Preconditions': pre,
            'Test Steps': steps, 'Expected Result': expected, 'Actual Result': actual, 'Status': status,
            'Evidence file': evidence, 'Run date': date, 'Run by': by}


def backend_row(tid, name, case, old, note):
    module = case['classname'].split('.')[-1]
    typ = 'Security / role' if re.sub(r'\[.*', '', name) in SECURITY_TESTS else (
        'Backend guardrail' if module == 'test_guard' else 'Backend API integration')
    steps = old['steps'] if old else f'1. Run pytest tests/{module}.py::{re.sub(r"\[.*", "", name)} with an isolated database and AI keys blank.'
    expected = old['expected'] if old else 'All assertions pass.'
    actual = ('All assertions passed.' if case['status'] == 'Pass' else case['message']) + (f' ({note})' if note and old else '')
    return row(tid, typ, backend_requirement(name), name if not old else name, 'Isolated test database; hosted AI keys blank (as in CI)',
               steps, expected, actual, case['status'], rel(FINAL / 'logs' / 'backend-tests.xml'), '2026-11-10', ASHWINDER)


# ----------------------------------------------------------------------------------------------- other sheets
def routing_rows():
    rows = []
    for dataset, ev_file in (('ai-evaluation-100.json', 'ai-eval-offline-100.json'), ('ai-evaluation-holdout-50.json', 'ai-eval-offline-holdout-50.json')):
        questions = {c['id']: c for c in json.loads(read(ROOT / 'docs' / dataset))['cases']}
        ev = json.loads(read(NOV10 / ev_file))
        diag = {r['id']: r for r in json.loads(read(NOV10 / 'ai-eval-hosted-diagnostic-gpt-4o-mini.json'))['results']} if '100' in dataset else {}
        check(len(ev['results']) == len(questions), f'{ev_file}: {len(ev["results"])} results for {len(questions)} questions')
        for r in ev['results']:
            q = questions[r['case_id']]
            d = diag.get(r['case_id'])
            rows.append({'ID': r['case_id'], 'Set': '100-question' if '100' in dataset else 'Holdout 50', 'Question': q['question'],
                         'Expected office': r['expected'], 'Returned office': (r['returned'] or [''])[0],
                         'Top-3 returned': '; '.join(r['returned'][:3]), 'Top-1': 'Pass' if r['top1'] else 'Fail',
                         'Top-3': 'Pass' if r['top3'] else 'Fail',
                         'Mode': 'offline' + (' (safety reply)' if r['mode'] == 'safety' else ''), 'Run date': '2026-11-10',
                         'Hosted diagnostic top-1': ('Pass' if d['top1'] else 'Fail') if d and d.get('mode') == 'rag' else ''})
    return rows


def summary_rows(tests):
    by = collections.OrderedDict()
    for t in tests:
        by.setdefault(t['Test Type'], collections.Counter())[t['Status']] += 1
    out = []
    for typ, c in by.items():
        total = sum(c.values())
        executed = c['Pass'] + c['Fail']
        out.append({'Test Type': typ, 'Total': total, **{s: c[s] for s in STATUSES},
                    'Pass rate': f"{100 * c['Pass'] / executed:.0f}%" if executed else 'n/a'})
    tot = collections.Counter(t['Status'] for t in tests)
    executed = tot['Pass'] + tot['Fail']
    out.append({'Test Type': 'Total', 'Total': len(tests), **{s: tot[s] for s in STATUSES},
                'Pass rate': f"{100 * tot['Pass'] / executed:.0f}%" if executed else 'n/a'})
    return out


DEFECT_FIX = {  # commit(s) that fixed each defect (verified against git history at build time) and verifying tests
    'D-01': (['a8c1032'], ['test_victim_reports_get_support_not_refusal', 'test_victim_report_never_becomes_off_topic']),
    'D-02': (['a8c1032'], ['test_model_routes_by_meaning_not_keywords']),
    'D-03': (['a8c1032'], ['test_classification[i wanna hit someone-violence]']),
    'D-04': (['a8c1032'], ['test_classification[i got scammed-None]']),
    'D-05': (['fc26feb'], ['test_classification[fuck you-abuse]', 'test_model_intents_map_to_tested_responses[abuse-boundary]']),
    'D-06': (['fc26feb'], ['screenshot:assistant-empty-desktop.png']),  # visual check only; no automated test covers it
    'D-07': (['a8c1032'], ['DOCKER-001']),
    'D-08': (['a8c1032'], ['E2E-002', 'E2E-007', 'E2E-012']),
    'D-09': (['a8c1032', '73e1bc1'], ['E2E-001', 'E2E-002', 'E2E-006', 'E2E-007', 'E2E-011', 'E2E-012']),
    'D-10': (['a8c1032', '0f0f407'], ['PERF-001']),  # errors under load; PERF-003 also had 0% errors but fails on latency (D-15)
    'D-11': (['73e1bc1'], ['DOCKER-001', 'DOCKER-002']),  # environment issue; 73e1bc1 holds the retest evidence
    'D-12': (['91414be', '72933dd'], ['AI-003', 'AI-004']),
    'D-13': ([], ['USAB-001']),
    'D-14': (['73e1bc1', '0f0f407'], ['FE-UNIT-001', 'FE-UNIT-002', 'FE-UNIT-003']),
    'D-15': (['03b3835'], ['AI-005', 'test_slow_provider_falls_back_to_cited_sources_within_the_limit']),
}


def defect_rows(tests):
    text = read(ROOT / 'docs' / 'DEFECTS.md')
    lines = [l for l in text.splitlines() if re.match(r'\| D-\d\d \|', l)]
    check(len(lines) == 15, f'expected D-01 to D-15 in DEFECTS.md, found {len(lines)}')
    by_name = {t['Test Name']: t for t in tests}
    by_id = {t['Test ID']: t for t in tests}
    out = []
    for l in lines:
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        if len(c) == 11:  # "Fixed defects" table
            did, sev, sprint, found_date, summary, cause, fix, fixed_text, commit_text, _verified_text, status = c
            check(sprint == sprint_for(found_date), f'{did}: sprint {sprint} does not match found date {found_date}')
            story = {'D-07': '77, 83'}.get(did, '83' if did <= 'D-06' else '89')
        else:  # "Open defects" table (original columns)
            did, found, where, summary, sev, story, cause, fix, status = c[:9]
            found_date = dt.datetime.strptime(found + ' 2026', '%b %d %Y').date().isoformat()
            fixed_text = commit_text = ''
        commits, verifiers = DEFECT_FIX[did]
        for sha in re.findall(r'\b[0-9a-f]{7}\b', commit_text):
            check(sha in commits, f'{did}: commit {sha} in DEFECTS.md is not in the verified fix list')
            commit_date(sha)  # fails if the hash is not in git history
        dates = [commit_date(s) for s in commits]
        ids, visual = [], []
        for v in verifiers:
            if v.startswith('screenshot:'):
                shot = FINAL / 'screenshots' / v.split(':', 1)[1]
                check(shot.exists(), f'{did}: screenshot {rel(shot)} missing')
                visual.append(f'visual check: {rel(shot)}')
                continue
            t = by_id.get(v) or by_name.get(v)
            check(t is not None, f'{did}: verifying test {v} not found')
            ids.append(t['Test ID'])
        state = 'Fixed' if status.startswith(('Fixed', 'Closed')) else 'Open'
        if state == 'Fixed':
            bad = [i for i in ids if by_id[i]['Status'] != 'Pass']
            check(not bad, f'{did} is marked fixed but its verifying tests did not pass: {bad}')
        out.append({'ID': did, 'Severity': sev, 'Sprint found': sprint_for(found_date), 'Found date': found_date,
                    'Summary': re.sub(r'`', '', summary), 'Root cause': re.sub(r'`', '', cause), 'Fix': re.sub(r'`', '', fix),
                    'Fixed date': fixed_text or (max(dates) if dates and state == 'Fixed' else ''),
                    'Commit': commit_text or (', '.join(commits) if commits else 'n/a'), 'Status': state,
                    'Status detail': status, 'Story': story.split('/')[0].strip(), 'Verified by (test ID)': ', '.join(ids + visual)})
    return out


NOTES = {
    'NFR-01': 'Local SQLite load test passes; Docker/PostgreSQL latency and hosted answer latency miss the targets (D-15); staging not run.',
    'NFR-02': 'Role tests and ZAP baseline pass; HTTPS on cloud staging not verified (local Docker demo).',
    'NFR-03': 'Privacy tests pass. Hosted answers send a redacted question plus public office context (clarification in REQUIREMENTS.md).',
    'NFR-04': 'Accessibility and 360 px checks pass on three engines; SUS study not run yet.',
    'FR-04': 'Offline routing passes; full hosted evaluation blocked by provider limits (D-12); label review not recorded.',
}


def traceability_rows(tests):
    out = []
    for req, title in REQUIREMENTS.items():
        mapped = [t for t in tests if req in [x.strip() for x in t['Requirement (FR/NFR)'].split(',')]]
        c = collections.Counter(t['Status'] for t in mapped)
        if not mapped or c['Pass'] == 0 and c['Fail'] == 0:
            status = 'Not run'
        elif c['Fail'] == 0 and c['Blocked'] == 0 and c['Not run'] == 0:
            status = 'Met'
        elif c['Pass'] == 0:
            status = 'Not met'
        else:
            status = 'Partial'
        reason = NOTES.get(req, '')
        if not reason and status != 'Met':
            reason = 'Not passing: ' + ', '.join(f"{t['Test ID']} ({t['Status']})" for t in mapped if t['Status'] != 'Pass')
        out.append({'Requirement': req, 'Description': title, 'Test IDs': ', '.join(t['Test ID'] for t in mapped),
                    'Tests': len(mapped), 'Pass': c['Pass'], 'Fail': c['Fail'], 'Blocked': c['Blocked'],
                    'Not run / descoped': c['Not run'] + c['Descoped'], 'Status': status, 'Reason': reason})
    return out


# ----------------------------------------------------------------------------------------------- xlsx
def write_xlsx(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    head_font = Font(name='Aptos', bold=True, color='FFFFFF', size=10)
    head_fill = PatternFill('solid', fgColor=NAVY)
    thin = Side(style='thin', color='C9D3DD')
    widths = {'Test ID': 12, 'Test Type': 22, 'Requirement (FR/NFR)': 20, 'Test Name': 48, 'Preconditions': 34, 'Test Steps': 48,
              'Expected Result': 40, 'Actual Result': 48, 'Status': 11, 'Evidence file': 44, 'Run date': 16, 'Run by': 18,
              'Question': 60, 'Expected office': 34, 'Returned office': 34, 'Top-3 returned': 60, 'Summary': 50, 'Root cause': 50,
              'Fix': 50, 'Test IDs': 60, 'Description': 50, 'Reason': 60, 'Verified by (test ID)': 36, 'Status detail': 40}
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        cols = list(rows[0].keys())
        ws.append(cols)
        for r in rows:
            ws.append([r[c] for c in cols])
        for i, c in enumerate(cols, 1):
            cell = ws.cell(row=1, column=i)
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            ws.column_dimensions[get_column_letter(i)].width = widths.get(c, 14)
        for r in ws.iter_rows(min_row=2):
            for cell in r:
                cell.font = Font(name='Aptos', size=9, color=INK)
                cell.alignment = Alignment(vertical='top', wrap_text=True)
                cell.border = Border(bottom=thin)
                head = cols[cell.column - 1]
                if head in ('Status', 'Top-1', 'Top-3', 'Hosted diagnostic top-1') and cell.value in STATUS_FILL:
                    cell.fill = PatternFill('solid', fgColor=STATUS_FILL[cell.value])
                if title == 'Summary' and r[0].value == 'Total':
                    cell.font = Font(name='Aptos', size=9, bold=True, color=INK)
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        ws.row_dimensions[1].height = 30
    wb.save(path)


# ----------------------------------------------------------------------------------------------- docx
def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd')
    sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), color)
    tcPr.append(sh)


def para(doc, text, size=9.5, color=INK, bold=False, space_after=4, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name, r.font.size, r.font.bold, r.font.italic = 'Aptos', Pt(size), bold, italic
    r.font.color.rgb = RGBColor.from_string(color)
    p.paragraph_format.space_after = Pt(space_after)
    return p


def heading(doc, text, level=1):
    p = para(doc, text, size=13 if level == 1 else 10.5, color=NAVY if level == 1 else INK, bold=True, space_after=3)
    p.paragraph_format.space_before = Pt(10 if level == 1 else 6)
    p.paragraph_format.keep_with_next = True
    return p


def table(doc, headers, rows, widths=None, status_col=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(str(h))
        run.font.name, run.font.size, run.font.bold = 'Aptos', Pt(8), True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(cell, NAVY)
    for n, r in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = ''
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.name, run.font.size = 'Aptos', Pt(8)
            run.font.color.rgb = RGBColor.from_string(INK)
            if n % 2 == 1:
                shade(cells[i], ZEBRA)
            if status_col is not None and i == status_col and str(v) in STATUS_FILL:
                shade(cells[i], STATUS_FILL[str(v)])
    if widths:
        for row_ in t.rows:
            for i, w in enumerate(widths):
                row_.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def crop_for_report(src, dst, max_ratio=1.0):
    from PIL import Image
    im = Image.open(src)
    w, h = im.size
    if h > w * max_ratio:
        im = im.crop((0, 0, w, int(w * max_ratio)))
    im.save(dst)
    return dst


def write_docx(path, data, final):
    tests, summary, trace, defects, raw = data['tests'], data['summary'], data['trace'], data['defects'], data['raw']
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(0.75)
    sec.top_margin = sec.bottom_margin = Inches(0.7)
    doc.styles['Normal'].font.name = 'Aptos'
    para(doc, 'Test Summary and Defect Report', size=22, color='000000', bold=True, space_after=2)
    para(doc, 'CSE 6324 Advanced Topics in Software Engineering  ·  Team 3  ·  MavAssist', size=9, color=NAVY, bold=True, space_after=2)
    para(doc, f'Generated {dt.date.today().isoformat()} by scripts/build_test_report.py from the raw results in {final.name}/ and test-evidence-2026-11-10/. '
              'Every number below is read from a raw result file; nothing was entered by hand.', size=9, color=MUTED, space_after=8)

    heading(doc, '1. Scope and environment')
    para(doc, 'Scope: the MavAssist web application (student directory, search, assistant, saved and recent resources; administrator resources, '
              'categories, notices and usage insights), its API, and the Docker stack with PostgreSQL. Out of scope this term: cloud staging and '
              'BrowserStack (see docs/SCOPE_CHANGES.md).')
    table(doc, ['Item', 'Environment'], [
        ['Machine', 'Windows 11 laptop; Docker Desktop for the container stack'],
        ['Backend tests', f"pytest with an isolated SQLite database and AI keys blank (as in CI); coverage {raw['coverage']}%"],
        ['Browser tests', 'Playwright on Chromium, Firefox and WebKit against the API in offline mode and the web dev server'],
        ['Load tests', 'k6, 50 virtual users for 60 s: local API on SQLite, and the Docker stack on PostgreSQL (AI keys blank)'],
        ['Security scan', 'OWASP ZAP baseline (passive) against the Docker web app and API'],
        ['AI routing', 'Offline: keyword and semantic retrieval with cited sources. Hosted: diagnostic sample only (provider limits)'],
        ['Runs', 'Nov 9 baseline and Nov 10 retest by Harmanpreet Kaur; Nov 10 re-run and final run by Ashwinder Singh'],
    ], widths=[1.4, 5.6])

    heading(doc, '2. Results by test type')
    table(doc, ['Test type', 'Total', 'Pass', 'Fail', 'Blocked', 'Descoped', 'Not run', 'Pass rate'],
          [[s['Test Type'], s['Total'], s['Pass'], s['Fail'], s['Blocked'], s['Descoped'], s['Not run'], s['Pass rate']] for s in summary],
          widths=[2.2, .6, .6, .6, .7, .8, .7, .8])
    para(doc, 'Pass rate is passed / (passed + failed); blocked, descoped and not-run cases are counted separately.', size=8, color=MUTED)

    heading(doc, '3. Requirement coverage')
    table(doc, ['Req.', 'Description', 'Tests', 'Pass', 'Status', 'Reason'],
          [[t['Requirement'], t['Description'], t['Tests'], t['Pass'], t['Status'], t['Reason']] for t in trace],
          widths=[.55, 2.2, .5, .5, .65, 2.6], status_col=4)

    heading(doc, '4. Performance')
    ks, kp = raw['k6_sqlite'], raw['k6_postgres']
    table(doc, ['Run (50 users × 60 s)', 'Requests', 'Errors', 'Non-AI p95', 'Chat p95', 'Result'], [
        ['Local API, SQLite, offline mode', ks['requests'], f"{ks['errors_pct']}%", f"{ks['non_ai_p95']:,} ms", f"{ks['chat_p95']:,} ms", 'Pass' if ks['ok'] else 'Fail'],
        ['Docker stack, PostgreSQL, AI keys blank', kp['requests'], f"{kp['errors_pct']}%", f"{kp['non_ai_p95']:,} ms", f"{kp['chat_p95']:,} ms", 'Pass' if kp['ok'] else 'Fail'],
    ], widths=[2.4, .8, .7, 1.0, 1.0, .7], status_col=5)
    diag = raw['eval']['diag']
    para(doc, 'Targets: errors < 1%, non-AI p95 < 1,000 ms, chat p95 < 5,000 ms. The Docker stack had no errors but missed both latency '
              'targets; it runs semantic retrieval on the CPU for every query, the likely cause (not yet confirmed). Hosted answers '
              f"(diagnostic, {diag['hosted_answers']} answers) took p50 {diag['hosted_latency_s']['p50']} s and p95 {diag['hosted_latency_s']['p95']} s against a 5 s target (D-15). "
              'A per-question time limit that falls back to cited summaries is implemented; its before/after measurement is pending.')

    heading(doc, '5. AI routing accuracy')
    o1, o2 = raw['eval']['offline100'], raw['eval']['offline50']
    table(doc, ['Set (offline, measured)', 'Questions', 'Top-1', 'Top-3', 'Unknown offices', 'Result'], [
        ['100-question set', o1['cases'], f"{100 * o1['all_answers_top1_accuracy']:.0f}%", f"{100 * o1['all_answers_top3_accuracy']:.0f}%", o1['unknown_offices'], by_id(tests, 'AI-001')],
        ['50-question holdout', o2['cases'], f"{100 * o2['all_answers_top1_accuracy']:.0f}%", f"{100 * o2['all_answers_top3_accuracy']:.0f}%", o2['unknown_offices'], by_id(tests, 'AI-002')],
    ], widths=[2.2, .9, .7, .7, 1.1, .7], status_col=5)
    para(doc, f"Hosted model, noted separately: a diagnostic sample of {diag['hosted_answers']} hosted answers on the 100-question set, all "
              f"{sum(r['top1'] for r in diag['results'] if r['mode'] == 'rag')} correct at top-1, before the paid account ran out of credit. "
              'This is a diagnostic, not acceptance: the full hosted evaluation (AI-003) is blocked by provider limits (D-12).')

    heading(doc, '6. Security scan')
    before = collections.Counter(a['risk'] for a in raw['zap']['web-before'])
    after = collections.Counter(a['risk'] for a in raw['zap']['web'])
    api = collections.Counter(a['risk'] for a in raw['zap']['api'])
    table(doc, ['Target', 'High', 'Medium', 'Low', 'Info'], [
        ['Web app, before fix', before['High'], before['Medium'], before['Low'], before['Informational']],
        ['Web app, after fix', after['High'], after['Medium'], after['Low'], after['Informational']],
        ['API', api['High'], api['Medium'], api['Low'], api['Informational']],
    ], widths=[2.4, .8, .8, .8, .8])
    para(doc, 'The medium finding (Content-Security-Policy without form-action, which has no fallback) was fixed in nginx.conf and vercel.json '
              'and re-scanned. Remaining low findings are documented in docs/SECURITY_SCAN.md.')

    heading(doc, '7. Defects')
    table(doc, ['ID', 'Sev.', 'Found', 'Summary', 'Status', 'Commit', 'Verified by'],
          [[d['ID'], d['Severity'], d['Found date'], d['Summary'][:110], d['Status'], d['Commit'], d['Verified by (test ID)']] for d in defects],
          widths=[.45, .5, .75, 2.75, .55, .9, 1.1], status_col=4)

    heading(doc, '8. Open items and owners')
    table(doc, ['Item', 'Owner', 'Next step'], [
        ['D-13 / USAB-001-002: SUS study with 10+ students', 'Krisha Patel', 'Run sessions per docs/SUS_STUDY.md; score with scripts/sus_score.py'],
        ['LABEL-001: independent review of evaluation labels', 'Harmanpreet Kaur / Suhas S', 'Record decisions in docs/LABEL_REVIEW.md'],
        ['STAGE-001-002: cloud staging and HTTPS', 'Ashwinder Singh (decision)', 'Deploy or confirm the local Docker demo (docs/SCOPE_CHANGES.md)'],
        ['D-12 / AI-003: full hosted evaluation', 'Ashwinder Singh', 'Run in free-tier batches (evaluate_ai.py --sample) once a free model works'],
        ['D-15 / AI-005 / PERF-003: latency', 'Ashwinder Singh', 'Measure the time limit before/after; investigate Docker retrieval cost'],
    ], widths=[2.8, 1.5, 2.7])

    heading(doc, '9. Selected screenshots')
    shots = [('assistant-answer-desktop', 'Assistant answer with cited sources'), ('assistant-crisis-desktop', 'Crisis support response'),
             ('assistant-harm-report-desktop', 'Harm report: victim support'), ('assistant-violence-desktop', 'Violence: refusal and safety contacts'),
             ('assistant-not-found-desktop', 'Out of scope: not found'), ('assistant-fallback-desktop', 'Hosted model unavailable: cited-source fallback'),
             ('directory-desktop', 'Student directory'), ('admin-insights-desktop', 'Administrator usage insights')]
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix='mavassist-report-'))  # cropped copies for the report only; not evidence
    grid = doc.add_table(rows=0, cols=2)
    for i in range(0, len(shots), 2):
        cells = grid.add_row().cells
        for j, (name, caption) in enumerate(shots[i:i + 2]):
            src = final / 'screenshots' / f'{name}.png'
            check(src.exists(), f'screenshot {rel(src)} missing')
            img = crop_for_report(src, tmp / f'{name}.png')
            p = cells[j].paragraphs[0]
            p.add_run().add_picture(str(img), width=Inches(3.2))
            cap = cells[j].add_paragraph()
            r = cap.add_run(f'Figure {i + j + 1}. {caption}')
            r.font.name, r.font.size, r.font.bold = 'Aptos', Pt(8), True
            r.font.color.rgb = RGBColor.from_string(NAVY)
    para(doc, f'All screenshots (desktop, 360 px, administrator pages) are in {final.name}/screenshots/.', size=8, color=MUTED)
    doc.save(path)
    shutil.rmtree(tmp, ignore_errors=True)


def by_id(tests, tid):
    return next(t['Status'] for t in tests if t['Test ID'] == tid)


# ----------------------------------------------------------------------------------------------- verification
def verify(xlsx, docx_path, data):
    raw, tests = data['raw'], data['tests']
    expected = collections.Counter(t['Status'] for t in tests)
    # 1. raw results vs inventory
    be_rows = [t for t in tests if t['Evidence file'].endswith('logs/backend-tests.xml')]
    check(len(be_rows) == len(raw['backend']), f"backend rows {len(be_rows)} != JUnit cases {len(raw['backend'])}")
    check(sum(t['Status'] == 'Pass' for t in be_rows) == sum(c['status'] == 'Pass' for c in raw['backend']), 'backend pass count differs from JUnit')
    e2e_rows = [t for t in tests if t['Evidence file'].endswith('playwright-results.json')]
    check(len(e2e_rows) == len(raw['e2e']) == 15, f'E2E rows {len(e2e_rows)} / Playwright results {len(raw["e2e"])} (expected 15)')
    check(sum(t['Status'] == 'Pass' for t in e2e_rows) == raw['e2e_stats']['expected'], 'E2E pass count differs from Playwright stats')
    unit_rows = [t for t in tests if t['Evidence file'].endswith('frontend-unit-junit.xml')]
    check(len(unit_rows) == len(raw['unit']), 'unit rows differ from Vitest JUnit')
    # 2. xlsx re-read
    wb = openpyxl.load_workbook(xlsx)
    check(wb.sheetnames == ['All Test Cases', 'AI Routing Cases', 'Summary', 'Defects', 'Traceability'], f'unexpected sheets {wb.sheetnames}')
    ws = wb['All Test Cases']
    hdr = [c.value for c in ws[1]]
    x_counts = collections.Counter(r[hdr.index('Status')] for r in ws.iter_rows(min_row=2, values_only=True))
    check(x_counts == expected, f'xlsx status counts {dict(x_counts)} != inventory {dict(expected)}')
    sm = wb['Summary']
    shdr = [c.value for c in sm[1]]
    total = [r for r in sm.iter_rows(min_row=2, values_only=True) if r[0] == 'Total'][0]
    x_total = {s: total[shdr.index(s)] for s in STATUSES} | {'Total': total[shdr.index('Total')]}
    check(x_total['Total'] == len(tests) and all(x_total[s] == expected[s] for s in STATUSES), f'xlsx Summary total {x_total} != inventory')
    check(wb['AI Routing Cases'].max_row - 1 == len(raw['eval']['offline100']['results']) + len(raw['eval']['offline50']['results']) == 150,
          'AI Routing Cases should have 150 rows')
    check(wb['Defects'].max_row - 1 == 15, 'Defects sheet should list D-01 to D-15')
    check(wb['Traceability'].max_row - 1 == len(REQUIREMENTS), 'Traceability should list every FR and NFR')
    # 3. docx re-read: results-by-type table must equal the xlsx Summary sheet
    d = docx.Document(docx_path)
    res = next(t for t in d.tables if t.rows[0].cells[0].text == 'Test type')
    d_rows = {r.cells[0].text: [c.text for c in r.cells[1:7]] for r in res.rows[1:]}
    x_rows = {r[0]: [str(r[shdr.index(k)]) for k in ['Total', *STATUSES]] for r in sm.iter_rows(min_row=2, values_only=True)}
    check(d_rows == x_rows, f'docx results table differs from xlsx Summary:\n docx={d_rows}\n xlsx={x_rows}')
    k = next(t for t in d.tables if t.rows[0].cells[0].text.startswith('Run (50 users'))
    check(k.rows[1].cells[1].text == str(raw['k6_sqlite']['requests']) and k.rows[2].cells[1].text == str(raw['k6_postgres']['requests']),
          'docx k6 table differs from k6 summaries')
    return x_total


def main():
    global FINAL
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', default=None, help='final evidence folder (default: newest test-evidence-final-*)')
    ap.add_argument('--pdf', action='store_true', help='also render the docx to PDF (needs Microsoft Word)')
    args = ap.parse_args()
    finals = sorted(ROOT.glob('test-evidence-final-*'))
    FINAL = (ROOT / args.final) if args.final else (finals[-1] if finals else None)
    check(FINAL and FINAL.is_dir(), 'no test-evidence-final-* folder found')
    tests, raw = build_inventory(FINAL)
    data = {'tests': tests, 'raw': raw, 'routing': routing_rows(), 'summary': summary_rows(tests),
            'defects': defect_rows(tests), 'trace': traceability_rows(tests)}
    xlsx, docx_path = FINAL / XLSX_NAME, FINAL / DOCX_NAME
    write_xlsx(xlsx, {'All Test Cases': tests, 'AI Routing Cases': data['routing'], 'Summary': data['summary'],
                      'Defects': data['defects'], 'Traceability': data['trace']})
    write_docx(docx_path, data, FINAL)
    totals = verify(xlsx, docx_path, data)
    for f in (xlsx, docx_path):
        shutil.copy2(f, ROOT / 'docs' / f.name)
    if args.pdf:
        from docx2pdf import convert
        convert(str(docx_path), str(FINAL / DOCX_NAME.replace('.docx', '.pdf')))
    (FINAL / 'report-totals.json').write_text(json.dumps({'totals': totals, 'summary': data['summary'],
        'traceability': [{k: t[k] for k in ('Requirement', 'Status')} for t in data['trace']]}, indent=2), encoding='utf-8')
    print(json.dumps({'tests': len(tests), **{s: totals[s] for s in STATUSES}}, indent=None))
    print('Verified: xlsx Summary == docx results table == raw results. Wrote', rel(xlsx), 'and', rel(docx_path), '(copied to docs/)')


FINAL = None
if __name__ == '__main__':
    main()
