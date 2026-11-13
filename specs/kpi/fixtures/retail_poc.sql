-- fixtures/retail_poc.sql
-- Dataset of the article "Why one query per KPI breaks" (poc/sql/01_setup.sql), copied verbatim
-- so that every number in the article can be re-run. Spec home: ../04-article-reformulated.md#art-verify
CREATE OR REPLACE TABLE boutique AS
SELECT * FROM (VALUES
  ('B1', 'Pacific Place', 'HK'),
  ('B2', 'Canton Road',   'HK'),
  ('B3', 'Marina Bay',    'SG')
) AS t(boutique_id, boutique_name, market);

CREATE OR REPLACE TABLE message_sent AS
SELECT message_id, client_id, channel, market, CAST(sent_date AS DATE) AS sent_date FROM (VALUES
  (1,  'C1', 'Email',  'HK', '2026-10-02'),
  (2,  'C1', 'SMS',    'HK', '2026-10-05'),
  (3,  'C2', 'Email',  'HK', '2026-10-03'),
  (4,  'C3', 'WeChat', 'HK', '2026-10-04'),
  (5,  'C3', 'Email',  'HK', '2026-10-09'),
  (6,  'C4', 'SMS',    'SG', '2026-10-02'),
  (7,  'C4', 'SMS',    'SG', '2026-10-12'),
  (8,  'C5', 'Email',  'SG', '2026-10-06'),
  (9,  'C5', 'WeChat', 'SG', '2026-10-07'),
  (10, 'C6', 'Email',  'SG', '2026-10-08')
) AS t(message_id, client_id, channel, market, sent_date);

CREATE OR REPLACE TABLE sales_txn AS
SELECT txn_id, client_id, boutique_id, CAST(txn_date AS DATE) AS txn_date, CAST(net_amount AS DECIMAL(12,2)) AS net_amount FROM (VALUES
  ('T1',  'C1', 'B1', '2026-10-10', 1200),
  ('T2',  'C2', 'B1', '2026-10-11',  800),
  ('T3',  'C2', 'B1', '2026-10-18',  400),
  ('T4',  'C3', 'B2', '2026-10-12', 3000),
  ('T5',  'C1', 'B2', '2026-10-15',  600),
  ('T6',  'C5', 'B3', '2026-10-13', 2500),
  ('T7',  'C5', 'B3', '2026-10-20', 1500),
  ('T8',  'C6', 'B3', '2026-10-21', 1000),
  ('T9',  'C1', 'B1', '2025-10-09', 2000),
  ('T10', 'C3', 'B2', '2025-10-14', 4000),
  ('T11', 'C5', 'B3', '2025-10-18', 4000)
) AS t(txn_id, client_id, boutique_id, txn_date, net_amount);
