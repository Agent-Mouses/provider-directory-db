"""
Deep scraper: discover and verify all CMS Provider Directory FHIR API endpoints.

Sources:
1. Known payer developer portals (direct scrape for base URLs)
2. Edifecs Federal Data Portal (many Medicaid/small payers)
3. 1upHealth hosted endpoints
4. Onyx Health hosted endpoints
5. Common URL pattern probing
6. CMS/ONC published endpoint lists
"""
import sqlite3
import requests
import json
import re
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')
TIMEOUT = 20
HEADERS = {'Accept': 'application/fhir+json, application/json'}

# ─── SOURCE 1: Edifecs Federal Data Portal ───────────────────────────────────
# Many Medicaid plans use Edifecs cloud. The portal page lists all tenants.
EDIFECS_BASE = "https://fdp.edifecsfedcloud.com"
EDIFECS_TENANTS = [
    "alameda.alliance.for.health", "caloptima", "cencal.health",
    "central.california.alliance", "cook.childrens", "denver.health",
    "florida.blue", "gold.coast.health.plan", "health.plan.of.san.joaquin",
    "la.care", "north.dakota.medicaid", "partnership.healthplan",
    "san.francisco.health.plan", "santa.clara.family.health.plan",
    "sfhp", "texas.childrens", "texas.medicaid", "triple.s",
    "careoregon", "health.plan.of.san.mateo", "calviva",
    "kern.health.systems", "inland.empire.health.plan",
]

# ─── SOURCE 2: Known developer portals to probe ─────────────────────────────
PORTAL_PROBES = [
    # (org_name, base_url_to_try, portal_url)
    ("AllCare Health", "https://fhir.allcarehealth.com/r4/", "https://devportal.allcarehealth.com/"),
    ("Devoted Health", "https://api.devoted.com/fhir/r4/", "https://www.devoted.com/developers/"),
    ("Health Alliance Plan (HAP)", "https://api.hap.org/fhir/r4/", "https://developer.hap.org/"),
    ("Healthfirst", "https://hf-fhir-provider-directory-sys-api-prod.us-e1.cloudhub.io/", "https://interoperability.healthfirst.org/"),
    ("CareFirst BlueCross BlueShield", "https://api.carefirst.com/fhir/provider-directory/", "https://developer.carefirst.com/"),
    ("Excellus BCBS", "https://api.excellusbcbs.com/fhir/r4/", "https://news.excellusbcbs.com/developer-info/"),
    ("Blue Shield of California", "https://api.blueshieldca.com/fhir/r4/", "https://devportal-dev.blueshieldca.com/"),
    ("SCAN Health Plan", "https://fhir.scanhealthplan.com/r4/", "https://developer.scanhealthplan.com/"),
    ("Point32Health", "https://fhir.point32health.org/r4/", "https://developer.point32health.org/"),
    ("Geisinger", "https://fhir.geisinger.org/r4/", "https://developer.geisinger.org/"),
    ("Priority Health", "https://fhir.priorityhealth.com/r4/", "https://developer.priorityhealth.com/"),
    ("EmblemHealth", "https://fhir.emblemhealth.com/r4/", "https://developer.emblemhealth.com/"),
    ("UPMC Health Plan", "https://api.upmchealthplan.com/fhir/r4/", "https://developer.upmchealthplan.com/"),
    ("Highmark", "https://api.highmark.com/fhir/r4/", "https://developer.highmark.com/"),
    ("Independence Blue Cross", "https://api.ibx.com/fhir/r4/", "https://developer.ibx.com/"),
    ("Horizon BCBS NJ", "https://fhir.horizonblue.com/r4/", "https://developer.horizonblue.com/"),
    ("Cigna", "https://fhir.cigna.com/ProviderDirectory/v1/", "https://developer.cigna.com/"),
    ("SelectHealth", "https://fhir.selecthealth.org/r4/", "https://developer.selecthealth.org/"),
    ("MVP Health Care", "https://fhir.mvphealthcare.com/r4/", "https://developer.mvphealthcare.com/"),
    ("Medica", "https://fhir.medica.com/r4/", "https://developer.medica.com/"),
    ("UCare", "https://fhir.ucare.org/r4/", "https://developer.ucare.org/"),
    ("Community Health Group", "https://api.onyxhealth.io/fhir/chg/r4/", "https://developer.chgsd.com/"),
    ("IEHP", "https://fhir.iehp.org/r4/", "https://fhir.iehp.org/devportal/"),
    ("Maine Medicaid", "https://fhir.maine.gov/r4/", "https://www.maine.gov/dhhs/oms/providers/provider-directory-api"),
    ("Washington Medicaid", "https://fhir.wa.gov/r4/", "https://www.hca.wa.gov/"),
]

