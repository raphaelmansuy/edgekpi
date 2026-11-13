BEGIN
CREATE TEMPORARY VIEW edgekpi_native_review_20261112 WITH METRICS LANGUAGE YAML AS $$
version: 1.1
source: workspace.edgekpi_spec.message
dimensions:
  - name: typology
    expr: typology
  - name: tier
    expr: tier
  - name: campaign
    expr: campaign
  - name: yr
    expr: yr
  - name: market
    expr: market
measures:
  - name: sent
    expr: COUNT(*)
  - name: delivered
    expr: COUNT(*) FILTER (WHERE is_delivered)
  - name: opened
    expr: COUNT(*) FILTER (WHERE is_opened)
  - name: clicked
    expr: COUNT(*) FILTER (WHERE is_clicked)
  - name: clients
    expr: COUNT(DISTINCT client_id)
  - name: delivery_rate
    expr: MEASURE(delivered) * 1.0 / NULLIF(MEASURE(sent), 0)
  - name: open_rate
    expr: MEASURE(opened) * 1.0 / NULLIF(MEASURE(delivered), 0)
  - name: click_rate
    expr: MEASURE(clicked) * 1.0 / NULLIF(MEASURE(delivered), 0)
  - name: ctor
    expr: MEASURE(clicked) * 1.0 / NULLIF(MEASURE(opened), 0)
$$;
SELECT typology, tier, campaign, yr, market, GROUPING_ID(typology, tier, campaign, yr, market) AS gid, MEASURE(sent) AS sent, MEASURE(delivered) AS delivered, MEASURE(opened) AS opened, MEASURE(clicked) AS clicked, MEASURE(clients) AS clients, MEASURE(delivery_rate) AS delivery_rate, MEASURE(open_rate) AS open_rate, MEASURE(click_rate) AS click_rate, MEASURE(ctor) AS ctor
FROM edgekpi_native_review_20261112
GROUP BY GROUPING SETS ((typology, tier, campaign, yr, market), (typology, tier, campaign, yr), (typology, tier, campaign), (typology, tier, yr, market), (typology, tier, yr), (typology, tier), (typology, yr, market), (typology, yr), (typology), (yr, market), (yr), ());
END