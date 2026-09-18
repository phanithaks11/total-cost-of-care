-- ============================================================
-- TCOC METRIC VIEWS
-- Reusable KPI definitions for dashboards, Genie, and notebooks
-- ============================================================

-- ============================================================
-- 1. Claims-Level Metrics
-- Source: silver_payer_claims_enriched (most granular fact table)
-- Enables flexible slicing by any dimension at query time
-- ============================================================

CREATE OR REPLACE VIEW phanitha_test_catalog.tcoc_gold.tcoc_claims_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: phanitha_test_catalog.tcoc_silver.silver_payer_claims_enriched
  comment: >
    Claim-level TCOC metrics. Slice by any dimension (LOB, plan, state,
    service category, provider, network status) to get consistent KPIs
    across dashboards, Genie spaces, and notebooks.

  dimensions:
    - name: Service Month
      expr: service_month
      display_name: Service Month
      comment: Month when the service was rendered
      format:
        type: date
        date_format: locale_short_month
      synonyms:
        - month
        - service date
        - report month

    - name: Line of Business
      expr: line_of_business
      display_name: Line of Business
      comment: Member's line of business (Commercial, Medicare, Medicaid)
      synonyms:
        - LOB
        - business line

    - name: Plan Type
      expr: plan_type
      display_name: Plan Type
      comment: Insurance plan type (HMO, PPO, EPO, POS)

    - name: Member State
      expr: member_state
      display_name: Member State
      comment: US state where the member resides
      synonyms:
        - state
        - geography
        - region

    - name: Procedure Category
      expr: procedure_category
      display_name: Service Category
      comment: Clinical service category (Surgery, Emergency, Primary Care, etc.)
      synonyms:
        - service category
        - service type
        - procedure type

    - name: Provider Specialty
      expr: provider_specialty
      display_name: Provider Specialty
      comment: Medical specialty of the servicing provider

    - name: Network Status
      expr: network_status
      display_name: Network Status
      comment: In-Network or Out-of-Network

    - name: Claim Status
      expr: claim_status
      display_name: Claim Status
      comment: Current claim adjudication status (Paid, Denied, Pending)

    - name: Gender
      expr: gender
      display_name: Gender
      comment: Member gender

    - name: Age Band
      expr: |-
        CASE
          WHEN age < 18 THEN 'Pediatric'
          WHEN age < 30 THEN 'Young Adult'
          WHEN age < 50 THEN 'Adult'
          WHEN age < 65 THEN 'Senior'
          ELSE 'Medicare'
        END
      display_name: Age Band
      comment: Age-based member segmentation
      synonyms:
        - age group
        - age range

  measures:
    - name: Total Paid
      expr: SUM(paid_amount)
      display_name: Total Paid
      comment: Total amount paid by payers
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact
      synonyms:
        - paid
        - total cost
        - spend

    - name: Total Billed
      expr: SUM(billed_amount)
      display_name: Total Billed
      comment: Total amount billed by providers
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact

    - name: Claim Count
      expr: COUNT(claim_id)
      display_name: Claims
      comment: Total number of claims
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact
      synonyms:
        - number of claims
        - claims

    - name: Unique Members
      expr: COUNT(DISTINCT member_id)
      display_name: Unique Members
      comment: Distinct member count
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact
      synonyms:
        - members
        - member count
        - lives

    - name: PMPM
      expr: MEASURE(`Total Paid`) / MEASURE(`Unique Members`)
      display_name: PMPM
      comment: Per Member Per Month cost
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
      synonyms:
        - per member per month
        - cost per member

    - name: Avg Cost per Claim
      expr: MEASURE(`Total Paid`) / MEASURE(`Claim Count`)
      display_name: Avg Cost per Claim
      comment: Average paid amount per claim
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2

    - name: Reimbursement Rate
      expr: MEASURE(`Total Paid`) / MEASURE(`Total Billed`) * 100
      display_name: Reimbursement Rate %
      comment: Paid as percentage of billed — payer efficiency
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - payment rate
        - reimb rate

    - name: Denied Claims
      expr: COUNT(claim_id) FILTER (WHERE claim_status = 'Denied')
      display_name: Denied Claims
      comment: Number of denied claims
      format:
        type: number
        decimal_places:
          type: exact
          places: 0

    - name: Denial Rate
      expr: MEASURE(`Denied Claims`) * 100.0 / MEASURE(`Claim Count`)
      display_name: Denial Rate %
      comment: Percentage of claims denied
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - denial pct
        - denied percentage

    - name: Out-of-Network Paid
      expr: SUM(paid_amount) FILTER (WHERE network_status = 'Out-of-Network')
      display_name: OON Paid
      comment: Total paid for out-of-network services
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact
      synonyms:
        - OON cost
        - out of network spend

    - name: Network Leakage
      expr: MEASURE(`Out-of-Network Paid`) * 100.0 / MEASURE(`Total Paid`)
      display_name: Network Leakage %
      comment: Out-of-network spend as percentage of total paid
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - OON pct
        - network leakage pct

    - name: ER Visits
      expr: COUNT(claim_id) FILTER (WHERE procedure_category = 'Emergency')
      display_name: ER Visits
      comment: Number of emergency department visits
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
      synonyms:
        - emergency visits
        - ED visits

    - name: ER Rate per 1000
      expr: MEASURE(`ER Visits`) * 1000.0 / MEASURE(`Unique Members`)
      display_name: ER Rate / 1,000
      comment: Emergency visits per 1,000 members
      format:
        type: number
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - ER utilization
        - emergency rate

    - name: Surgery Costs
      expr: SUM(paid_amount) FILTER (WHERE procedure_category = 'Surgery')
      display_name: Surgery Costs
      comment: Total paid for surgical procedures
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact

    - name: Preventive Visits
      expr: COUNT(claim_id) FILTER (WHERE procedure_category IN ('Primary Care', 'Preventive'))
      display_name: Preventive Visits
      comment: Number of primary care and preventive service visits
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
      synonyms:
        - preventive care
        - wellness visits

    - name: Total Units
      expr: SUM(units)
      display_name: Total Units
      comment: Total service units across all claims
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
$$;


