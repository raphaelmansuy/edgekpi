WITH agg AS (
  SELECT typology, market,
    GROUPING_ID(typology, market) AS gid,
    COUNT(*) AS sent,
    COUNT(*) FILTER (WHERE is_delivered) AS delivered,
    COUNT(DISTINCT client_id) AS unique_clients
  FROM message
  WHERE TRUE
  GROUP BY GROUPING SETS ((typology, market), (typology), (market), ())
  HAVING COUNT(*) > 0
)
SELECT typology, market, gid, sent, delivered, unique_clients, delivered * 1.0 / NULLIF(sent, 0) AS delivery_rate
FROM agg
