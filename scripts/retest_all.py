"""
Real-test ALL payer API endpoints. No guessing. No estimates.
Hits each api_base/metadata with actual HTTP request and records:
- HTTP status code
- Response time in ms
- FHIR version (if parseable)
- Classification based on actual response

Classifications (based solely on HTTP response):
- valid: 200 + valid FHIR CapabilityStatement JSON
- valid_non_fhir: 200 but not FHIR JSON
- auth_required: 401 or 403
- not_found: 404
- server_error: 5xx
- redirect: 3xx (followed, final result recorded)
- timeout: no response within 20s
- connection_refused: TCP refused
- dns_failure: hostname doesn't resolve
- ssl_error: TLS handshake failed
- unreachable: other connection error
- no_api: no api_base in record
"""
import sqlite3
import requests
import os
import sys
import time
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')
RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'retest_results.json')
TIMEOUT = 20
DELAY = 0.5  # seconds between requests


def classify(status_code, error, body_json):
    """Classify based on actual HTTP result."""
    if error:
        if 'timeout' in error.lower() or 'timed out' in error.lower():
            return 'timeout'
        if 'name or service not known' in error.lower() or 'nodename nor servname' in error.lower() or 'getaddrinfo' in error.lower():
            return 'dns_failure'
        if 'connection refused' in error.lower() or 'errno 111' in error.lower():
            return 'connection_refused'
        if 'ssl' in error.lower() or 'certificate' in error.lower():
            return 'ssl_error'
        return 'unreachable'
    if status_code == 200:
        if body_json and body_json.get('resourceType') == 'CapabilityStatement':
            return 'valid'
        return 'valid_non_fhir'
    if status_code in (401, 403):
        return 'auth_required'
    if status_code == 404:
        return 'not_found'
    if 400 <= status_code < 500:
        return 'client_error'
    if 500 <= status_code < 600:
        return 'server_error'
    if 300 <= status_code < 400:
        return 'redirect'
    return f'http_{status_code}'


def test_endpoint(api_base):
    """Hit api_base/metadata and return raw result."""
    url = api_base.rstrip('/') + '/metadata'
    start = time.time()
    try:
        resp = requests.get(
            url, timeout=TIMEOUT,
            headers={'Accept': 'application/fhir+json', 'User-Agent': 'FHIR-Directory-Validator/1.0'},
            allow_redirects=True
        )
        elapsed_ms = int((time.time() - start) * 1000)
        body_json = None
        fhir_version = None
        try:
            body_json = resp.json()
            if isinstance(body_json, dict):
                fhir_version = body_json.get('fhirVersion')
        except (json.JSONDecodeError, ValueError):
            pass

        classification = classify(resp.status_code, None, body_json)
        return {
            'url': url,
            'status_code': resp.status_code,
            'response_time_ms': elapsed_ms,
            'fhir_version': fhir_version,
            'classification': classification,
            'error': None,
            'final_url': resp.url if resp.url != url else None,
        }
    except requests.exceptions.Timeout:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            'url': url, 'status_code': None, 'response_time_ms': elapsed_ms,
            'fhir_version': None, 'classification': 'timeout', 'error': 'timeout', 'final_url': None,
        }
    except requests.exceptions.ConnectionError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        err_str = str(e)[:200]
        classification = classify(None, err_str, None)
        return {
            'url': url, 'status_code': None, 'response_time_ms': elapsed_ms,
            'fhir_version': None, 'classification': classification, 'error': err_str, 'final_url': None,
        }
    except requests.exceptions.SSLError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            'url': url, 'status_code': None, 'response_time_ms': elapsed_ms,
            'fhir_version': None, 'classification': 'ssl_error', 'error': str(e)[:200], 'final_url': None,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            'url': url, 'status_code': None, 'response_time_ms': elapsed_ms,
            'fhir_version': None, 'classification': 'unreachable', 'error': str(e)[:200], 'final_url': None,
        }


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get ALL payers
    rows = conn.execute("SELECT id, org_name, api_base FROM payers ORDER BY id").fetchall()
    total = len(rows)
    print(f"Testing {total} payers...")
    print(f"Start: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    results = []
    counts = {}

    for i, row in enumerate(rows):
        payer_id = row['id']
        org_name = row['org_name']
        api_base = row['api_base']

        if not api_base or api_base.strip() == '':
            result = {
                'payer_id': payer_id, 'org_name': org_name, 'api_base': None,
                'url': None, 'status_code': None, 'response_time_ms': 0,
                'fhir_version': None, 'classification': 'no_api', 'error': 'no api_base', 'final_url': None,
            }
        else:
            print(f"  [{i+1}/{total}] {org_name[:45]:45s} ... ", end='', flush=True)
            result = test_endpoint(api_base)
            result['payer_id'] = payer_id
            result['org_name'] = org_name
            result['api_base'] = api_base

            symbol = {'valid': '✅', 'valid_non_fhir': '🟡', 'auth_required': '🔒',
                      'timeout': '⏱️', 'not_found': '❌', 'unreachable': '🚫',
                      'dns_failure': '🌐', 'connection_refused': '🚫', 'ssl_error': '🔐',
                      'server_error': '💥', 'client_error': '⚠️', 'redirect': '↪️'
                      }.get(result['classification'], '❓')
            detail = f"HTTP {result['status_code']}" if result['status_code'] else result['error'][:40] if result['error'] else ''
            print(f"{symbol} {result['classification']} | {detail} | {result['response_time_ms']}ms")
            time.sleep(DELAY)

        results.append(result)
        counts[result['classification']] = counts.get(result['classification'], 0) + 1

    # Save raw results JSON
    with open(RESULTS_PATH, 'w') as f:
        json.dump({'tested_at': datetime.now(timezone.utc).isoformat(), 'total': total, 'results': results}, f, indent=2)

    # Update DB
    print("\n" + "=" * 80)
    print("Updating database with real results...")

    # Clear validation_log for fresh results
    conn.execute("DELETE FROM validation_log")

    for r in results:
        if r['classification'] == 'no_api':
            conn.execute("""UPDATE payers SET last_validated = datetime('now'),
                           last_validated_status = 'no_api' WHERE id = ?""", (r['payer_id'],))
        else:
            conn.execute("""INSERT INTO validation_log (payer_id, endpoint_url, status_code,
                           response_time_ms, fhir_version, is_valid, error)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                         (r['payer_id'], r['url'], r['status_code'], r['response_time_ms'],
                          r['fhir_version'], 1 if r['classification'] == 'valid' else 0, r['error']))
            conn.execute("""UPDATE payers SET last_validated = datetime('now'),
                           last_validated_status = ?, fhir_version = COALESCE(?, fhir_version)
                           WHERE id = ?""",
                         (r['classification'], r['fhir_version'], r['payer_id']))

    conn.commit()
    conn.close()

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total payers tested: {total}")
    print(f"Tested at: {datetime.now(timezone.utc).isoformat()}")
    print()
    for cls, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count * 100 / total
        print(f"  {cls:25s}: {count:4d} ({pct:.1f}%)")
    print()
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == '__main__':
    run()