-- ============================================================
-- 2. Member-Level Metrics
-- Source: tcoc_member_summary (one row per member)
-- For population health, risk stratification, and member analytics
-- ============================================================

CREATE OR REPLACE VIEW phanitha_test_catalog.tcoc_gold.tcoc_member_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: phanitha_test_catalog.tcoc_gold.tcoc_member_summary
  comment: >
    Member-level TCOC metrics for population health analysis.
    Each row is one member — use for risk stratification,
    cost distribution, and member segmentation.

  dimensions:
    - name: Cost Risk Tier
      expr: cost_risk_tier
      display_name: Cost Risk Tier
      comment: Member cost segmentation (Low / Moderate / High / Catastrophic)
      synonyms:
        - risk tier
        - risk level
        - cost tier

    - name: Age Band
      expr: age_band
      display_name: Age Band
      comment: Age-based member grouping
      synonyms:
        - age group

    - name: Line of Business
      expr: line_of_business
      display_name: Line of Business
      comment: Member's line of business
      synonyms:
        - LOB

    - name: Plan Type
      expr: plan_type
      display_name: Plan Type
      comment: Insurance plan type

    - name: Member State
      expr: member_state
      display_name: Member State
      comment: Member's state of residence
      synonyms:
        - state
        - geography

    - name: Gender
      expr: gender
      display_name: Gender

  measures:
    - name: Total Members
      expr: COUNT(member_id)
      display_name: Total Members
      comment: Total member count
      format:
        type: number
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact
      synonyms:
        - member count
        - lives
        - population

    - name: Total Paid
      expr: SUM(total_paid)
      display_name: Total Paid
      comment: Aggregate paid amount across all members
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact

    - name: Total Billed
      expr: SUM(total_billed)
      display_name: Total Billed
      comment: Aggregate billed amount across all members
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact

    - name: Avg PMPM
      expr: SUM(total_paid) / SUM(months_enrolled)
      display_name: Avg PMPM
      comment: Weighted average per-member-per-month cost
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 2
      synonyms:
        - PMPM
        - per member per month

    - name: Avg Claims per Member
      expr: SUM(total_claims) / COUNT(member_id)
      display_name: Avg Claims / Member
      comment: Average number of claims per member
      format:
        type: number
        decimal_places:
          type: exact
          places: 1

    - name: Network Leakage
      expr: SUM(out_of_network_paid) * 100.0 / SUM(total_paid)
      display_name: Network Leakage %
      comment: Out-of-network cost as percentage of total paid
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
      synonyms:
        - OON pct

    - name: Catastrophic Members
      expr: COUNT(member_id) FILTER (WHERE cost_risk_tier = 'Catastrophic')
      display_name: Catastrophic Members
      comment: Members in the Catastrophic cost tier (>$15K total paid)
      format:
        type: number
        decimal_places:
          type: exact
          places: 0

    - name: Catastrophic Cost
      expr: SUM(total_paid) FILTER (WHERE cost_risk_tier = 'Catastrophic')
      display_name: Catastrophic Cost
      comment: Total paid for Catastrophic-tier members
      format:
        type: currency
        currency_code: USD
        decimal_places:
          type: exact
          places: 0
        abbreviation: compact

    - name: Catastrophic Cost Share
      expr: |-
        MEASURE(`Catastrophic Cost`) * 100.0 / MEASURE(`Total Paid`)
      display_name: Catastrophic Cost Share %
      comment: Percentage of total cost driven by Catastrophic-tier members
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1

    - name: High Risk Members
      expr: COUNT(member_id) FILTER (WHERE cost_risk_tier IN ('High', 'Catastrophic'))
      display_name: High Risk Members
      comment: Members in High or Catastrophic cost tiers
      format:
        type: number
        decimal_places:
          type: exact
          places: 0

    - name: Total ER Visits
      expr: SUM(er_visits)
      display_name: Total ER Visits
      comment: Aggregate emergency department visits
      format:
        type: number
        decimal_places:
          type: exact
          places: 0

    - name: ER Rate per 1000
      expr: SUM(er_visits) * 1000.0 / COUNT(member_id)
      display_name: ER Rate / 1,000
      comment: Emergency visits per 1,000 members
      format:
        type: number
        decimal_places:
          type: exact
          places: 1

    - name: Total Denied Claims
      expr: SUM(denied_claims)
      display_name: Total Denied Claims
      comment: Aggregate denied claims across all members
      format:
        type: number
        decimal_places:
          type: exact
          places: 0

    - name: Denial Rate
      expr: SUM(denied_claims) * 100.0 / SUM(total_claims)
      display_name: Denial Rate %
      comment: Percentage of claims denied across the member population
      format:
        type: percentage
        decimal_places:
          type: exact
          places: 1
$$;
