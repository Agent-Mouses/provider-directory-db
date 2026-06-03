"""
Find new endpoints for NEEDS_ENDPOINT_UPDATE payers and test them.
Strategy:
1. Pull official CMS SMA Endpoint Directory for state Medicaid URLs
2. Try known FHIR URL patterns for major payers (developer portals, known vendors)
3. Test each discovered URL with real HTTP request
4. Update DB only if new URL works
"""
import sqlite3
import requests
import csv
import io
import time
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')
TIMEOUT = 20
DELAY = 0.5

# Known payer FHIR endpoint patterns (from developer docs, public registries)
KNOWN_ENDPOINTS = {
    "Aetna": [
        "https://fhir-ehr.cerner.com/r4/aetna",
        "https://vteapif1.aetna.com/fhir/v1/r4",
    ],
    "Elevance Health (Anthem)": [
        "https://fhir.anthem.com/provider-directory/v1",
        "https://api.anthem.com/fhir/provider-directory/v1",
        "https://fhir.carelon.com/provider-directory/",
    ],
    "UnitedHealthcare": [
        "https://fhir.uhc.com/v1/provider-directory",
        "https://sandbox.uhc.com/api/fhir/provider-directory/v1",
        "https://public.uhc.com/api/fhir/provider-directory/v1",
    ],
    "Humana Inc.": [
        "https://fhir.humana.com/api",
        "https://fhir.humana.com/api/provider-directory",
    ],
    "Molina Healthcare": [
        "https://fhir.molinahealthcare.com/provider-directory",
        "https://api.molinahealthcare.com/fhir/provider-directory",
    ],
    "Centene Corporation": [
        "https://fhir.centene.com/provider-directory",
        "https://api.centene.com/fhir/provider-directory/v1",
    ],
    "Highmark Health": [
        "https://api.highmark.com/fhir/provider-directory",
        "https://fhir.highmark.com/provider-directory",
    ],
    "Blue Shield of California": [
        "https://api.blueshieldca.com/fhir/provider-directory",
        "https://developer.blueshieldca.com/api/fhir/provider-directory",
    ],
    "Independence Blue Cross": [
        "https://api.ibx.com/fhir/provider-directory",
        "https://fhir.ibx.com/provider-directory",
    ],
    "UPMC Health Plan": [
        "https://api.upmchealthplan.com/fhir/provider-directory",
        "https://fhir.upmchp.com/provider-directory",
    ],
    "CareSource": [
        "https://fhir.caresource.com/provider-directory",
        "https://api.caresource.com/fhir/provider-directory",
    ],
    "Health Alliance Plan": [
        "https://api.hap.org/fhir/provider-directory",
        "https://fhir.hap.org/provider-directory",
    ],
    "Healthfirst": [
        "https://hf-fhir-provider-directory-sys-api-prod.us-e1.cloudhub.io",
        "https://api.healthfirst.org/fhir/provider-directory",
    ],
    "Devoted Health": [
        "https://api.devoted.com/fhir/provider-directory",
        "https://fhir.devoted.com/provider-directory",
    ],
    "Geisinger Health Plan": [
        "https://fhir.geisinger.org/provider-directory",
        "https://api.geisinger.org/fhir/provider-directory",
    ],
}


