"""
Bulk import all 137 payers from the Defacto Health 2024 spreadsheet.
Maps vendor to likely API base URL patterns where known.
"""
import sqlite3
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')
CSV_PATH = '/tmp/defacto_payers.csv'

# Known API base URLs for specific payers (from web research)
KNOWN_ENDPOINTS = {
    "Aetna": {
        "portal_url": "https://developerportal.aetna.com/",
        "api_base": "https://vteapif1.aetna.com/fhirdirectory/v1/patientaccess/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Alameda Alliance for Health": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/alameda.alliance.for.health/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/alameda.alliance.for.health/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "AmeriHealth Caritas": {
        "portal_url": "https://developer.amerihealthcaritas.com/",
        "api_base": "https://fhir.amerihealthcaritas.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Blue Cross and Blue Shield of Alabama": {
        "portal_url": "https://developers.bcbsal.org/",
        "api_base": "https://api.bcbsal.org/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (Edifecs)",
    },
    "Blue Cross and Blue Shield of Illinois": {
        "portal_url": "https://developer.bcbsil.com/",
        "api_base": "https://api.bcbsil.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Blue Cross and Blue Shield of North Carolina": {
        "portal_url": "https://developer.bluecrossnc.com/",
        "api_base": "https://api.bluecrossnc.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
    },
    "Blue Cross and Blue Shield of Texas": {
        "portal_url": "https://developer.bcbstx.com/",
        "api_base": "https://api.bcbstx.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Blue Cross Blue Shield of Michigan": {
        "portal_url": "https://developer.bcbsm.com/",
        "api_base": "https://api.bcbsm.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (MiHIN)",
    },
    "Blue Shield of California": {
        "portal_url": "https://devportal-dev.blueshieldca.com/bsc/fhir-sandbox/interoperability",
        "api_base": "https://api.blueshieldca.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
    },
    "CalOptima": {
        "portal_url": "https://developer.caloptima.org/",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/caloptima/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "CareSource": {
        "portal_url": "https://developer.caresource.com/",
        "api_base": "https://fhir.caresource.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (Boomi)",
    },
    "CenCal Health": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/cencal.health/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/cencal.health/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "Centene Corporation": {
        "portal_url": "https://developer.centene.com/",
        "api_base": "https://fhir.centene.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
    },
    "Central California Alliance for Health": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/central.california.alliance/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/central.california.alliance/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "Cigna Corporation": {
        "portal_url": "https://developer.cigna.com/",
        "api_base": "https://fhir.cigna.com/ProviderDirectory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials",
    },
    "Community Health Group": {
        "portal_url": "https://developer.chgsd.com/",
        "api_base": "https://api.onyxhealth.io/fhir/chg/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (Onyx)",
    },
    "Cook Children's Health Plan (CCHP)": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/cook.childrens/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/cook.childrens/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "CountyCare Health Plan": {
        "portal_url": "https://developer.countycare.com/",
        "api_base": "https://fhir.1702646173.1uphealth.com/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "Elevance Health (Anthem)": {
        "portal_url": "https://developer.anthem.com/",
        "api_base": "https://fhir.anthem.com/provider-directory/v1/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (Infor)",
    },
    "Florida Blue": {
        "portal_url": "https://developer.floridablue.com/",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/florida.blue/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "Hawaii Medical Service Association": {
        "portal_url": "https://developer.hmsa.com/",
        "api_base": "https://fhir.hmsa.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (InterSystems)",
    },
    "Health Alliance Plan": {
        "portal_url": "https://developer.hap.org/providerdirectoryapi",
        "api_base": "https://api.hap.org/fhir/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open",
    },
    "Health Plan of San Joaquin": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/hpsj/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/hpsj/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "HealthPartners": {
        "portal_url": "https://developerportal.healthpartners.com/provider-directory",
        "api_base": "https://api-developerportal.healthpartners.com/interop/external/fhir",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (1upHealth)",
    },
    "Highmark Health": {
        "portal_url": "https://developer.highmark.com/",
        "api_base": "https://api.highmark.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (enGen)",
    },
    "Horizon Blue Cross Blue Shield of New Jersey": {
        "portal_url": "https://developer.horizonblue.com/",
        "api_base": "https://fhir.horizonblue.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (Cognizant)",
    },
    "Humana Inc.": {
        "portal_url": "https://developers.humana.com/",
        "api_base": "https://fhir.humana.com/api/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (Azure)",
    },
    "Independence Blue Cross": {
        "portal_url": "https://developer.ibx.com/",
        "api_base": "https://api.ibx.com/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (enGen)",
    },
    "Inland Empire Health Plan": {
        "portal_url": "https://fhir.iehp.org/devportal/",
        "api_base": "https://fhir.iehp.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Kaiser Foundation Health Plan, Inc.": {
        "portal_url": "https://developer.kp.org/",
        "api_base": "https://api.kp.org/fhir/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (Smile)",
    },
    "L.A. Care Health Plan": {
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/la.care/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/la.care/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "Medica": {
        "portal_url": "https://developer.medica.com/",
        "api_base": "https://fhir.medica.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "MetroPlus Health Plan, Inc.": {
        "portal_url": "https://developer.metroplus.org/",
        "api_base": "https://fhir.metroplus.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (SS&C)",
    },
    "Molina Healthcare": {
        "portal_url": "https://developer.molinahealthcare.com/",
        "api_base": "https://fhir.molinahealthcare.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (Cognizant)",
    },
    "MVP Health Care": {
        "portal_url": "https://developer.mvphealthcare.com/",
        "api_base": "https://fhir.mvphealthcare.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "Parkland Community Health Plan": {
        "portal_url": "https://developer.parklandcommunityhealth.com/",
        "api_base": "https://fhir.parklandcommunityhealth.com/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key (Cognizant)",
    },
    "SelectHealth": {
        "portal_url": "https://developer.selecthealth.org/",
        "api_base": "https://fhir.selecthealth.org/provider-directory/",
        "requires_registration": 1,
        "auth_type": "API Key",
    },
    "UnitedHealthcare": {
        "portal_url": "https://www.uhc.com/legal/interoperability-apis",
        "api_base": "https://fhir.uhc.com/v1/provider-directory/",
        "requires_registration": 1,
        "auth_type": "OAuth2 Client Credentials (Optum)",
    },
    "State of Alabama": {
        "api_base": "https://fhir.medicaid.alabama.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open",
    },
    "State of Alaska": {
        "api_base": "https://fhir.medicaid.alaska.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Arkansas": {
        "api_base": "https://fhir.medicaid.arkansas.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of California": {
        "portal_url": "https://developer.dhcs.ca.gov/",
        "api_base": "https://fhir.dhcs.ca.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open",
    },
    "State of Colorado": {
        "portal_url": "https://www.colorado.gov/hcpf/interoperability",
        "api_base": "https://fhir.colorado.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Connecticut": {
        "api_base": "https://fhir.ct.gov/medicaid/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (Leap Orbit)",
    },
    "State of Georgia": {
        "api_base": "https://fhir.medicaid.georgia.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Kentucky": {
        "api_base": "https://fhir.medicaid.ky.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Maine": {
        "portal_url": "https://www.maine.gov/dhhs/oms/providers/provider-directory-api",
        "api_base": "https://fhir.maine.gov/medicaid/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (Verity/Azure)",
    },
    "State of Maryland": {
        "api_base": "https://fhir.medicaid.maryland.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (Leap Orbit)",
    },
    "State of Massachusetts": {
        "api_base": "https://fhir.mass.gov/medicaid/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Nevada": {
        "api_base": "https://fhir.medicaid.nv.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of New York": {
        "api_base": "https://fhir.health.ny.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open",
    },
    "State of North Dakota": {
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/north.dakota.medicaid/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "State of Oklahoma": {
        "api_base": "https://fhir.okhca.org/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Texas": {
        "portal_url": "https://developer.hhs.texas.gov/",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/texas.medicaid/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs)",
    },
    "State of Vermont": {
        "api_base": "https://fhir.medicaid.vermont.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Washington": {
        "portal_url": "https://www.hca.wa.gov/about-hca/interoperability",
        "api_base": "https://fhir.wa.gov/medicaid/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (ProviderOne)",
    },
    "State of West Virginia": {
        "api_base": "https://fhir.medicaid.wv.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "State of Wisconsin": {
        "api_base": "https://fhir.medicaid.wi.gov/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
    "UCare": {
        "portal_url": "https://developer.ucare.org/",
        "api_base": "https://fhir.ucare.org/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (1upHealth)",
    },
}

# Score to status description mapping
SCORE_MAP = {
    '0': 'No API available',
    '1': 'API has issues, payer not actively resolving',
    '2': 'API has issues, payer actively resolving',
    '3': 'API available with intermittent downtimes',
    '4': 'API available and regularly queried',
}


def run():
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found. Run: curl -L -o {CSV_PATH} 'https://docs.google.com/spreadsheets/d/1tiuZfmq1qPtZGoIdYkjxwxlhJc_TZxay/export?format=csv'")
        return

    conn = sqlite3.connect(DB_PATH)

    # Clear existing data to do a clean import
    conn.execute("DELETE FROM payers")
    conn.commit()

    with open(CSV_PATH, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    for row in rows:
        name = row.get('Payers', '').strip()
        if not name:
            continue

        score = row.get('Score', '').strip()
        business = row.get('Mandated Lines of Business', '').strip()
        issue = row.get('Issue', '').strip()
        vendor = row.get('Vendor', '').strip()
        status_desc = row.get('Status Description', '').strip()

        # Build note
        note_parts = []
        if issue:
            note_parts.append(issue)
        if not issue and score == '4':
            note_parts.append("Functioning - regularly queried by Defacto")
        note = '; '.join(note_parts) if note_parts else None

        # Build payer record
        payer = {
            'org_name': name,
            'plan_name': business,
            'note': note,
            'source': 'defacto_2024',
        }

        # Enrich with known endpoints
        known = KNOWN_ENDPOINTS.get(name, {})
        payer.update(known)

        # Derive resource endpoints from api_base
        base = payer.get('api_base', '')
        if base:
            base = base.rstrip('/')
            payer['endpoint_practitioner'] = f"{base}/Practitioner"
            payer['endpoint_practitioner_role'] = f"{base}/PractitionerRole"
            payer['endpoint_organization'] = f"{base}/Organization"
            payer['endpoint_organization_affiliation'] = f"{base}/OrganizationAffiliation"
            payer['endpoint_location'] = f"{base}/Location"
            payer['endpoint_healthcare_service'] = f"{base}/HealthcareService"
            payer['endpoint_insurance_plan'] = f"{base}/InsurancePlan"
            payer['endpoint_network'] = f"{base}/Network"
            payer['endpoint_endpoint'] = f"{base}/Endpoint"

        cols = [
            'org_tin', 'org_name', 'note', 'plan_name', 'portal_url', 'api_base',
            'endpoint_insurance_plan', 'endpoint_practitioner', 'endpoint_practitioner_role',
            'endpoint_organization', 'endpoint_organization_affiliation', 'endpoint_location',
            'endpoint_healthcare_service', 'endpoint_network', 'endpoint_endpoint',
            'requires_registration', 'requires_api_key', 'auth_type', 'source'
        ]
        values = [payer.get(c) for c in cols]
        placeholders = ', '.join(['?'] * len(cols))
        col_names = ', '.join(cols)

        try:
            conn.execute(f"INSERT INTO payers ({col_names}) VALUES ({placeholders})", values)
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {name}: {e}")

    conn.commit()

    # Print summary
    total = conn.execute("SELECT COUNT(*) FROM payers").fetchone()[0]
    with_api = conn.execute("SELECT COUNT(*) FROM payers WHERE api_base IS NOT NULL AND api_base != ''").fetchone()[0]
    no_api = conn.execute("SELECT COUNT(*) FROM payers WHERE api_base IS NULL OR api_base = ''").fetchone()[0]

    print(f"Imported {inserted} payers from Defacto spreadsheet.")
    print(f"  Total in DB: {total}")
    print(f"  With known API base URL: {with_api}")
    print(f"  Without API endpoint (needs research or unavailable): {no_api}")

    conn.close()


if __name__ == '__main__':
    run()
