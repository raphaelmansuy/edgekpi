WITH agg AS (
  SELECT D.typology AS typology, C.market AS market,
    GROUPING_ID(D.typology, C.market) AS gid,
    COUNT(*) AS m1,
    COUNT(DISTINCT C.client_id) FILTER(WHERE C.is_delivered) AS m2,
    COUNT(*) FILTER(WHERE C.is_delivered) AS m3,
    COUNT(*) FILTER(WHERE C.is_opened) AS m4,
    COUNT(*) FILTER(WHERE C.is_clicked) AS m5
  FROM message AS C
  LEFT JOIN client AS D ON D.client_id = C.client_id
  WHERE (TRY_CAST(:start_date AS DATE) IS NULL OR CAST(C.send_date AS DATE) >= TRY_CAST(:start_date AS DATE))
    AND (TRY_CAST(:end_date AS DATE) IS NULL OR CAST(C.send_date AS DATE) < TRY_CAST(:end_date AS DATE))
  GROUP BY GROUPING SETS ((D.typology, C.market), (D.typology), (C.market), ())
  HAVING COUNT(*) > 0
)
SELECT typology, market, gid,
  m1 AS sent,
  m2 AS reached,
  TRY_DIVIDE(m3, m1) AS delivery_rate,
  TRY_DIVIDE(m4, m3) AS open_rate,
  m5 * 1.0 / NULLIF(m3, 0) AS click_rate,
  TRY_DIVIDE(m5, m4) AS ctor
FROM agg