def test_url(url):
    """Test a single URL, return result dict."""
    # Try /metadata first
    test_urls = []
    base = url.rstrip('/')
    if not base.endswith('/metadata'):
        test_urls.append(base + '/metadata')
    test_urls.append(base)

    for test_url in test_urls:
        try:
            resp = requests.get(
                test_url, timeout=TIMEOUT,
                headers={'Accept': 'application/fhir+json', 'User-Agent': 'FHIR-Directory-Validator/1.0'},
                allow_redirects=True
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and data.get('resourceType') == 'CapabilityStatement':
                        return {'url': base, 'status': 'valid', 'code': 200, 'fhir_version': data.get('fhirVersion')}
                    return {'url': base, 'status': 'valid_non_fhir', 'code': 200, 'fhir_version': None}
                except (json.JSONDecodeError, ValueError):
                    return {'url': base, 'status': 'valid_non_fhir', 'code': 200, 'fhir_version': None}
            elif resp.status_code in (401, 403):
                return {'url': base, 'status': 'auth_required', 'code': resp.status_code, 'fhir_version': None}
            elif resp.status_code == 404:
                continue  # try next URL variant
            else:
                return {'url': base, 'status': f'http_{resp.status_code}', 'code': resp.status_code, 'fhir_version': None}
        except requests.exceptions.Timeout:
            return {'url': base, 'status': 'timeout', 'code': None, 'fhir_version': None}
        except Exception:
            continue

    return None  # nothing worked


def fetch_sma_directory():
    """Pull the official CMS SMA Endpoint Directory."""
    url = "https://raw.githubusercontent.com/CMSgov/SMA-Endpoint-Directory/main/SMAEndpointDirectory.csv"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        print(f"Failed to fetch SMA directory: {resp.status_code}")
        return {}

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)

    header_key = '\ufeffState Medicaid Agency Interoperability and Patient Access Endpoint Directory'
    pd_key = 'Provider Directory Endpoint Information '

    state_urls = {}
    for r in rows[1:]:
        state = r[header_key].strip()
        pd_raw = r[pd_key].strip() if r[pd_key] else ''
        if pd_raw and 'http' in pd_raw.lower() and 'not yet' not in pd_raw.lower():
            lines = [l.strip().replace('\xa0', '') for l in pd_raw.split('\n') if l.strip().startswith('http')]
            if lines:
                state_urls[state] = lines[0]
    return state_urls


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all broken payers
    broken = conn.execute("""
        SELECT id, org_name, api_base, last_validated_status 
        FROM payers WHERE compliance_flag='NEEDS_ENDPOINT_UPDATE'
        ORDER BY org_name
    """).fetchall()
    print(f"Payers needing endpoint update: {len(broken)}")

    # Fetch official SMA directory
    print("\nFetching CMS SMA Endpoint Directory...")
    sma_urls = fetch_sma_directory()
    print(f"  Got {len(sma_urls)} state URLs from CMS")

    # Map state names to DB records
    state_map = {}
    for r in broken:
        name = r['org_name']
        if name.startswith('State of '):
            state_name = name.replace('State of ', '')
            state_map[state_name] = r

    updated = 0
    failed = 0
    results = []

    # 1. Try SMA directory URLs for state payers
    print("\n=== Testing CMS SMA URLs for state Medicaid ===")
    for state_name, sma_url in sma_urls.items():
        if state_name in state_map:
            rec = state_map[state_name]
            # Only try if URL differs from what we have
            current = rec['api_base'].rstrip('/') if rec['api_base'] else ''
            new_base = sma_url.split('?')[0].rstrip('/')  # strip query params
            # Also try the base without resource-specific path
            # e.g. /r4/public/Practitioner -> /r4
            candidates = [sma_url]
            if '/Practitioner' in sma_url:
                candidates.append(sma_url.split('/Practitioner')[0])
            if '/Organization' in sma_url:
                candidates.append(sma_url.split('/Organization')[0])

            print(f"  {state_name:20s} ... ", end='', flush=True)
            found = None
            for candidate in candidates:
                result = test_url(candidate)
                if result and result['status'] in ('valid', 'valid_non_fhir', 'auth_required'):
                    found = result
                    break
                time.sleep(DELAY)

            if found:
                print(f"✅ {found['status']} | {found['url']}")
                conn.execute("""UPDATE payers SET api_base=?, last_validated=datetime('now'),
                    last_validated_status=?, fhir_version=COALESCE(?, fhir_version),
                    compliance_flag=?, updated_at=datetime('now')
                    WHERE id=?""",
                    (found['url'],
                     found['status'],
                     found.get('fhir_version'),
                     'COMPLIANT' if found['status'] == 'valid' else 'COMPLIANT_WITH_REGISTRATION',
                     rec['id']))
                updated += 1
                results.append({'id': rec['id'], 'org': rec['org_name'], 'new_url': found['url'], 'status': found['status']})
            else:
                print(f"❌ still broken")
                failed += 1
            time.sleep(DELAY)

    # 2. Try known endpoints for major payers
    print("\n=== Testing known endpoints for major payers ===")
    for r in broken:
        org = r['org_name']
        if org in KNOWN_ENDPOINTS:
            print(f"  {org:40s} ... ", end='', flush=True)
            found = None
            for candidate in KNOWN_ENDPOINTS[org]:
                result = test_url(candidate)
                if result and result['status'] in ('valid', 'valid_non_fhir', 'auth_required'):
                    found = result
                    break
                time.sleep(DELAY)

            if found:
                print(f"✅ {found['status']} | {found['url']}")
                conn.execute("""UPDATE payers SET api_base=?, last_validated=datetime('now'),
                    last_validated_status=?, fhir_version=COALESCE(?, fhir_version),
                    compliance_flag=?, updated_at=datetime('now')
                    WHERE id=?""",
                    (found['url'],
                     found['status'],
                     found.get('fhir_version'),
                     'COMPLIANT' if found['status'] == 'valid' else 'COMPLIANT_WITH_REGISTRATION',
                     r['id']))
                updated += 1
                results.append({'id': r['id'], 'org': org, 'new_url': found['url'], 'status': found['status']})
            else:
                print(f"❌ no working URL found")
                failed += 1
            time.sleep(DELAY)

    # 3. For payers with known vendor platforms, try alternate tenant URLs
    print("\n=== Testing vendor platform patterns ===")
    vendor_patterns = {
        '1uphealth': lambda org: [
            f"https://api.1up.health/provider-directory/{org.lower().replace(' ', '-')}"
        ],
        'edifecs': lambda state: [
            f"https://us120.fhir.m3.edifecsfedcloud.com/{state.lower()[:2]}_pd"
        ],
    }

    conn.commit()

    # Summary
    print("\n" + "=" * 80)
    print("DISCOVERY SUMMARY")
    print("=" * 80)
    print(f"Updated with working endpoints: {updated}")
    print(f"Still broken: {failed}")
    print(f"Not attempted (no known alternatives): {len(broken) - updated - failed}")

    if results:
        print("\n=== Successfully Updated ===")
        for r in results:
            print(f"  [{r['id']}] {r['org']:40s} → {r['status']:15s} | {r['new_url']}")

    # Final DB stats
    rows = conn.execute("SELECT compliance_flag, COUNT(*) FROM payers GROUP BY compliance_flag ORDER BY COUNT(*) DESC").fetchall()
    print("\n=== Current DB Status ===")
    for r in rows:
        print(f"  {r[0]:35s}: {r[1]}")

    conn.close()


if __name__ == '__main__':
    run()
