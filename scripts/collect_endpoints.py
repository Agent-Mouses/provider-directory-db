"""
Collect payer Provider Directory API endpoints from:
1. ONC Lantern (healthit.gov) - daily endpoint data
2. Known payer developer portals (hardcoded seed data)
3. CMS NPPES as supplementary org data
"""
import sqlite3
import requests
import csv
import io
import os
import time
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')

LANTERN_ENDPOINTS_URL = "https://lantern.healthit.gov/api/daily/download"
LANTERN_ORGS_URL = "https://lantern.healthit.gov/api/organizations/v1"

# Known payer endpoints from public documentation and Defacto research
KNOWN_PAYERS = [
    {
        "org_name": "Aetna / CVS Health",
        "portal_url": "https://developerportal.aetna.com/",
        "api_base": "https://vteapif1.aetna.com/fhirdirectory/v1/patientaccess/",
        "requires_registration": 1,
        "auth_type": "API Key (register on portal)",
        "source": "developer_portal",
    },
    {
        "org_name": "UnitedHealthcare",
        "portal_url": "https://www.uhc.com/legal/interoperability-apis",
        "api_base": "https://fhir.uhc.com/v1/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Humana",
        "portal_url": "https://developers.humana.com/",
        "api_base": "https://fhir.humana.com/api/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Elevance Health (Anthem)",
        "portal_url": "https://developer.anthem.com/",
        "api_base": "https://fhir.anthem.com/provider-directory/v1/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Molina Healthcare",
        "portal_url": "https://developer.molinahealthcare.com/",
        "api_base": "https://fhir.molinahealthcare.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Kaiser Permanente",
        "portal_url": "https://developer.kp.org/",
        "api_base": "https://api.kp.org/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Centene (WellCare)",
        "note": "Missing Practitioner-plan relationships per Defacto 2024",
        "portal_url": "https://developer.centene.com/",
        "api_base": "https://fhir.centene.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "CareSource",
        "portal_url": "https://developer.caresource.com/",
        "api_base": "https://fhir.caresource.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Cigna / Evernorth",
        "portal_url": "https://developer.cigna.com/",
        "api_base": "https://fhir.cigna.com/ProviderDirectory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Blue Cross Blue Shield of Massachusetts",
        "portal_url": "https://developer.bluecrossma.com/",
        "api_base": "https://fhir.bluecrossma.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "HealthPartners",
        "portal_url": "https://developerportal.healthpartners.com/provider-directory",
        "api_base": "https://api-developerportal.healthpartners.com/interop/external/fhir",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "L.A. Care Health Plan",
        "portal_url": "https://developer.lacare.org/",
        "api_base": "https://fhir.lacare.org/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (no auth)",
        "source": "developer_portal",
    },
    {
        "org_name": "Amerihealth Caritas",
        "portal_url": "https://developer.amerihealthcaritas.com/",
        "api_base": "https://fhir.amerihealthcaritas.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Colorado Medicaid (HCPF)",
        "portal_url": "https://www.colorado.gov/hcpf/interoperability",
        "api_base": "https://fhir.colorado.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (no auth)",
        "source": "state_medicaid",
    },
    {
        "org_name": "Abilis Health (HMO SNP)",
        "note": "No machine readable API",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "UPMC Health Plan",
        "note": "Missing Practitioner-plan relationships per Defacto 2024",
        "portal_url": "https://developer.upmchealthplan.com/",
        "api_base": "https://fhir.upmchealthplan.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "developer_portal",
    },
    {
        "org_name": "Healthfirst (NY)",
        "note": "Missing Practitioner-plan relationships per Defacto 2024",
        "portal_url": "https://developer.healthfirst.org/",
        "api_base": "https://fhir.healthfirst.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Florida Medicaid",
        "note": "No API available as of 2024",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Illinois Medicaid",
        "note": "No API available as of 2024",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Pennsylvania Medicaid",
        "note": "No API available as of 2024",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "CalOptima",
        "note": "Missing Practitioner-plan relationships per Defacto 2024",
        "portal_url": "https://developer.caloptima.org/",
        "api_base": "https://fhir.caloptima.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Inland Empire Health Plan",
        "note": "Missing Practitioner-plan relationships per Defacto 2024",
        "portal_url": "https://developer.iehp.org/",
        "api_base": "https://fhir.iehp.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "BlueCross BlueShield of Tennessee",
        "note": "Missing data - only Exchange plans showing per Defacto 2024",
        "portal_url": "https://developer.bcbst.com/",
        "api_base": "https://fhir.bcbst.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
        "source": "developer_portal",
    },
    {
        "org_name": "Michigan Medicaid",
        "note": "Missing NPIs per Defacto 2024",
        "portal_url": "https://developer.michigan.gov/medicaid/",
        "api_base": "https://fhir.michigan.gov/medicaid/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (no auth)",
        "source": "state_medicaid",
    },
    {
        "org_name": "Medicare Fee-for-Service (CMS)",
        "portal_url": "https://developer.cms.gov/",
        "api_base": "https://bcda.cms.gov/",
        "note": "BCDA provides claims data; provider directory via NPPES/PECOS",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
        "source": "cms",
    },
    {
        "org_name": "Department of Veterans Affairs",
        "portal_url": "https://developer.va.gov/",
        "api_base": "https://api.va.gov/services/provider-directory/v1/",
        "requires_registration": 1,
        "auth_type": "API Key (developer.va.gov)",
        "source": "federal",
    },
]


