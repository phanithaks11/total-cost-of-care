-- ============================================================
-- TCOC GOLD LAYER - Analytics-Ready Aggregates
-- 6 materialized views for dashboard consumption
-- ============================================================

USE CATALOG phanitha_test_catalog;
USE SCHEMA tcoc_gold;

-- ============================================================
-- 1. Member-Level TCOC Summary
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_member_summary
COMMENT 'One row per member with total cost, utilization, and risk tier'
AS
WITH member_claims AS (
  SELECT
    member_id,
    member_code,
    member_state,
    plan_type,
    line_of_business,
    age,
    gender,
    enrollment_date,
    GREATEST(MONTHS_BETWEEN(DATE'2025-12-31', enrollment_date), 1) AS months_enrolled,
    COUNT(claim_id) AS total_claims,
    SUM(billed_amount) AS total_billed,
    SUM(paid_amount) AS total_paid,
    SUM(billed_amount) - SUM(paid_amount) AS total_member_liability,
    AVG(billed_amount) AS avg_claim_cost,
    COUNT(DISTINCT procedure_category) AS distinct_service_categories,
    COUNT(DISTINCT provider_id) AS distinct_providers,
    COUNT(DISTINCT service_month) AS active_months,
    SUM(CASE WHEN network_status = 'In-Network' THEN paid_amount ELSE 0 END) AS in_network_paid,
    SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) AS out_of_network_paid,
    SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
    SUM(CASE WHEN procedure_category = 'Emergency' THEN 1 ELSE 0 END) AS er_visits,
    SUM(CASE WHEN procedure_category = 'Surgery' THEN paid_amount ELSE 0 END) AS surgery_costs,
    SUM(CASE WHEN procedure_category IN ('Primary Care', 'Preventive') THEN 1 ELSE 0 END) AS preventive_visits
  FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
  GROUP BY ALL
)
SELECT
  *,
  ROUND(total_paid / NULLIF(months_enrolled, 0), 2) AS pmpm,
  CASE
    WHEN total_paid < 1000 THEN 'Low'
    WHEN total_paid < 5000 THEN 'Moderate'
    WHEN total_paid < 15000 THEN 'High'
    ELSE 'Catastrophic'
  END AS cost_risk_tier,
  ROUND(out_of_network_paid / NULLIF(total_paid, 0) * 100, 2) AS network_leakage_pct,
  CASE
    WHEN age < 18 THEN 'Pediatric'
    WHEN age < 30 THEN 'Young Adult'
    WHEN age < 50 THEN 'Adult'
    WHEN age < 65 THEN 'Senior'
    ELSE 'Medicare'
  END AS age_band,
  ROUND(denied_claims / NULLIF(CAST(total_claims AS DOUBLE), 0) * 100, 2) AS denial_rate_pct
FROM member_claims;

-- ============================================================
-- 2. PMPM Trends
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_pmpm_trends
COMMENT 'Monthly per-member-per-month trends by LOB, plan type, and geography'
AS
SELECT
  service_month AS report_month,
  line_of_business,
  plan_type,
  member_state,
  COUNT(DISTINCT member_id) AS active_members,
  SUM(billed_amount) AS total_billed,
  SUM(paid_amount) AS total_paid,
  COUNT(claim_id) AS claim_count,
  SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_count,
  SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) AS oon_paid,
  SUM(CASE WHEN procedure_category = 'Surgery' THEN paid_amount ELSE 0 END) AS surgery_paid,
  SUM(CASE WHEN procedure_category = 'Emergency' THEN paid_amount ELSE 0 END) AS emergency_paid,
  SUM(CASE WHEN procedure_category IN ('Primary Care', 'Preventive') THEN paid_amount ELSE 0 END) AS primary_care_paid,
  SUM(CASE WHEN procedure_category = 'Radiology' THEN paid_amount ELSE 0 END) AS radiology_paid,
  ROUND(SUM(paid_amount) / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS pmpm,
  ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(claim_id), 0), 2) AS denial_rate_pct,
  ROUND(SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) * 100.0 / NULLIF(SUM(paid_amount), 0), 2) AS network_leakage_pct
FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
GROUP BY ALL;

-- ============================================================
-- 3. Service Category Costs
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_service_category_costs
COMMENT 'Cost breakdown by procedure category and service type'
AS
SELECT
  procedure_category,
  provider_specialty,
  network_status,
  line_of_business,
  plan_type,
  service_month,
  COUNT(claim_id) AS claim_count,
  COUNT(DISTINCT member_id) AS unique_members,
  SUM(billed_amount) AS total_billed,
  SUM(paid_amount) AS total_paid,
  AVG(billed_amount) AS avg_billed_per_claim,
  AVG(paid_amount) AS avg_paid_per_claim,
  ROUND(SUM(paid_amount) / NULLIF(SUM(billed_amount), 0) * 100, 2) AS reimbursement_rate_pct,
  SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
  ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(claim_id), 0), 2) AS denial_rate_pct,
  SUM(units) AS total_units,
  ROUND(SUM(paid_amount) / NULLIF(SUM(units), 0), 2) AS cost_per_unit
FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
GROUP BY ALL;

-- ============================================================
-- 4. Provider & Network Analysis
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_provider_network_analysis
COMMENT 'Provider efficiency, network leakage, and cost variation'
AS
SELECT
  provider_id,
  provider_specialty,
  provider_state,
  network_status,
  line_of_business,
  COUNT(claim_id) AS total_claims,
  COUNT(DISTINCT member_id) AS unique_patients,
  SUM(billed_amount) AS total_billed,
  SUM(paid_amount) AS total_paid,
  AVG(billed_amount) AS avg_billed,
  AVG(paid_amount) AS avg_paid,
  ROUND(SUM(paid_amount) / NULLIF(SUM(billed_amount), 0) * 100, 2) AS reimbursement_rate,
  SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
  ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(claim_id), 0), 2) AS denial_rate_pct,
  AVG(paid_amount) - AVG(AVG(paid_amount)) OVER (PARTITION BY provider_specialty) AS cost_vs_specialty_avg,
  COUNT(DISTINCT procedure_category) AS service_breadth,
  COUNT(DISTINCT service_month) AS active_months
FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
GROUP BY ALL;

-- ============================================================
-- 5. Geographic Analysis
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_geographic_analysis
COMMENT 'State-level cost patterns and benchmarking'
AS
SELECT
  member_state,
  line_of_business,
  plan_type,
  service_month AS report_month,
  COUNT(DISTINCT member_id) AS active_members,
  COUNT(claim_id) AS claim_count,
  SUM(billed_amount) AS total_billed,
  SUM(paid_amount) AS total_paid,
  ROUND(SUM(paid_amount) / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS pmpm,
  ROUND(COUNT(claim_id) * 1.0 / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS claims_per_member,
  SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) AS oon_paid,
  ROUND(SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) * 100.0 / NULLIF(SUM(paid_amount), 0), 2) AS oon_pct,
  SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) AS denied_claims,
  ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(claim_id), 0), 2) AS denial_rate_pct,
  SUM(CASE WHEN procedure_category = 'Emergency' THEN 1 ELSE 0 END) AS er_visits,
  ROUND(SUM(CASE WHEN procedure_category = 'Emergency' THEN 1 ELSE 0 END) * 1000.0 / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS er_rate_per_1000,
  SUM(CASE WHEN procedure_category = 'Surgery' THEN paid_amount ELSE 0 END) AS surgery_paid,
  AVG(age) AS avg_age
FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
GROUP BY ALL;

-- ============================================================
-- 6. Executive KPIs
-- ============================================================

CREATE OR REFRESH MATERIALIZED VIEW tcoc_executive_kpis
COMMENT 'Pre-computed executive KPIs for dashboard consumption'
AS
WITH claims_agg AS (
  SELECT
    COUNT(DISTINCT member_id) AS total_members,
    COUNT(claim_id) AS total_claims,
    ROUND(SUM(billed_amount), 2) AS total_billed,
    ROUND(SUM(paid_amount), 2) AS total_paid,
    ROUND(SUM(paid_amount) / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS overall_pmpm,
    ROUND(SUM(paid_amount) / NULLIF(SUM(billed_amount), 0) * 100, 2) AS overall_reimbursement_rate,
    ROUND(SUM(CASE WHEN network_status = 'Out-of-Network' THEN paid_amount ELSE 0 END) * 100.0 / NULLIF(SUM(paid_amount), 0), 2) AS network_leakage_pct,
    ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(claim_id), 0), 2) AS denial_rate_pct,
    ROUND(COUNT(claim_id) * 1.0 / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS claims_per_member,
    COUNT(DISTINCT provider_id) AS active_providers,
    ROUND(SUM(CASE WHEN procedure_category = 'Emergency' THEN 1 ELSE 0 END) * 1000.0 / NULLIF(COUNT(DISTINCT member_id), 0), 2) AS er_rate_per_1000,
    MIN(service_date) AS data_start_date,
    MAX(service_date) AS data_end_date
  FROM phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
),
catastrophic AS (
  SELECT
    COUNT(*) AS catastrophic_tier_members,
    ROUND(COALESCE(SUM(total_paid), 0), 2) AS catastrophic_tier_cost
  FROM tcoc_member_summary
  WHERE cost_risk_tier = 'Catastrophic'
)
SELECT
  ca.*,
  cat.catastrophic_tier_members,
  cat.catastrophic_tier_cost,
  current_timestamp() AS refreshed_at
FROM claims_agg ca
CROSS JOIN catastrophic cat;
