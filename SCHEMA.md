# Data Dictionary — `payers` Table

**Database:** `data/provider_directory.db` (SQLite)
**Rows:** 540 | **Columns:** 41 | **Cell coverage:** 100%
**Last validated:** June 11, 2026

---

## Organization Identity

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Unique row identifier (auto-increment) | `37` |
| `org_tin` | TEXT | IRS Employer Identification Number (XX-XXXXXXX). `UNDISCOVERABLE` if not findable in public records. | `05-0494040` |
| `org_name` | TEXT | Legal or marketing name of the health plan | `Aetna` |
| `plan_name` | TEXT | Product line or plan type description | `Medicare Advantage, Medicaid MCO` |
| `note` | TEXT | Free-text notes (validation history, issues) | `Functioning - regularly queried by Defacto` |

---

## Plan Type Flags

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `is_medicare_advantage` | TEXT | `Yes` / `No` | Offers Medicare Advantage plans |
| `is_medicaid_mco` | TEXT | `Yes` / `No` | Operates as Medicaid Managed Care Organization |
| `is_chip` | TEXT | `Yes` / `No` | Participates in Children's Health Insurance Program |
| `is_qhp` | TEXT | `Yes` / `No` | Offers Qualified Health Plans on ACA Marketplace |

---

## API Endpoints

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `portal_url` | TEXT | Developer portal or interoperability page URL | `https://developerportal.aetna.com/` |
| `api_base` | TEXT | FHIR API base URL (root for all resource queries). `N/A` if no API exists. | `https://fhir-ehr.cerner.com/r4/aetna` |
| `endpoint_insurance_plan` | TEXT | Full URL for InsurancePlan resource | `{api_base}/InsurancePlan` |
| `endpoint_practitioner` | TEXT | Full URL for Practitioner resource | `{api_base}/Practitioner` |
| `endpoint_practitioner_role` | TEXT | Full URL for PractitionerRole resource | `{api_base}/PractitionerRole` |
| `endpoint_organization` | TEXT | Full URL for Organization resource | `{api_base}/Organization` |
| `endpoint_organization_affiliation` | TEXT | Full URL for OrganizationAffiliation resource | `{api_base}/OrganizationAffiliation` |
| `endpoint_location` | TEXT | Full URL for Location resource | `{api_base}/Location` |
| `endpoint_healthcare_service` | TEXT | Full URL for HealthcareService resource | `{api_base}/HealthcareService` |
| `endpoint_network` | TEXT | Full URL for Network resource | `{api_base}/Network` |
| `endpoint_endpoint` | TEXT | Full URL for Endpoint resource | `{api_base}/Endpoint` |

---

## Authentication

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| `requires_registration` | INTEGER | Whether app registration is needed before querying | `0` = no, `1` = yes |
| `requires_api_key` | INTEGER | Whether an API key is needed | `0` = no, `1` = yes |
| `auth_type` | TEXT | Authentication method used | `open`, `API Key`, `OAuth2 Client Credentials`, `OAuth2/SMART`, `N/A` |

**CMS compliance note:** `open`, `API Key`, and `OAuth2 Client Credentials` are CMS-compliant for Provider Directory APIs. `OAuth2/SMART` (user-level auth) is likely non-compliant per 85 FR 25543.

---

## Validation Status

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| `last_validated` | TEXT | Date of most recent HTTP test | `2026-06-11` |
| `last_validated_status` | TEXT | Result of testing `{api_base}/metadata` | See below |
| `fhir_version` | TEXT | FHIR version from CapabilityStatement or platform | `4.0.1`, `N/A` |

**Status values:**

| Status | Meaning |
|--------|---------|
| `valid` | HTTP 200 + FHIR CapabilityStatement returned |
| `valid_non_fhir` | HTTP 200 but non-standard response (server confirmed live) |
| `auth_required` | HTTP 401/403 (server exists, needs credentials) |
| `no_api` | No endpoint URL exists for this plan |
| `ip_restricted` | Connection timeout/refused (blocks external access) |

---

## Compliance

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| `compliance_flag` | TEXT | Overall CMS compliance determination | `COMPLIANT`, `COMPLIANT_WITH_REGISTRATION`, `NON_COMPLIANT` |
| `violation_type` | TEXT | Type of violation (if any) | `NONE`, `NO_API`, `NOT_PUBLICLY_ACCESSIBLE`, `CLIENT_ERROR`, `MISSING_CRITICAL_DATA` |
| `violation_detail` | TEXT | Human-readable explanation of the issue | Free text |

---

## Data Quality (NPI Verification)

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| `data_quality_flag` | TEXT | Whether real provider data was confirmed | See below |
| `data_quality_sample_npi` | TEXT | A sample NPI extracted and verified against NPPES | `1447509856` or `N/A — requires OAuth` |
| `data_quality_practitioner_count` | TEXT | Number of practitioners reported by the API | `18432` or `N/A — requires OAuth` |
| `data_quality_checked` | TEXT | Date of data quality audit | `2026-06-11` |

**Data quality flags:**

| Flag | Meaning |
|------|---------|
| `VERIFIED_REAL` | Queried Practitioner, got NPIs, verified against CMS NPPES Registry — real data |
| `AUTH_WALL` | Server exists but requires OAuth credentials — cannot verify data without registering |
| `UNVERIFIABLE` | Server returned errors (HTTP 500, timeout) — data quality unknown |
| `EMPTY` | Server returned empty Bundle with no entries — possible dummy/staging API |
| `NO_API` | No endpoint exists |
| `NO_NPI` | Returns practitioner data but without NPI identifiers |

---

## Provenance

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `source` | TEXT | Source category key | `defacto_2024`, `cms_sma_directory`, `cms_ma_directory_2026` |
| `source_detail` | TEXT | Detailed description of where this record came from | `Availity Public FHIR Directory (verified 2026-06-11)` |
| `source_url` | TEXT | URL of the source document/dataset | `https://defacto.health/2024/06/24/...` |
| `source_date` | TEXT | Date the source was published or accessed | `2024-06-24` |
| `created_at` | TEXT | When this record was first added to the DB | `2026-06-03 13:33:27` |
| `updated_at` | TEXT | When this record was last modified | `2026-06-03 17:49:01` |

---

## Internal / Team Tracking

| Column | Type | Description |
|--------|------|-------------|
| `id_provider_alt` | TEXT | Alternative provider identifier (if payer uses non-standard ID). Usually `N/A`. |
| `team_status` | TEXT | Internal team workflow status (e.g., `pending`, `Under Review`). Usually `N/A`. |

---

## Quick Reference: How to Query

```sql
-- All open-access payers with verified real data
SELECT org_name, api_base FROM payers
WHERE data_quality_flag = 'VERIFIED_REAL';

-- Medicare Advantage plans by compliance
SELECT org_name, compliance_flag, auth_type FROM payers
WHERE is_medicare_advantage = 'Yes'
ORDER BY compliance_flag;

-- Non-compliant payers and why
SELECT org_name, violation_type, violation_detail FROM payers
WHERE compliance_flag = 'NON_COMPLIANT';

-- Count by plan type
SELECT
    SUM(CASE WHEN is_medicare_advantage = 'Yes' THEN 1 ELSE 0 END) as MA,
    SUM(CASE WHEN is_medicaid_mco = 'Yes' THEN 1 ELSE 0 END) as Medicaid,
    SUM(CASE WHEN is_chip = 'Yes' THEN 1 ELSE 0 END) as CHIP
FROM payers;
```
