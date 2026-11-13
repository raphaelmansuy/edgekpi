WITH agg AS (
  SELECT typology, tier, campaign, yr, market,
    GROUPING_ID(typology, tier, campaign, yr, market) AS gid,
    COUNT(*) AS sent,
    COUNT(*) FILTER (WHERE is_delivered) AS delivered,
    COUNT(*) FILTER (WHERE is_opened) AS opened,
    COUNT(*) FILTER (WHERE is_clicked) AS clicked,
    COUNT(DISTINCT client_id) AS clients
  FROM workspace.edgekpi_spec.message
  WHERE TRUE
  GROUP BY GROUPING SETS ((typology, tier, campaign, yr, market), (typology, tier, campaign, yr), (typology, tier, campaign), (typology, tier, yr, market), (typology, tier, yr), (typology, tier), (typology, yr, market), (typology, yr), (typology), (yr, market), (yr), ())
  HAVING COUNT(*) > 0
)
SELECT typology, tier, campaign, yr, market, gid, sent, delivered, opened, clicked, clients, delivered * 1.0 / NULLIF(sent, 0) AS delivery_rate, opened * 1.0 / NULLIF(delivered, 0) AS open_rate, clicked * 1.0 / NULLIF(delivered, 0) AS click_rate, clicked * 1.0 / NULLIF(opened, 0) AS ctor
FROM agg