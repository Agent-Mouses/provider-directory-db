# CMS Provider Directory API Database

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

A SQLite database tracking **all CMS-regulated payer Provider Directory FHIR API endpoints** — their availability, compliance status, and verification results.

Developed by the [Mullan Institute for Health Workforce Equity](https://gwhwi.org) at the George Washington University Milken Institute School of Public Health.

> **Read [AGENTS.md](AGENTS.md) before making changes.**

## Overview

The CMS Interoperability and Patient Access Final Rule (CMS-9115-F) requires Medicare Advantage organizations, Medicaid programs, and CHIP plans to publish Provider Directory APIs using FHIR R4. This repo collects, validates, and monitors those endpoints across the entire regulated universe.

This database supports research on payer interoperability compliance, health workforce data accessibility, and the infrastructure available for provider directory data exchange.

## Database

`data/provider_directory.db` — SQLite

**533 records | 408 unique organizations | All real-tested 2026-06-03**

### Unit of Analysis

One row = one payer plan/product line. A parent organization (e.g., Centene) may have multiple rows for each subsidiary plan brand (Ambetter, WellCare, etc.) sharing the same API endpoint.

## Compliance Status (real HTTP + DNS tests)

| Status | Count | % |
|--------|-------|---|
| COMPLIANT (verified live FHIR, open access) | 39 | 7.3% |
| COMPLIANT_WITH_REGISTRATION (server exists, needs auth/registration) | 419 | 78.6% |
| NON_COMPLIANT (no API or not publicly accessible) | 75 | 14.1% |

## Validation Results (all 533 tested)

| Status | Count | How verified |
|--------|-------|---|
| `auth_required` | 359 | HTTP 401/403 returned (server exists) |
| `dns_failure` | 46 | Published URL does not resolve in DNS |
| `ip_restricted` | 43 | DNS resolves but connection refused/timeout (WAF/VPN) |
| `valid` | 33 | FHIR CapabilityStatement returned (200 + valid JSON) |
| `no_api` | 28 | No api_base URL in record |
| `client_error` | 17 | HTTP 4xx (server exists, path issue) |
| `valid_non_fhir` | 7 | HTTP 200 but not a CapabilityStatement |

## Verified Live FHIR Endpoints (14 unique)

All return CapabilityStatement with fhirVersion 4.0.1:

| Organization | API Base |
|---|---|
| Aetna/CVS Health | https://fhir-ehr.cerner.com/r4/aetna |
| Blue Cross and Blue Shield of Texas | https://cmsinterop.tmhp.com/tmhp/fhir/pd/R4 |
| Blue Cross Blue Shield of Michigan | https://api.interopstation.com/mdhhs/fhir |
| CareSource | https://orchestrateserver.caresource.careevolution.com/api/fhir/provider-directory |
| Cigna | https://fhir.cigna.com/ProviderDirectory/v1 |
| HealthPartners | https://api-developerportal.healthpartners.com/interop/external/fhir |
| Horizon BCBS New Jersey | https://api.interopstation.com/njios/fhir |
| Inland Empire Health Plan | https://fhir.iehp.org/provider-directory/ |
| State of Arkansas | https://fite.ar-prd.gw02.abacusinsights.ai/provider-directory |
| State of Idaho | https://api-idmedicaid.safhir.io/v1/api/provider-directory |
| State of Nebraska | https://dhhs-api.ne.gov/dhhs/trading-partner/api/cmsi/provider/1.0.0 |
| State of New Jersey | https://api.interopstation.com/njios/fhir |
| State of Washington | https://wa.fhir.mhbapp.com/pd/api/v1 |
| State of Wyoming | https://wy.fhir.mhbapp.com/pd/api/v1 |

## Non-Compliance Violations (75 payers)

| Violation | Count | Meaning |
|-----------|-------|---------|
| NOT_PUBLICLY_ACCESSIBLE | 46 | Published URL does not resolve (DNS failure) |
| NO_API | 14 | No API endpoint published at all |
| REGISTRATION_BLOCKS_ACCESS | 6 | Developer registration broken/blocked |
| MISSING_CRITICAL_DATA | 5 | API exists but returns errors/missing data |
| NOT_MACHINE_READABLE | 3 | Web HTML only, no FHIR API |

## Data Sources

See [SOURCES.md](SOURCES.md) for full citations.

| Source | Records |
|--------|---------|
| Defacto Health 2024 | 230 |
| CMS Universe Expansion (MCOs, CHIP, states) | 160 |
| CMS MA Plan Directory 2026-05 (official) | 105 |
| CMS SMA Endpoint Directory (official) | 36 |
| Automated Discovery | 2 |

## Usage

```bash
pip install -r requirements.txt

# Real-test all endpoints (writes to DB + data/retest_results.json)
python scripts/retest_all.py

# Discover new endpoints for broken payers
python scripts/discover_new_endpoints.py

# Initialize database (first time only)
python scripts/init_db.py
```

## Query Examples

```python
import sqlite3
conn = sqlite3.connect('data/provider_directory.db')

# All verified live FHIR endpoints
conn.execute("SELECT org_name, api_base, fhir_version FROM payers WHERE last_validated_status='valid'")

# Non-compliant payers
conn.execute("SELECT org_name, violation_type, violation_detail FROM payers WHERE compliance_flag='NON_COMPLIANT'")

# All payers with confirmed server existence
conn.execute("SELECT org_name, api_base FROM payers WHERE compliance_flag IN ('COMPLIANT', 'COMPLIANT_WITH_REGISTRATION')")
```

## Regulatory Reference

| CFR | Applies to |
|-----|-----------|
| 42 CFR § 422.120 | Medicare Advantage |
| 42 CFR § 431.70 | Medicaid FFS |
| 42 CFR § 438.242(b)(6) | Medicaid managed care |
| 42 CFR § 457.760 | CHIP FFS |
| 42 CFR § 457.1233(d) | CHIP managed care |

## Technical Standard

- HL7 FHIR R4 (Release 4.0.1)
- HL7 US Core IG STU 6.1.0
- HL7 Da Vinci PDex Plan Net IG STU 1.2.0

## Citation

```
Mullan Institute for Health Workforce Equity. (2026). CMS Provider Directory API
Database. George Washington University. https://github.com/hltiunn/provider-directory-db
```

## License

This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE).
