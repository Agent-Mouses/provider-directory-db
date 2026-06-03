"""
Validate Provider Directory API endpoints by hitting /metadata (FHIR CapabilityStatement).
Records results in validation_log table.
"""
import sqlite3
import requests
import os
import time
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_endpoint(api_base: str, timeout: int = 15) -> dict:
    """Hit [base]/metadata and return validation result."""
    url = api_base.rstrip('/') + '/metadata'
    start = time.time()
    try:
        resp = requests.get(url, timeout=timeout, headers={'Accept': 'application/fhir+json'})
        elapsed = int((time.time() - start) * 1000)
        result = {
            'endpoint_url': url,
            'status_code': resp.status_code,
            'response_time_ms': elapsed,
            'is_valid': 1 if resp.status_code == 200 else 0,
            'error': None,
        }
        if resp.status_code == 200:
            try:
                data = resp.json()
                result['fhir_version'] = data.get('fhirVersion', '')
            except Exception:
                result['fhir_version'] = ''
        return result
    except requests.exceptions.Timeout:
        return {'endpoint_url': url, 'status_code': None, 'response_time_ms': timeout * 1000,
                'is_valid': 0, 'fhir_version': '', 'error': 'timeout'}
    except requests.exceptions.ConnectionError as e:
        return {'endpoint_url': url, 'status_code': None, 'response_time_ms': 0,
                'is_valid': 0, 'fhir_version': '', 'error': f'connection_error: {str(e)[:100]}'}
    except Exception as e:
        return {'endpoint_url': url, 'status_code': None, 'response_time_ms': 0,
                'is_valid': 0, 'fhir_version': '', 'error': str(e)[:200]}


def run(limit: int = 0):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, org_name, api_base FROM payers WHERE api_base IS NOT NULL AND api_base != ''"
    ).fetchall()

    if limit:
        rows = rows[:limit]

    print(f"Validating {len(rows)} endpoints...")
    for row in rows:
        payer_id, org_name, api_base = row['id'], row['org_name'], row['api_base']
        print(f"  {org_name:40s} ... ", end='', flush=True)
        result = check_endpoint(api_base)

        # Log to validation_log
        conn.execute("""
            INSERT INTO validation_log (payer_id, endpoint_url, status_code, response_time_ms,
                                        fhir_version, is_valid, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (payer_id, result['endpoint_url'], result['status_code'],
              result['response_time_ms'], result.get('fhir_version', ''),
              result['is_valid'], result['error']))

        # Update payer record
        conn.execute("""
            UPDATE payers SET last_validated = datetime('now'),
                              last_validated_status = ?,
                              fhir_version = COALESCE(?, fhir_version)
            WHERE id = ?
        """, ('valid' if result['is_valid'] else f"error:{result.get('error') or result.get('status_code')}",
              result.get('fhir_version'), payer_id))

        status = f"✅ {result['status_code']} ({result['response_time_ms']}ms)" if result['is_valid'] \
            else f"❌ {result.get('error') or result.get('status_code')}"
        print(status)
        time.sleep(1)  # Be polite

    conn.commit()
    conn.close()
    print("Validation complete.")


if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run(limit)
