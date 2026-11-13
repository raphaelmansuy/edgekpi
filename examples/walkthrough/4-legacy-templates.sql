-- Legacy KPI templates in the common registry pattern: one templated SQL text per KPI with a grouping
-- slot (../../specs/kpi/03-problem-catalogue.md, PRB-REGISTRY-TEMPLATE).
-- Input of migrate_templates.py. All four templates are synthetic.

-- kpi: sent
SELECT {{ group_by_list }}, COUNT(*) AS kpi_value
FROM message C
WHERE 1 = 1
GROUP BY {{ group_by_list }};

-- kpi: delivery_rate
SELECT {{ group_by_list }},
       COUNT(*) FILTER (WHERE C.is_delivered) * 1.0
         / NULLIF(COUNT(*), 0) AS kpi_value
FROM message C
WHERE 1 = 1
GROUP BY {{ group_by_list }};

-- kpi: reached_clients
SELECT {{ group_by_list }},
       COUNT(DISTINCT C.client_id) AS kpi_value
FROM message C
WHERE 1 = 1 AND C.is_delivered
GROUP BY {{ group_by_list }};

-- kpi: messages_per_client
SELECT {{ group_by_list }}, AVG(n) AS kpi_value
FROM (SELECT {{ group_by_list }}, client_id, COUNT(*) AS n
      FROM message GROUP BY {{ group_by_list }}, client_id) t
GROUP BY {{ group_by_list }};
