-- Example data for the three implementation examples: eight messages, one row per message.
-- Same rows as the worked example in ../../specs/kpi/START-HERE.md. Runs on DuckDB and on Databricks SQL.
CREATE OR REPLACE TABLE message AS
SELECT * FROM (VALUES
  (1, 'c1', 'New', 'HK', TRUE,  TRUE,  TRUE),
  (2, 'c1', 'New', 'HK', TRUE,  TRUE,  FALSE),
  (3, 'c2', 'New', 'HK', FALSE, FALSE, FALSE),
  (4, 'c3', 'New', 'SG', TRUE,  TRUE,  FALSE),
  (5, 'c4', 'VIP', 'HK', TRUE,  TRUE,  TRUE),
  (6, 'c4', 'VIP', 'SG', TRUE,  FALSE, FALSE),
  (7, 'c5', 'VIP', 'SG', TRUE,  TRUE,  TRUE),
  (8, 'c5', 'VIP', 'SG', FALSE, FALSE, FALSE)
) AS t(message_id, client_id, typology, market, is_delivered, is_opened, is_clicked);
