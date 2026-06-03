# Provider Directory API Database

A SQLite database tracking CMS-regulated payer Provider Directory FHIR API endpoints, their availability, authentication requirements, and validation status.

## Background

The CMS Interoperability and Patient Access Final Rule (CMS-9115-F, 2020) requires Medicare Advantage, Medicaid, and CHIP payers to publish Provider Directory APIs using FHIR R4 and the Da Vinci PDex Plan Net IG. This repo collects and monitors those endpoints.

## Schema

The `payers` table tracks:

| Column | Description |
|--------|-------------|
| org_tin | Organization TIN |
| org_name | Payer/organization name |
| note | Issues or status notes |
| plan_name | Specific plan name (if API differs by plan) |
| portal_url | Developer portal URL |
| api_base | FHIR base URL |
| endpoint_insurance_plan | `[base]/InsurancePlan` |
| endpoint_practitioner | `[base]/Practitioner` |
| endpoint_practitioner_role | `[base]/PractitionerRole` |
| endpoint_organization | `[base]/Organization` |
| endpoint_organization_affiliation | `[base]/OrganizationAffiliation` |
| endpoint_location | `[base]/Location` |
| endpoint_healthcare_service | `[base]/HealthcareService` |
| endpoint_network | `[base]/Network` |
| endpoint_endpoint | `[base]/Endpoint` |
| requires_registration | Whether app registration is needed |
| auth_type | Authentication method |
| last_validated | Last time endpoint was checked |
| last_validated_status | Result of last validation |
| fhir_version | FHIR version from CapabilityStatement |
| source | Where this record came from |

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Collect/update payer endpoints
python scripts/collect_endpoints.py

# Validate endpoints (hit /metadata)
python scripts/validate_endpoints.py        # all endpoints
python scripts/validate_endpoints.py 5      # first 5 only
```

## Data Sources

- **ONC Lantern** (lantern.healthit.gov) — certified FHIR endpoint monitoring
- **Defacto Health** — payer compliance research (2024 report)
- **CMS developer portals** — individual payer developer documentation
- **State Medicaid portals** — state-level interoperability pages

## Current Coverage

- 26 payers seeded (top MA, Medicaid MCOs, state Medicaids)
- Includes status notes for non-functional APIs (Defacto 2024 findings)
- Endpoint validation with response time tracking

## CMS Regulatory Reference

- 42 CFR § 422.120 (Medicare Advantage)
- 42 CFR § 431.70 (Medicaid FFS)
- 42 CFR § 438.242(b)(6) (Medicaid managed care)
- 42 CFR § 457.760 (CHIP FFS)
- 42 CFR § 457.1233(d) (CHIP managed care)

## Technical Standards

- HL7 FHIR R4 (Release 4.0.1)
- HL7 US Core IG STU 6.1.0
- HL7 Da Vinci PDex Plan Net IG STU 1.2.0