# ─── SOURCE 3: 1upHealth hosted endpoints ────────────────────────────────────
# 1upHealth hosts many payer APIs. Common pattern: https://fhir.1up.health/{tenant}/
ONEUP_PATTERN = "https://api.1up.health/fhir/r4/"

# ─── SOURCE 4: Common URL patterns to probe ──────────────────────────────────
# Many payers follow predictable FHIR URL patterns
PATTERN_PROBES = [
    "https://fhir.{slug}.com/r4/metadata",
    "https://api.{slug}.com/fhir/r4/metadata",
    "https://fhir.{slug}.org/r4/metadata",
    "https://{slug}.fhir.1up.health/metadata",
]

PAYER_SLUGS = [
    "aetna", "anthem", "bcbsal", "bcbsil", "bcbsmn", "bcbsnc", "bcbsnm",
    "bcbst", "bcbstx", "bluecrossmn", "blueshieldca", "carefirst",
    "caresource", "centene", "cigna", "emblemhealth", "excellusbcbs",
    "floridablue", "geisinger", "hap", "healthfirst", "highmark",
    "horizonblue", "humana", "ibx", "kaiser", "medica", "metroplus",
    "molina", "molinahealthcare", "mvphealthcare", "point32health",
    "priorityhealth", "scanhealthplan", "selecthealth", "sentara",
    "ucare", "uhc", "unitedhealth", "upmchealthplan", "wellsense",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_metadata(url, timeout=TIMEOUT):
    """Hit a FHIR /metadata endpoint and parse the CapabilityStatement."""
    meta_url = url.rstrip('/') + '/metadata' if '/metadata' not in url else url
    try:
        resp = requests.get(meta_url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('resourceType') == 'CapabilityStatement':
                return {
                    'url': url.rstrip('/').replace('/metadata', ''),
                    'status': 'valid',
                    'fhir_version': data.get('fhirVersion', ''),
                    'status_code': 200,
                    'software': data.get('software', {}).get('name', ''),
                    'resources': [r.get('type') for r in data.get('rest', [{}])[0].get('resource', [])],
                }
        return {'url': url, 'status': 'error', 'status_code': resp.status_code}
    except requests.exceptions.Timeout:
        return {'url': url, 'status': 'timeout'}
    except Exception as e:
        return {'url': url, 'status': 'error', 'error': str(e)[:100]}


def discover_edifecs():
    """Probe Edifecs Federal Data Portal tenants."""
    print("─── Probing Edifecs tenants ───")
    results = []
    for tenant in EDIFECS_TENANTS:
        url = f"{EDIFECS_BASE}/fhir/{tenant}"
        print(f"  {tenant:45s} ... ", end='', flush=True)
        result = check_metadata(url)
        if result.get('status') == 'valid':
            print(f"✅ FHIR {result['fhir_version']}")
            result['org_name'] = tenant.replace('.', ' ').title()
            result['portal_url'] = f"{EDIFECS_BASE}/#/portal/{tenant}/home"
            result['auth_type'] = 'Open (Edifecs)'
            result['requires_registration'] = 0
            results.append(result)
        else:
            print(f"❌ {result.get('status_code', result.get('status'))}")
        time.sleep(0.5)
    return results


def discover_portals():
    """Probe known developer portal base URLs."""
    print("\n─── Probing known developer portals ───")
    results = []
    for org_name, base_url, portal_url in PORTAL_PROBES:
        print(f"  {org_name:40s} ... ", end='', flush=True)
        result = check_metadata(base_url)
        if result.get('status') == 'valid':
            print(f"✅ FHIR {result['fhir_version']} | {len(result.get('resources',[]))} resources")
            result['org_name'] = org_name
            result['portal_url'] = portal_url
            results.append(result)
        else:
            print(f"❌ {result.get('status_code', result.get('error', result.get('status')))}")
        time.sleep(0.5)
    return results


def discover_patterns():
    """Probe common URL patterns for payer FHIR endpoints."""
    print("\n─── Probing URL patterns ───")
    results = []
    for slug in PAYER_SLUGS:
        for pattern in PATTERN_PROBES:
            url = pattern.format(slug=slug)
            result = check_metadata(url)
            if result.get('status') == 'valid':
                clean_url = url.replace('/metadata', '')
                print(f"  ✅ FOUND: {clean_url} (FHIR {result['fhir_version']})")
                result['org_name'] = slug.replace('.', ' ').title()
                result['url'] = clean_url
                results.append(result)
                break  # found one pattern for this slug, move on
            time.sleep(0.3)
    return results


def store_results(results):
    """Store discovered endpoints in the database."""
    conn = get_db()
    stored = 0
    for r in results:
        base = r.get('url', '').rstrip('/')
        if not base:
            continue

        # Check if this base URL already exists
        existing = conn.execute("SELECT id FROM payers WHERE api_base = ?", (base + '/',)).fetchone()
        if not existing:
            existing = conn.execute("SELECT id FROM payers WHERE api_base = ?", (base,)).fetchone()

        resources = r.get('resources', [])
        ep = lambda res: f"{base}/{res}" if res in resources else None

        if existing:
            # Update existing record with validation results
            conn.execute("""
                UPDATE payers SET
                    last_validated = datetime('now'),
                    last_validated_status = 'valid',
                    fhir_version = ?,
                    endpoint_practitioner = COALESCE(?, endpoint_practitioner),
                    endpoint_practitioner_role = COALESCE(?, endpoint_practitioner_role),
                    endpoint_organization = COALESCE(?, endpoint_organization),
                    endpoint_location = COALESCE(?, endpoint_location),
                    endpoint_insurance_plan = COALESCE(?, endpoint_insurance_plan),
                    endpoint_healthcare_service = COALESCE(?, endpoint_healthcare_service),
                    endpoint_network = COALESCE(?, endpoint_network),
                    updated_at = datetime('now')
                WHERE id = ?
            """, (r.get('fhir_version'), ep('Practitioner'), ep('PractitionerRole'),
                  ep('Organization'), ep('Location'), ep('InsurancePlan'),
                  ep('HealthcareService'), ep('Network'), existing['id']))
        else:
            # Insert new record
            conn.execute("""
                INSERT INTO payers (org_name, api_base, portal_url, requires_registration, auth_type,
                    fhir_version, last_validated, last_validated_status,
                    endpoint_practitioner, endpoint_practitioner_role, endpoint_organization,
                    endpoint_location, endpoint_insurance_plan, endpoint_healthcare_service,
                    endpoint_network, source)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'valid', ?, ?, ?, ?, ?, ?, ?, 'deep_scrape')
            """, (r.get('org_name', ''), base, r.get('portal_url', ''),
                  r.get('requires_registration', 0), r.get('auth_type', ''),
                  r.get('fhir_version', ''),
                  ep('Practitioner'), ep('PractitionerRole'), ep('Organization'),
                  ep('Location'), ep('InsurancePlan'), ep('HealthcareService'),
                  ep('Network')))
        stored += 1

    conn.commit()
    conn.close()
    return stored


def run():
    print("=" * 70)
    print("DEEP SCRAPE: CMS Provider Directory FHIR API Discovery")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    all_results = []

    # Source 1: Edifecs
    all_results.extend(discover_edifecs())

    # Source 2: Known portals
    all_results.extend(discover_portals())

    # Source 3: Pattern probing
    all_results.extend(discover_patterns())

    # Store results
    print(f"\n{'=' * 70}")
    print(f"Discovery complete. Found {len(all_results)} valid FHIR endpoints.")
    stored = store_results(all_results)
    print(f"Stored/updated {stored} records in database.")

    # Final stats
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM payers").fetchone()[0]
    validated = conn.execute("SELECT COUNT(*) FROM payers WHERE last_validated_status = 'valid'").fetchone()[0]
    print(f"\nDatabase: {total} total rows, {validated} validated as live FHIR endpoints.")
    conn.close()


if __name__ == '__main__':
    run()
