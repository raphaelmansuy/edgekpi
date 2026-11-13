-- fixtures/s4_messages_databricks.sql
-- Databricks SQL port of s4_messages.sql. Same 12 cells, same 1,050 messages, same expected grid.
-- Differences from the DuckDB file: explode(sequence()) instead of LATERAL generate_series,
-- row_number() needs an ORDER BY, and STRING instead of VARCHAR.
CREATE OR REPLACE TABLE cell AS
SELECT * FROM (VALUES
  ('New',      'Gold',   'A', 2025, 'HK', 100, 0.80,  0),
  ('New',      'Gold',   'A', 2025, 'SG',  50, 0.90, 30),
  ('New',      'Gold',   'A', 2026, 'HK', 200, 0.90, 60),
  ('New',      'Gold',   'A', 2026, 'SG', 100, 0.80, 90),
  ('New',      'Gold',   'B', 2025, 'HK', 100, 0.70, 15),
  ('New',      'Gold',   'B', 2025, 'SG',  50, 0.80, 45),
  ('New',      'Gold',   'B', 2026, 'HK', 100, 0.90, 75),
  ('New',      'Gold',   'B', 2026, 'SG',  50, 0.90,  5),
  ('Existing', 'Silver', 'C', 2025, 'HK',  50, 0.80,  0),
  ('Existing', 'Silver', 'C', 2025, 'SG', 100, 0.70, 10),
  ('Existing', 'Silver', 'C', 2026, 'HK',  50, 0.90, 20),
  ('Existing', 'Silver', 'C', 2026, 'SG', 100, 0.80, 30)
) AS t(typology, tier, campaign, yr, market, sent, dr, client_offset);

CREATE OR REPLACE TABLE message AS
SELECT
  row_number() OVER (ORDER BY c.typology, c.tier, c.campaign, c.yr, c.market, g.i) AS message_id,
  CONCAT(CASE c.typology WHEN 'New' THEN 'N' ELSE 'E' END,
         lpad(CAST(((c.client_offset + g.i) % CASE c.typology WHEN 'New' THEN 120 ELSE 60 END) + 1 AS STRING), 3, '0')) AS client_id,
  c.typology, c.tier, c.campaign, c.yr, c.market,
  make_date(c.yr, 3, 15)                                                          AS send_date,
  (g.i <= round(c.sent * c.dr))                                                   AS is_delivered,
  (g.i <= round(c.sent * c.dr) AND (g.i + c.client_offset) % 7 IN (0, 1, 2))      AS is_opened,
  (g.i <= round(c.sent * c.dr) AND (g.i + c.client_offset) % 7 = 0)               AS is_clicked
FROM cell c LATERAL VIEW explode(sequence(1, c.sent)) g AS i;