def get_db():
    return sqlite3.connect(DB_PATH)


def upsert_payer(conn, payer: dict):
    """Insert or update a payer record."""
    cols = [
        'org_tin', 'org_name', 'note', 'plan_name', 'portal_url', 'api_base',
        'endpoint_insurance_plan', 'endpoint_practitioner', 'endpoint_practitioner_role',
        'endpoint_organization', 'endpoint_organization_affiliation', 'endpoint_location',
        'endpoint_healthcare_service', 'endpoint_network', 'endpoint_endpoint',
        'requires_registration', 'requires_api_key', 'auth_type', 'source'
    ]
    # Build values from payer dict, defaulting to None
    values = [payer.get(c) for c in cols]
    placeholders = ', '.join(['?'] * len(cols))
    col_names = ', '.join(cols)
    update_clause = ', '.join([f"{c}=excluded.{c}" for c in cols if c != 'org_name'])

    sql = f"""
        INSERT INTO payers ({col_names})
        VALUES ({placeholders})
        ON CONFLICT(org_name, plan_name) DO UPDATE SET
        {update_clause},
        updated_at=datetime('now')
    """
    conn.execute(sql, values)


def collect_from_lantern():
    """Try to fetch endpoint data from ONC Lantern."""
    print("Fetching from Lantern API...")
    payers = []
    try:
        resp = requests.get(LANTERN_ENDPOINTS_URL, timeout=30)
        if resp.status_code == 200:
            # Lantern returns CSV
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                # Filter for provider directory endpoints
                url = row.get('url', '') or row.get('URL', '')
                org = row.get('organization_name', '') or row.get('Organization Name', '')
                if not url or not org:
                    continue
                payers.append({
                    'org_name': org,
                    'api_base': url,
                    'fhir_version': row.get('fhir_version', '') or row.get('FHIR Version', ''),
                    'source': 'lantern',
                })
            print(f"  Got {len(payers)} endpoints from Lantern")
        else:
            print(f"  Lantern returned {resp.status_code}, skipping")
    except Exception as e:
        print(f"  Lantern unavailable: {e}")
    return payers


def collect_known_payers():
    """Return hardcoded known payer data."""
    print(f"Loading {len(KNOWN_PAYERS)} known payer records...")
    # For payers with api_base, derive individual resource endpoints
    enriched = []
    for p in KNOWN_PAYERS:
        payer = dict(p)
        base = payer.get('api_base', '')
        if base:
            base = base.rstrip('/')
            payer.setdefault('endpoint_practitioner', f"{base}/Practitioner")
            payer.setdefault('endpoint_practitioner_role', f"{base}/PractitionerRole")
            payer.setdefault('endpoint_organization', f"{base}/Organization")
            payer.setdefault('endpoint_organization_affiliation', f"{base}/OrganizationAffiliation")
            payer.setdefault('endpoint_location', f"{base}/Location")
            payer.setdefault('endpoint_healthcare_service', f"{base}/HealthcareService")
            payer.setdefault('endpoint_insurance_plan', f"{base}/InsurancePlan")
            payer.setdefault('endpoint_network', f"{base}/Network")
            payer.setdefault('endpoint_endpoint', f"{base}/Endpoint")
        enriched.append(payer)
    return enriched


def run():
    conn = get_db()
    # Seed known payers
    payers = collect_known_payers()
    # Try Lantern
    lantern_payers = collect_from_lantern()
    payers.extend(lantern_payers)

    inserted = 0
    for p in payers:
        try:
            upsert_payer(conn, p)
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {p.get('org_name')}: {e}")
    conn.commit()
    conn.close()
    print(f"Done. {inserted} payer records upserted into database.")


if __name__ == '__main__':
    run()
