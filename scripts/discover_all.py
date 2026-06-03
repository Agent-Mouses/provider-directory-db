"""
Background endpoint discovery for all unverified organizations.
Run with: nohup python3 scripts/discover_all.py > data/discovery.log 2>&1 &
"""
import sqlite3, requests, time, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

DB_PATH = 'data/provider_directory.db'
HEADERS = {'Accept': 'application/fhir+json, application/json'}
TIMEOUT = 6

def slugify(name):
    name = name.lower()
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)
    for s in [' inc', ' llc', ' corp', ' corporation', ' health plan', ' health plans',
              ' healthcare', ' health care', ' health', ' insurance', ' plan', ' of america',
              ' medical', ' group', ' services', ' systems', ' network']:
        name = name.replace(s, '')
    return re.sub(r'[^a-z0-9]+', '', name.strip())

def probe(org_id, org_name):
    slug = slugify(org_name)
    if len(slug) < 3:
        return None
    urls = [
        f"https://fhir.{slug}.com/r4/metadata",
        f"https://api.{slug}.com/fhir/r4/metadata",
        f"https://fhir.{slug}.org/r4/metadata",
        f"https://interop.{slug}.com/fhir/r4/metadata",
        f"https://developer.{slug}.com/fhir/r4/metadata",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get('resourceType') == 'CapabilityStatement':
                        return (org_id, org_name, url.replace('/metadata',''), 'valid', data.get('fhirVersion',''))
                except: pass
            elif resp.status_code in (401, 403):
                return (org_id, org_name, url.replace('/metadata',''), 'auth', '')
        except: pass
    return None

def main():
    print(f"[{datetime.now().isoformat()}] Starting endpoint discovery...")
    sys.stdout.flush()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    unverified = conn.execute("""
        SELECT id, org_name FROM payers 
        WHERE compliance_flag = 'UNKNOWN' AND (api_base IS NULL OR api_base = '')
    """).fetchall()
    conn.close()

    print(f"[{datetime.now().isoformat()}] Probing {len(unverified)} orgs with 10 threads...")
    sys.stdout.flush()

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(probe, r['id'], r['org_name']): r for r in unverified}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                results.append(result)
                org_id, org_name, base, status, fv = result
                icon = "✅" if status == 'valid' else "🔒"
                print(f"  {icon} [{done}/{len(unverified)}] {org_name:40s} | {base}")
                sys.stdout.flush()
            elif done % 50 == 0:
                print(f"  ... {done}/{len(unverified)} probed ({len(results)} found so far)")
                sys.stdout.flush()

    # Store results
    print(f"\n[{datetime.now().isoformat()}] Storing {len(results)} discoveries...")
    conn = sqlite3.connect(DB_PATH)
    for org_id, org_name, base, status, fv in results:
        if status == 'valid':
            conn.execute("""UPDATE payers SET api_base=?, last_validated=datetime('now'),
                last_validated_status='valid', fhir_version=?, compliance_flag='COMPLIANT',
                violation_type=NULL, violation_detail=NULL,
                endpoint_practitioner=?, endpoint_practitioner_role=?,
                endpoint_organization=?, endpoint_location=?, endpoint_insurance_plan=?
                WHERE id=?""",
                (base, fv, f"{base}/Practitioner", f"{base}/PractitionerRole",
                 f"{base}/Organization", f"{base}/Location", f"{base}/InsurancePlan", org_id))
        else:
            conn.execute("""UPDATE payers SET api_base=?, last_validated=datetime('now'),
                last_validated_status='exists_needs_auth',
                compliance_flag='COMPLIANT_WITH_REGISTRATION', requires_registration=1
                WHERE id=?""", (base, org_id))
    conn.commit()

    # Summary
    total = conn.execute("SELECT COUNT(*) FROM payers").fetchone()[0]
    by_flag = conn.execute("SELECT compliance_flag, COUNT(*) FROM payers GROUP BY compliance_flag").fetchall()
    conn.close()

    live = sum(1 for r in results if r[3] == 'valid')
    auth = sum(1 for r in results if r[3] == 'auth')
    print(f"\n{'='*60}")
    print(f"DISCOVERY COMPLETE: {live} live | {auth} auth-gated | {len(unverified)-live-auth} not found")
    print(f"DB total: {total}")
    for flag, cnt in by_flag:
        print(f"  {flag:35s}: {cnt}")
    print(f"[{datetime.now().isoformat()}] Done.")

if __name__ == '__main__':
    main()
