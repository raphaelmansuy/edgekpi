WITH agg AS (
  SELECT typology, market,
    GROUPING_ID(typology, market) AS gid,
    COUNT(*) AS m1,
    COUNT(*) FILTER(WHERE C.is_delivered) AS m2,
    COUNT(DISTINCT C.client_id) FILTER(WHERE C.is_delivered) AS m3
  FROM message AS C
  WHERE TRUE
  GROUP BY GROUPING SETS ((typology, market), (typology), (market), ())
  HAVING COUNT(*) > 0
)
SELECT typology, market, gid,
  m1 AS sent,
  m2 * 1.0 / NULLIF(m1, 0) AS delivery_rate,
  m3 AS reached_clients
FROM agg
