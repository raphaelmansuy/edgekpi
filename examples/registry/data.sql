-- Data for the harder migration test (migrate_registry.py). Synthetic. Runs on DuckDB and Databricks SQL.
-- Fact: one row per message. Dimension: one row per client. Events: several rows per message.

CREATE OR REPLACE TABLE client AS
SELECT * FROM (VALUES
  ('c1', 'New', 'Gold'),
  ('c2', 'New', 'Silver'),
  ('c3', 'New', 'Gold'),
  ('c4', 'VIP', 'Gold'),
  ('c5', 'VIP', 'Gold'),
  ('c6', 'VIP', 'Silver')
) AS t(client_id, typology, tier);

-- Message 9 is the only message of its group and is not delivered: zero denominators and an empty group.
-- Message 13 belongs to a client missing from the dimension: a genuine unknown typology.
CREATE OR REPLACE TABLE message AS
SELECT * FROM (VALUES
  (1,  'c1', 'HK', DATE '2025-03-10', TRUE,  TRUE,  TRUE),
  (2,  'c1', 'HK', DATE '2026-02-05', TRUE,  TRUE,  FALSE),
  (3,  'c2', 'HK', DATE '2026-03-12', FALSE, FALSE, FALSE),
  (4,  'c3', 'SG', DATE '2025-11-20', TRUE,  TRUE,  FALSE),
  (5,  'c4', 'HK', DATE '2026-01-15', TRUE,  TRUE,  TRUE),
  (6,  'c4', 'SG', DATE '2026-04-02', TRUE,  FALSE, FALSE),
  (7,  'c5', 'SG', DATE '2025-06-30', TRUE,  TRUE,  TRUE),
  (8,  'c5', 'SG', DATE '2026-05-18', FALSE, FALSE, FALSE),
  (9,  'c6', 'JP', DATE '2026-06-01', FALSE, FALSE, FALSE),
  (10, 'c2', 'SG', DATE '2025-09-09', TRUE,  FALSE, FALSE),
  (11, 'c3', 'HK', DATE '2026-07-07', TRUE,  TRUE,  TRUE),
  (12, 'c1', 'SG', DATE '2025-12-31', TRUE,  TRUE,  FALSE),
  (13, 'c9', 'HK', DATE '2026-08-08', TRUE,  FALSE, FALSE)
) AS t(message_id, client_id, market, send_date, is_delivered, is_opened, is_clicked);

CREATE OR REPLACE TABLE message_event AS
SELECT * FROM (VALUES
  (1, 'open'), (1, 'open'), (1, 'click'),
  (2, 'open'),
  (4, 'open'),
  (5, 'open'), (5, 'open'), (5, 'click'),
  (7, 'open'), (7, 'click'),
  (11, 'open'), (11, 'open'), (11, 'click'),
  (12, 'open')
) AS t(message_id, event_type);
