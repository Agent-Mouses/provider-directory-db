#!/usr/bin/env python3
"""
audit_data_quality.py — Verify payer APIs serve REAL provider data (not dummy/empty).

For each payer with an accessible endpoint:
1. Query /Practitioner?_count=5
2. Extract NPIs from results
3. Verify NPIs against CMS NPPES Registry
4. Record: data_quality_flag, sample_npi, npi_verified, practitioner_count

Updates payers table with:
  - data_quality_flag: VERIFIED_REAL | UNVERIFIABLE | EMPTY | NO_API | AUTH_WALL
  - data_quality_sample_npi: a verified NPI from the response
  - data_quality_practitioner_count: total practitioners reported
  - data_quality_checked: date of last check

Usage:
  python scripts/audit_data_quality.py          # audit all
  python scripts/audit_data_quality.py --id 50  # audit one payer
  python scripts/audit_data_quality.py --open   # only open-access payers
"""

import sqlite3
import urllib.request
import urllib.parse
import ssl
import json
import time
import argparse
import sys
from datetime import datetime

DB_PATH = "data/provider_directory.db"
NPPES_API = "https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi}"
TIMEOUT = 15
DELAY = 0.5

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'Accept': 'application/fhir+json, application/json',
    'User-Agent': 'GWU-Mullan-Institute-FHIR-Auditor/1.0 (research@gwu.edu)'
}


def fetch_json(url, timeout=TIMEOUT):
    """Fetch URL and return parsed JSON or None."""
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    body = resp.read().decode('utf-8', errors='replace')
    return json.loads(body)


def query_practitioners(api_base, count=5):
    """Query Practitioner resource, return (total, entries) or raise."""
    url = f"{api_base.rstrip('/')}/Practitioner?_count={count}"
    data = fetch_json(url)
    if not isinstance(data, dict):
        return None, []
    total = data.get('total')
    entries = data.get('entry', [])
    return total, entries


def extract_npis(entries):
    """Extract NPI numbers from FHIR Practitioner entries."""
    npis = []
    for entry in entries:
        resource = entry.get('resource', {})
        for ident in resource.get('identifier', []):
            if ident.get('system') == 'http://hl7.org/fhir/sid/us-npi':
                npi = ident.get('value', '')
                if len(npi) == 10 and npi.isdigit():
                    npis.append(npi)
                    break
    return npis


def verify_npi(npi):
    """Check NPI against NPPES Registry. Returns (name, state) or None."""
    try:
        url = NPPES_API.format(npi=npi)
        data = fetch_json(url, timeout=10)
        results = data.get('results', [])
        if results:
            basic = results[0].get('basic', {})
            name = f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
            addresses = results[0].get('addresses', [])
            state = ''
            for addr in addresses:
                if addr.get('address_purpose') == 'LOCATION':
                    state = addr.get('state', '')
                    break
            return name, state
    except:
        pass
    return None


def audit_payer(pid, org_name, api_base, current_status):
    """Audit a single payer. Returns dict of fields to update."""
    result = {
        'data_quality_checked': datetime.now().strftime('%Y-%m-%d'),
        'data_quality_flag': None,
        'data_quality_sample_npi': None,
        'data_quality_practitioner_count': None,
    }

    if api_base in (None, '', 'N/A'):
        result['data_quality_flag'] = 'NO_API'
        return result

    # Try to query practitioners
    try:
        total, entries = query_practitioners(api_base)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            result['data_quality_flag'] = 'AUTH_WALL'
            return result
        else:
            result['data_quality_flag'] = 'UNVERIFIABLE'
            return result
    except json.JSONDecodeError:
        # Server returns non-JSON (e.g., HTML login page)
        result['data_quality_flag'] = 'AUTH_WALL'
        return result
    except Exception:
        result['data_quality_flag'] = 'UNVERIFIABLE'
        return result

    if not entries:
        result['data_quality_flag'] = 'EMPTY'
        result['data_quality_practitioner_count'] = 0
        return result

    result['data_quality_practitioner_count'] = total if total else len(entries)

    # Extract and verify NPIs
    npis = extract_npis(entries)
    if not npis:
        result['data_quality_flag'] = 'NO_NPI'
        return result

    # Verify first NPI against NPPES
    verified = verify_npi(npis[0])
    if verified:
        result['data_quality_flag'] = 'VERIFIED_REAL'
        result['data_quality_sample_npi'] = npis[0]
    else:
        result['data_quality_flag'] = 'NPI_NOT_FOUND'
        result['data_quality_sample_npi'] = npis[0]

    return result


def main():
    parser = argparse.ArgumentParser(description='Audit payer data quality')
    parser.add_argument('--id', type=int, help='Audit single payer by ID')
    parser.add_argument('--open', action='store_true', help='Only audit open-access payers')
    parser.add_argument('--all', action='store_true', help='Audit all payers')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Ensure columns exist
    for col in ['data_quality_flag', 'data_quality_sample_npi', 'data_quality_practitioner_count', 'data_quality_checked']:
        try:
            c.execute(f"ALTER TABLE payers ADD COLUMN {col} TEXT")
        except:
            pass

    # Select payers to audit
    if args.id:
        c.execute("SELECT id, org_name, api_base, last_validated_status FROM payers WHERE id = ?", (args.id,))
    elif args.open:
        c.execute("""SELECT id, org_name, api_base, last_validated_status FROM payers 
            WHERE last_validated_status IN ('valid', 'valid_non_fhir')
            AND api_base IS NOT NULL AND api_base != 'N/A'""")
    else:
        c.execute("""SELECT id, org_name, api_base, last_validated_status FROM payers 
            WHERE api_base IS NOT NULL AND api_base != 'N/A'
            ORDER BY id""")

    payers = c.fetchall()
    print(f"Auditing {len(payers)} payers...\n")

    stats = {}
    for i, (pid, name, api_base, status) in enumerate(payers):
        if i % 25 == 0 and i > 0:
            print(f"  Progress: {i}/{len(payers)}")

        result = audit_payer(pid, name, api_base, status)
        flag = result['data_quality_flag']
        stats[flag] = stats.get(flag, 0) + 1

        # Update DB
        c.execute("""UPDATE payers SET 
            data_quality_flag = ?,
            data_quality_sample_npi = ?,
            data_quality_practitioner_count = ?,
            data_quality_checked = ?
            WHERE id = ?""", (
            result['data_quality_flag'],
            result['data_quality_sample_npi'],
            str(result['data_quality_practitioner_count']) if result['data_quality_practitioner_count'] else None,
            result['data_quality_checked'],
            pid
        ))

        if flag == 'VERIFIED_REAL':
            print(f"  ✅ {name}: REAL (NPI {result['data_quality_sample_npi']} verified)")
        elif flag == 'EMPTY':
            print(f"  ⚠️  {name}: EMPTY response")

        time.sleep(DELAY)

    conn.commit()

    # Handle no_api payers
    c.execute("UPDATE payers SET data_quality_flag = 'NO_API', data_quality_checked = ? WHERE last_validated_status = 'no_api' AND data_quality_flag IS NULL", (datetime.now().strftime('%Y-%m-%d'),))

    conn.commit()

    print(f"\n{'='*60}")
    print("AUDIT COMPLETE")
    print(f"{'='*60}")
    for flag, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {flag}: {count}")

    conn.close()


if __name__ == '__main__':
    main()
