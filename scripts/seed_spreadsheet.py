"""
Seed additional payers from the Defacto Health spreadsheet image.
These are the smaller MA/Medicaid plans visible in the screenshot.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')

# Data from the user's spreadsheet screenshot + web research
ADDITIONAL_PAYERS = [
    {
        "org_name": "Abilis Health (HMO SNP)",
        "note": "No machine readable API",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Aetna Better",
        "portal_url": "https://developerportal.aetna.com/",
        "api_base": "https://vteapif1.aetna.com/fhirdirectory/v1/patientaccess/",
        "requires_registration": 1,
        "auth_type": "API Key (register on portal)",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "AgeRight Advantage",
        "note": "No machine readable API",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "AHF (Positive Healthcare)",
        "portal_url": "https://positivehealthcare.net/",
        "note": "No publicly documented FHIR API found",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Alameda Alliance for Health",
        "portal_url": "https://fdp.edifecsfedcloud.com/#/portal/alameda.alliance.for.health/home",
        "api_base": "https://fdp.edifecsfedcloud.com/fhir/alameda.alliance.for.health/",
        "requires_registration": 0,
        "auth_type": "Open (Edifecs portal)",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Align powered by Sanford Health Plan",
        "portal_url": "https://www.sanfordhealthplan.com/align/",
        "note": "Uses Sanford Health Plan FHIR infrastructure",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Align Senior Care",
        "note": "No machine readable API",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "Alignment Health Plan",
        "portal_url": "https://www.alignmenthealthplan.com/",
        "note": "Developer portal not publicly documented",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "AllCare Advantage",
        "portal_url": "https://devportal.allcarehealth.com/developer/docs/provider-directory-api",
        "api_base": "https://fhir.allcarehealth.com/r4/provider-directory/",
        "requires_registration": 0,
        "auth_type": "Open (no registration)",
        "source": "defacto_spreadsheet",
    },
    {
        "org_name": "AlohaCare",
        "portal_url": "https://www.alohacare.org/",
        "note": "FHIR API endpoint not publicly documented",
        "source": "defacto_spreadsheet",
    },
]


def run():
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for p in ADDITIONAL_PAYERS:
        # Derive resource endpoints if api_base present
        base = p.get('api_base', '')
        if base:
            base = base.rstrip('/')
            p.setdefault('endpoint_practitioner', f"{base}/Practitioner")
            p.setdefault('endpoint_practitioner_role', f"{base}/PractitionerRole")
            p.setdefault('endpoint_organization', f"{base}/Organization")
            p.setdefault('endpoint_organization_affiliation', f"{base}/OrganizationAffiliation")
            p.setdefault('endpoint_location', f"{base}/Location")
            p.setdefault('endpoint_healthcare_service', f"{base}/HealthcareService")
            p.setdefault('endpoint_insurance_plan', f"{base}/InsurancePlan")
            p.setdefault('endpoint_network', f"{base}/Network")
            p.setdefault('endpoint_endpoint', f"{base}/Endpoint")

        cols = [
            'org_tin', 'org_name', 'note', 'plan_name', 'portal_url', 'api_base',
            'endpoint_insurance_plan', 'endpoint_practitioner', 'endpoint_practitioner_role',
            'endpoint_organization', 'endpoint_organization_affiliation', 'endpoint_location',
            'endpoint_healthcare_service', 'endpoint_network', 'endpoint_endpoint',
            'requires_registration', 'requires_api_key', 'auth_type', 'source'
        ]
        values = [p.get(c) for c in cols]
        placeholders = ', '.join(['?'] * len(cols))
        col_names = ', '.join(cols)

        try:
            conn.execute(f"INSERT OR REPLACE INTO payers ({col_names}) VALUES ({placeholders})", values)
            inserted += 1
        except Exception as e:
            print(f"  Error: {p['org_name']}: {e}")

    conn.commit()
    conn.close()
    print(f"Added {inserted} payers from spreadsheet image.")


if __name__ == '__main__':
    run()
