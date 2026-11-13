-- Option 1: Databricks metric view.
-- Reduced from ../../specs/kpi/validation/2026-11-12/native-s4.sql, which ran on a Databricks serverless SQL warehouse with five
-- dimensions and twelve grouping sets. This two-dimension form has NOT been executed on its own.
-- Catalog, schema and table names are examples.

-- 1. Define once. The view holds measures and formulas, and no grouping.
CREATE OR REPLACE VIEW crm.gold.engagement_kpi
WITH METRICS LANGUAGE YAML AS $$
version: 1.1
comment: "Engagement KPIs, one row per message sent"
source: crm.silver.message
dimensions:
  - name: typology
    expr: typology
  - name: market
    expr: market
measures:
  - name: sent
    expr: COUNT(*)
  - name: delivered
    expr: COUNT(*) FILTER (WHERE is_delivered)
  - name: unique_clients
    expr: COUNT(DISTINCT client_id)
  - name: delivery_rate
    expr: MEASURE(delivered) * 1.0 / NULLIF(MEASURE(sent), 0)
    comment: "Delivered messages divided by sent messages"
$$;

-- 2. Ask for a view. The reader picks the grouping; totals come from the grouping sets.
SELECT typology, market,
       GROUPING_ID(typology, market) AS gid,
       MEASURE(sent)           AS sent,
       MEASURE(delivery_rate)  AS delivery_rate,
       MEASURE(unique_clients) AS unique_clients
FROM crm.gold.engagement_kpi
GROUP BY GROUPING SETS (
  (typology, market),   -- detail cells
  (typology),           -- typology totals
  (market),             -- market totals
  ()                    -- grand total
);
