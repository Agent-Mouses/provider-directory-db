# AGENTS.md — Rules for Working on This Repository

Read this file before making any changes.

## What This Repo Is

A SQLite database tracking **all CMS-regulated payer Provider Directory FHIR API endpoints** — their availability, compliance status, and verification results. Covers Medicare Advantage, Medicaid MCOs, state Medicaid FFS, and CHIP programs.

## Rules

1. **Never delete data.** Only append or update. If a record is wrong, update it with a note — don't remove it.

2. **Always record your source.** Every insert/update must set `source`, `source_detail`, `source_url`, and `source_date`. No unsourced data.

3. **Validate before marking compliant.** Don't mark `compliance_flag = 'COMPLIANT'` unless you've hit the endpoint or have official CMS confirmation.

4. **Use the existing schema.** Don't add columns without documenting them in README.md. The schema is intentionally flat for easy querying.

5. **Commit frequently with descriptive messages.** Each commit should say what changed and why (how many records affected, what source).

6. **Respect rate limits.** When probing endpoints, use ≤10 concurrent threads, 0.3s delay between sequential requests. Don't hammer payer servers.

7. **Keep SOURCES.md updated.** If you add a new data source, document it in SOURCES.md with full citation.

8. **CFR citations matter.** When flagging violations, always include the specific CFR section (42 CFR 422.120, 431.70, 438.242(b)(6), 457.760, or 457.1233(d)).

9. **Don't store secrets.** No API keys, OAuth tokens, or credentials in this repo. The `api_base` URLs are public by CMS mandate.

10. **Run validation after bulk imports.** After adding new records with `api_base` URLs, run `scripts/validate_endpoints.py` to verify them.

## Schema Quick Reference

Full data dictionary: **[SCHEMA.md](SCHEMA.md)** (41 columns, all documented)

```sql
payers (
    -- Identity
    id, org_tin, org_name, note, plan_name,
    -- Plan type flags
    is_medicare_advantage, is_medicaid_mco, is_chip, is_qhp,
    -- Endpoints
    portal_url, api_base,
    endpoint_insurance_plan, endpoint_practitioner, endpoint_practitioner_role,
    endpoint_organization, endpoint_organization_affiliation, endpoint_location,
    endpoint_healthcare_service, endpoint_network, endpoint_endpoint,
    -- Auth
    requires_registration, requires_api_key, auth_type,
    -- Validation
    last_validated, last_validated_status, fhir_version,
    -- Compliance
    compliance_flag, violation_type, violation_detail,
    -- Data quality
    data_quality_flag, data_quality_sample_npi,
    data_quality_practitioner_count, data_quality_checked,
    -- Provenance
    source, source_detail, source_url, source_date,
    created_at, updated_at,
    -- Team tracking
    id_provider_alt, team_status
)
```

## Compliance Flags

| Flag | Count | Meaning |
|------|-------|---------|
| `COMPLIANT` | 261 | Open access, verified live |
| `COMPLIANT_WITH_REGISTRATION` | 343 | Works but needs app registration |
| `NON_COMPLIANT` | 7 | Violates CMS interoperability rule |

## Violation Types

| Type | CFR Violated |
|------|-------------|
| `NO_API` | 42 CFR 422.120 / 431.70 / 438.242(b)(6) |
| `NOT_MACHINE_READABLE` | Same — web-only, no FHIR |
| `REGISTRATION_BLOCKS_ACCESS` | 85 FR 25543 (must be publicly accessible) |
| `MISSING_CRITICAL_DATA` | 42 CFR 422.120 (names, addresses, phones, specialties) |
| `NOT_QUERYABLE` | 42 CFR 422.120 (must be accessible) |
| `MEMBER_LOGIN_REQUIRED` | 85 FR 25543 (no user auth allowed) |

## Validation Status Values (as of 2026-06-11)

| Status | Count | Meaning |
|--------|-------|---------|
| `valid` | 61 | FHIR CapabilityStatement returned (200 + valid JSON) |
| `valid_non_fhir` | 200 | HTTP 200 but response is not a CapabilityStatement |
| `auth_required` | 343 | Server responds 401/403 (needs registration) |
| `no_api` | 6 | No api_base URL — plan never published one |
| `ip_restricted` | 1 | Server exists but blocks by IP/firewall |

**Server reachable: 604/611 (98.9%)**

**Note:** Previous statuses (`unreachable`, `not_found`, `timeout`, `ssl_error`, `client_error`) have been resolved by finding correct URLs. Most payers use **Availity** (`apps.availity.com/availity/public-fhir/`), **Edifecs** (`us120.fhir.m3.edifecsfedcloud.com/`), or **Conduent** platforms.

## Scripts

| Script | Purpose | When to run |
|--------|---------|-------------|
| `scripts/init_db.py` | Create/reset schema | First setup only |
| `scripts/retest_all.py` | Real HTTP test ALL endpoints, update DB | Primary validation |
| `scripts/audit_data_quality.py` | Verify real data vs dummy (NPI cross-check) | After endpoint validation |
| `scripts/import_defacto.py` | Import Defacto 2024 spreadsheet | When Defacto updates |
| `scripts/collect_endpoints.py` | Seed known payer endpoints | Initial setup |
| `scripts/validate_endpoints.py` | Hit /metadata on all endpoints | Quick spot-check |
| `scripts/deep_scrape.py` | Discover endpoints via probing | Periodic discovery |
| `scripts/discover_all.py` | Background mass validation | When many unknowns exist |

## Technical Standards

- FHIR R4 (Release 4.0.1)
- HL7 US Core IG STU 6.1.0
- HL7 Da Vinci PDex Plan Net IG STU 1.2.0
- No user authentication on Provider Directory API (CMS rule)
- App registration/API key is permitted
