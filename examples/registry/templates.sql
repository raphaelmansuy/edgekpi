-- Registry-style templates: six engagement KPIs, plus two that must be refused.
-- Input of migrate_registry.py and of `edgekpi infer`. Databricks SQL.
--
-- Written for this repository to exercise the shapes a templated registry commonly contains: a grouping slot,
-- a dimension join, optional date parameters, Databricks functions, and three spellings of a conditional
-- count. They are examples, not copies of any production system.

-- kpi: message-sent | sent
SELECT {{ group_by_list }}, COUNT(*) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
GROUP BY {{ group_by_list }};

-- kpi: message-reached | reached
SELECT {{ group_by_list }}, COUNT(DISTINCT C.client_id) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
  AND C.is_delivered
GROUP BY {{ group_by_list }};

-- kpi: delivery-rate | delivery_rate
SELECT {{ group_by_list }},
       try_divide(COUNT_IF(C.is_delivered), COUNT(*)) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
GROUP BY {{ group_by_list }};

-- kpi: open-rate | open_rate
SELECT {{ group_by_list }},
       try_divide(COUNT_IF(C.is_opened), COUNT_IF(C.is_delivered)) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
GROUP BY {{ group_by_list }};

-- kpi: click-rate | click_rate
SELECT {{ group_by_list }},
       COUNT(*) FILTER (WHERE C.is_clicked) * 1.0
         / NULLIF(COUNT(*) FILTER (WHERE C.is_delivered), 0) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
GROUP BY {{ group_by_list }};

-- kpi: click-to-open-rate | ctor
SELECT {{ group_by_list }},
       try_divide(SUM(CASE WHEN C.is_clicked THEN 1 ELSE 0 END),
                  COUNT_IF(C.is_opened)) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
WHERE 1 = 1
  AND (try_cast(:start_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) >= try_cast(:start_date AS DATE))
  AND (try_cast(:end_date AS DATE) IS NULL
       OR CAST(C.send_date AS DATE) < try_cast(:end_date AS DATE))
GROUP BY {{ group_by_list }};

-- kpi: open-events | open_events
SELECT {{ group_by_list }}, COUNT(*) AS kpi_value
FROM message C
LEFT JOIN client D ON D.client_id = C.client_id
JOIN message_event E ON E.message_id = C.message_id
WHERE 1 = 1 AND E.event_type = 'open'
GROUP BY {{ group_by_list }};

-- kpi: messages-per-client | messages_per_client
SELECT {{ group_by_list }}, AVG(n) AS kpi_value
FROM (SELECT {{ group_by_list }}, C.client_id, COUNT(*) AS n
      FROM message C LEFT JOIN client D ON D.client_id = C.client_id
      GROUP BY {{ group_by_list }}, C.client_id) t
GROUP BY {{ group_by_list }};
