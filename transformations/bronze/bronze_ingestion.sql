-- ============================================================
-- TCOC BRONZE LAYER - Raw Ingestion
-- 10 streaming tables from phanitha_test_catalog sources
-- ============================================================

USE CATALOG phanitha_test_catalog;
USE SCHEMA tcoc_bronze;

-- ============================================================
-- Payer Claims Data (hls_payer_claims schema)
-- ============================================================

CREATE OR REFRESH STREAMING TABLE bronze_payer_claims
COMMENT 'Raw payer claims data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_payer_claims.claims' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_payer_claims.claims);

CREATE OR REFRESH STREAMING TABLE bronze_payer_members
COMMENT 'Raw payer members data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_payer_claims.members' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_payer_claims.members);

CREATE OR REFRESH STREAMING TABLE bronze_payer_procedures
COMMENT 'Raw payer procedure reference data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_payer_claims.procedures' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_payer_claims.procedures);

CREATE OR REFRESH STREAMING TABLE bronze_payer_providers
COMMENT 'Raw payer provider data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_payer_claims.providers' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_payer_claims.providers);

-- ============================================================
-- Clinical / EHR Data (hls_demo schema)
-- ============================================================

CREATE OR REFRESH STREAMING TABLE bronze_clinical_claims
COMMENT 'Raw clinical claims data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.claims' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.claims);

CREATE OR REFRESH STREAMING TABLE bronze_clinical_diagnoses
COMMENT 'Raw clinical diagnoses data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.diagnoses' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.diagnoses);

CREATE OR REFRESH STREAMING TABLE bronze_clinical_encounters
COMMENT 'Raw clinical encounters data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.encounters' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.encounters);

CREATE OR REFRESH STREAMING TABLE bronze_clinical_facilities
COMMENT 'Raw clinical facilities data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.facilities' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.facilities);

CREATE OR REFRESH STREAMING TABLE bronze_clinical_patients
COMMENT 'Raw clinical patients data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.patients' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.patients);

CREATE OR REFRESH STREAMING TABLE bronze_clinical_providers
COMMENT 'Raw clinical providers data'
AS SELECT
  *,
  current_timestamp() AS _ingested_at,
  'hls_demo.providers' AS _source_table
FROM STREAM(phanitha_test_catalog.hls_demo.providers);
