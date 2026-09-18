-- ============================================================
-- TCOC SILVER LAYER - Cleansed and Enriched
-- 4 streaming tables with data quality expectations
-- ============================================================

USE CATALOG phanitha_test_catalog;
USE SCHEMA tcoc_silver;

-- ============================================================
-- 1. Enriched Payer Claims
-- Joins: claims + members + procedures + providers
-- ============================================================

CREATE OR REFRESH STREAMING TABLE silver_payer_claims_enriched (
  CONSTRAINT valid_claim_id EXPECT (claim_id IS NOT NULL),
  CONSTRAINT valid_billed_amount EXPECT (billed_amount > 0),
  CONSTRAINT valid_service_date EXPECT (service_date IS NOT NULL),
  CONSTRAINT valid_member_id EXPECT (member_id IS NOT NULL)
)
COMMENT 'Enriched payer claims with member, procedure, and provider details'
AS SELECT
  c.claim_id,
  c.member_id,
  c.provider_id,
  c.procedure_code,
  c.service_date,
  c.units,
  c.billed_amount,
  c.claim_status,
  c.denial_reason,
  c.paid_amount,
  pr.procedure_category,
  pr.procedure_desc,
  p.specialty AS provider_specialty,
  p.network_status,
  p.state AS provider_state,
  m.state AS member_state,
  m.plan_type,
  m.line_of_business,
  m.age,
  m.gender,
  m.enrollment_date,
  m.member_code,
  DATE_TRUNC('month', c.service_date) AS service_month,
  c._ingested_at,
  c._source_table
FROM STREAM(phanitha_test_catalog.tcoc_bronze.bronze_payer_claims) c
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_payer_members m ON c.member_id = m.member_id
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_payer_procedures pr ON c.procedure_code = pr.procedure_code
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_payer_providers p ON c.provider_id = p.provider_id;

-- ============================================================
-- 2. Enriched Clinical Encounters
-- Joins: encounters + patients + providers + facilities
-- ============================================================

CREATE OR REFRESH STREAMING TABLE silver_clinical_encounters_enriched (
  CONSTRAINT valid_encounter_id EXPECT (encounter_id IS NOT NULL),
  CONSTRAINT valid_patient_id EXPECT (patient_id IS NOT NULL)
)
COMMENT 'Enriched clinical encounters with patient, provider, and facility details'
AS SELECT
  e.encounter_id,
  e.patient_id,
  e.provider_id,
  e.facility_id,
  e.encounter_type,
  e.admit_datetime,
  e.discharge_datetime,
  e.status,
  e.chief_complaint,
  FLOOR(MONTHS_BETWEEN(current_date(), p.date_of_birth) / 12) AS patient_age,
  p.gender AS patient_gender,
  p.state AS patient_state,
  CONCAT(prov.first_name, ' ', prov.last_name) AS provider_name,
  prov.specialty AS provider_specialty,
  f.facility_name,
  f.facility_type,
  f.state AS facility_state,
  DATEDIFF(e.discharge_datetime, e.admit_datetime) AS length_of_stay,
  e._ingested_at,
  e._source_table
FROM STREAM(phanitha_test_catalog.tcoc_bronze.bronze_clinical_encounters) e
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_patients p ON e.patient_id = p.patient_id
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_providers prov ON e.provider_id = prov.provider_id
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_facilities f ON e.facility_id = f.facility_id;

-- ============================================================
-- 3. Enriched Clinical Claims
-- Joins: claims + encounters + patients
-- ============================================================

CREATE OR REFRESH STREAMING TABLE silver_clinical_claims_enriched (
  CONSTRAINT valid_claim_id EXPECT (claim_id IS NOT NULL),
  CONSTRAINT valid_billed_amount EXPECT (billed_amount > 0)
)
COMMENT 'Enriched clinical claims with encounter and patient context'
AS SELECT
  c.claim_id,
  c.encounter_id,
  c.patient_id,
  c.payer_id,
  c.claim_type,
  c.service_date,
  c.submitted_date,
  c.paid_date,
  c.billed_amount,
  c.allowed_amount,
  c.paid_amount,
  c.patient_responsibility,
  c.status,
  e.encounter_type,
  e.facility_id,
  p.gender AS patient_gender,
  p.state AS patient_state,
  FLOOR(MONTHS_BETWEEN(current_date(), p.date_of_birth) / 12) AS patient_age,
  c._ingested_at,
  c._source_table
FROM STREAM(phanitha_test_catalog.tcoc_bronze.bronze_clinical_claims) c
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_encounters e ON c.encounter_id = e.encounter_id
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_patients p ON c.patient_id = p.patient_id;

-- ============================================================
-- 4. Enriched Diagnoses
-- Joins: diagnoses + encounters + patients
-- ============================================================

CREATE OR REFRESH STREAMING TABLE silver_diagnoses_enriched (
  CONSTRAINT valid_diagnosis_id EXPECT (diagnosis_id IS NOT NULL),
  CONSTRAINT valid_icd10_code EXPECT (icd10_code IS NOT NULL)
)
COMMENT 'Enriched diagnoses with encounter and patient context'
AS SELECT
  d.diagnosis_id,
  d.encounter_id,
  d.patient_id,
  d.icd10_code,
  d.description,
  d.is_primary,
  d.diagnosis_type,
  e.encounter_type,
  e.admit_datetime,
  e.facility_id,
  p.gender AS patient_gender,
  p.state AS patient_state,
  FLOOR(MONTHS_BETWEEN(current_date(), p.date_of_birth) / 12) AS patient_age,
  d._ingested_at,
  d._source_table
FROM STREAM(phanitha_test_catalog.tcoc_bronze.bronze_clinical_diagnoses) d
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_encounters e ON d.encounter_id = e.encounter_id
LEFT JOIN phanitha_test_catalog.tcoc_bronze.bronze_clinical_patients p ON d.patient_id = p.patient_id;
