# Luminos Health — Total Cost of Care (TCOC)

A healthcare cost analytics platform built on Databricks Lakeflow Spark Declarative Pipelines, following the **medallion architecture** (Bronze → Silver → Gold) to transform raw payer claims and clinical EHR data into analytics-ready tables powering an executive dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  SOURCE DATA (phanitha_test_catalog)                            │
│  hls_payer_claims: claims, members, procedures, providers       │
│  hls_demo: claims, diagnoses, encounters, facilities,           │
│            patients, providers                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRONZE (tcoc_bronze) — 10 Streaming Tables                     │
│  Raw ingestion with _ingested_at and _source_table metadata     │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  SILVER (tcoc_silver) — 4 Streaming Tables                      │
│  Enriched joins with data quality expectations                  │
│  • silver_payer_claims_enriched                                 │
│  • silver_clinical_encounters_enriched                          │
│  • silver_clinical_claims_enriched                              │
│  • silver_diagnoses_enriched                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  GOLD (tcoc_gold) — 6 Materialized Views                        │
│  Analytics-ready aggregates for dashboard consumption            │
│  • tcoc_member_summary          (7,987 rows)                    │
│  • tcoc_pmpm_trends             (2,700 rows)                    │
│  • tcoc_service_category_costs (30,480 rows)                    │
│  • tcoc_provider_network_analysis (1,800 rows)                  │
│  • tcoc_geographic_analysis     (2,700 rows)                    │
│  • tcoc_executive_kpis          (1 row)                         │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD — Luminos Health Total Cost of Care                 │
│  5 pages: Executive Summary, PMPM Trends, Service Categories,   │
│  Network & Provider, Geography                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
total-cost-of-care/
├── README.md
└── transformations/
    ├── bronze/
    │   └── bronze_ingestion.sql      # 10 streaming tables — raw ingestion
    ├── silver/
    │   └── silver_tables.sql         # 4 streaming tables — enriched joins + DQ
    └── gold/
        └── gold_views.sql            # 6 materialized views — analytics layer
```

## Data Quality Expectations

The silver layer enforces constraints on every record:

| Table | Constraint | Action |
| --- | --- | --- |
| silver_payer_claims_enriched | `claim_id IS NOT NULL` | Warn |
| silver_payer_claims_enriched | `billed_amount > 0` | Warn |
| silver_payer_claims_enriched | `service_date IS NOT NULL` | Warn |
| silver_payer_claims_enriched | `member_id IS NOT NULL` | Warn |
| silver_clinical_encounters_enriched | `encounter_id IS NOT NULL` | Warn |
| silver_clinical_encounters_enriched | `patient_id IS NOT NULL` | Warn |
| silver_clinical_claims_enriched | `claim_id IS NOT NULL` | Warn |
| silver_clinical_claims_enriched | `billed_amount > 0` | Warn |
| silver_diagnoses_enriched | `diagnosis_id IS NOT NULL` | Warn |
| silver_diagnoses_enriched | `icd10_code IS NOT NULL` | Warn |

## Gold Layer — Key Metrics

| Metric | Description |
| --- | --- |
| **PMPM** | Per Member Per Month cost (total paid / active members) |
| **Denial Rate %** | Percentage of claims denied |
| **Network Leakage %** | Out-of-network spend as % of total paid |
| **ER Rate / 1,000** | Emergency visits per 1,000 members |
| **Cost Risk Tier** | Member segmentation: Low / Moderate / High / Catastrophic |
| **Reimbursement Rate** | Paid amount as % of billed amount |

## Pipeline Configuration

| Setting | Value |
| --- | --- |
| **Pipeline ID** | `24877043-6556-40fa-8603-442ca50b2a20` |
| **Catalog** | `phanitha_test_catalog` |
| **Schemas** | `tcoc_bronze`, `tcoc_silver`, `tcoc_gold` |
| **Compute** | Serverless, Photon enabled |
| **Channel** | Current |
| **Mode** | Triggered |

## Getting Started

1. Ensure access to `phanitha_test_catalog` with the source schemas `hls_payer_claims` and `hls_demo`
2. Create target schemas if they don't exist:
   ```sql
   CREATE SCHEMA IF NOT EXISTS phanitha_test_catalog.tcoc_bronze;
   CREATE SCHEMA IF NOT EXISTS phanitha_test_catalog.tcoc_silver;
   CREATE SCHEMA IF NOT EXISTS phanitha_test_catalog.tcoc_gold;
   ```
3. Configure the pipeline with the 3 SQL files under `transformations/`
4. Run a pipeline update to materialize all 20 datasets
