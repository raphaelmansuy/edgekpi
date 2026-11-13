WITH __stage0 AS (
  SELECT
    group_set,
    CASE WHEN group_set=0 THEN
      COUNT(1)
      END as "sent__0",
    CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__0",
    CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__0",
    CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__0",
    CASE WHEN group_set=0 THEN
      count(distinct base."client_id")
      END as "clients__0",
    (CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=0 THEN
      COUNT(1)
      END),0)) as "delivery_rate__0",
    (CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__0",
    (CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__0",
    (CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=0 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__0",
    CASE WHEN group_set IN (1,2) THEN
      base."yr"
      END as "yr__1",
    CASE WHEN group_set=1 THEN
      COUNT(1)
      END as "sent__1",
    CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__1",
    CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__1",
    CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__1",
    CASE WHEN group_set=1 THEN
      count(distinct base."client_id")
      END as "clients__1",
    (CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=1 THEN
      COUNT(1)
      END),0)) as "delivery_rate__1",
    (CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__1",
    (CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__1",
    (CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=1 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__1",
    CASE WHEN group_set=2 THEN
      base."market"
      END as "market__2",
    CASE WHEN group_set=2 THEN
      COUNT(1)
      END as "sent__2",
    CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__2",
    CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__2",
    CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__2",
    CASE WHEN group_set=2 THEN
      count(distinct base."client_id")
      END as "clients__2",
    (CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=2 THEN
      COUNT(1)
      END),0)) as "delivery_rate__2",
    (CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__2",
    (CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__2",
    (CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=2 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__2",
    CASE WHEN group_set IN (3,4,5,6,7,8,9,10,11) THEN
      base."typology"
      END as "typology__3",
    CASE WHEN group_set=3 THEN
      COUNT(1)
      END as "sent__3",
    CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__3",
    CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__3",
    CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__3",
    CASE WHEN group_set=3 THEN
      count(distinct base."client_id")
      END as "clients__3",
    (CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=3 THEN
      COUNT(1)
      END),0)) as "delivery_rate__3",
    (CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__3",
    (CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__3",
    (CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=3 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__3",
    CASE WHEN group_set IN (4,5) THEN
      base."yr"
      END as "yr__4",
    CASE WHEN group_set=4 THEN
      COUNT(1)
      END as "sent__4",
    CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__4",
    CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__4",
    CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__4",
    CASE WHEN group_set=4 THEN
      count(distinct base."client_id")
      END as "clients__4",
    (CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=4 THEN
      COUNT(1)
      END),0)) as "delivery_rate__4",
    (CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__4",
    (CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__4",
    (CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=4 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__4",
    CASE WHEN group_set=5 THEN
      base."market"
      END as "market__5",
    CASE WHEN group_set=5 THEN
      COUNT(1)
      END as "sent__5",
    CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__5",
    CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__5",
    CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__5",
    CASE WHEN group_set=5 THEN
      count(distinct base."client_id")
      END as "clients__5",
    (CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=5 THEN
      COUNT(1)
      END),0)) as "delivery_rate__5",
    (CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__5",
    (CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__5",
    (CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=5 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__5",
    CASE WHEN group_set IN (6,7,8,9,10,11) THEN
      base."tier"
      END as "tier__6",
    CASE WHEN group_set=6 THEN
      COUNT(1)
      END as "sent__6",
    CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__6",
    CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__6",
    CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__6",
    CASE WHEN group_set=6 THEN
      count(distinct base."client_id")
      END as "clients__6",
    (CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=6 THEN
      COUNT(1)
      END),0)) as "delivery_rate__6",
    (CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__6",
    (CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__6",
    (CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=6 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__6",
    CASE WHEN group_set IN (7,8) THEN
      base."yr"
      END as "yr__7",
    CASE WHEN group_set=7 THEN
      COUNT(1)
      END as "sent__7",
    CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__7",
    CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__7",
    CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__7",
    CASE WHEN group_set=7 THEN
      count(distinct base."client_id")
      END as "clients__7",
    (CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=7 THEN
      COUNT(1)
      END),0)) as "delivery_rate__7",
    (CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__7",
    (CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__7",
    (CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=7 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__7",
    CASE WHEN group_set=8 THEN
      base."market"
      END as "market__8",
    CASE WHEN group_set=8 THEN
      COUNT(1)
      END as "sent__8",
    CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__8",
    CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__8",
    CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__8",
    CASE WHEN group_set=8 THEN
      count(distinct base."client_id")
      END as "clients__8",
    (CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=8 THEN
      COUNT(1)
      END),0)) as "delivery_rate__8",
    (CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__8",
    (CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__8",
    (CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=8 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__8",
    CASE WHEN group_set IN (9,10,11) THEN
      base."campaign"
      END as "campaign__9",
    CASE WHEN group_set=9 THEN
      COUNT(1)
      END as "sent__9",
    CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__9",
    CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__9",
    CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__9",
    CASE WHEN group_set=9 THEN
      count(distinct base."client_id")
      END as "clients__9",
    (CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=9 THEN
      COUNT(1)
      END),0)) as "delivery_rate__9",
    (CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__9",
    (CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__9",
    (CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=9 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__9",
    CASE WHEN group_set IN (10,11) THEN
      base."yr"
      END as "yr__10",
    CASE WHEN group_set=10 THEN
      COUNT(1)
      END as "sent__10",
    CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__10",
    CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__10",
    CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__10",
    CASE WHEN group_set=10 THEN
      count(distinct base."client_id")
      END as "clients__10",
    (CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=10 THEN
      COUNT(1)
      END),0)) as "delivery_rate__10",
    (CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__10",
    (CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__10",
    (CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=10 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__10",
    CASE WHEN group_set=11 THEN
      base."market"
      END as "market__11",
    CASE WHEN group_set=11 THEN
      COUNT(1)
      END as "sent__11",
    CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END as "delivered__11",
    CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END as "opened__11",
    CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END as "clicked__11",
    CASE WHEN group_set=11 THEN
      count(distinct base."client_id")
      END as "clients__11",
    (CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=11 THEN
      COUNT(1)
      END),0)) as "delivery_rate__11",
    (CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "open_rate__11",
    (CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_delivered" THEN 1 END)
      END),0)) as "click_rate__11",
    (CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_clicked" THEN 1 END)
      END)*1.0/(NULLIF((CASE WHEN group_set=11 THEN
      COUNT(CASE WHEN base."is_opened" THEN 1 END)
      END),0)) as "ctor__11"
  FROM message as base
  CROSS JOIN (SELECT UNNEST(GENERATE_SERIES(0,11,1)) as group_set  ) as group_set
  GROUP BY 1,11,21,31,41,51,61,71,81,91,101,111
)
, __stage1 AS (
  SELECT 
    CASE WHEN group_set=11 THEN 10 ELSE group_set END as group_set,
    FIRST("sent__0") FILTER (WHERE "sent__0" IS NOT NULL) as "sent__0",
    FIRST("delivered__0") FILTER (WHERE "delivered__0" IS NOT NULL) as "delivered__0",
    FIRST("opened__0") FILTER (WHERE "opened__0" IS NOT NULL) as "opened__0",
    FIRST("clicked__0") FILTER (WHERE "clicked__0" IS NOT NULL) as "clicked__0",
    FIRST("clients__0") FILTER (WHERE "clients__0" IS NOT NULL) as "clients__0",
    FIRST("delivery_rate__0") FILTER (WHERE "delivery_rate__0" IS NOT NULL) as "delivery_rate__0",
    FIRST("open_rate__0") FILTER (WHERE "open_rate__0" IS NOT NULL) as "open_rate__0",
    FIRST("click_rate__0") FILTER (WHERE "click_rate__0" IS NOT NULL) as "click_rate__0",
    FIRST("ctor__0") FILTER (WHERE "ctor__0" IS NOT NULL) as "ctor__0",
    CASE WHEN group_set IN (1,2) THEN
      "yr__1"
      END as "yr__1",
    FIRST("sent__1") FILTER (WHERE "sent__1" IS NOT NULL) as "sent__1",
    FIRST("delivered__1") FILTER (WHERE "delivered__1" IS NOT NULL) as "delivered__1",
    FIRST("opened__1") FILTER (WHERE "opened__1" IS NOT NULL) as "opened__1",
    FIRST("clicked__1") FILTER (WHERE "clicked__1" IS NOT NULL) as "clicked__1",
    FIRST("clients__1") FILTER (WHERE "clients__1" IS NOT NULL) as "clients__1",
    FIRST("delivery_rate__1") FILTER (WHERE "delivery_rate__1" IS NOT NULL) as "delivery_rate__1",
    FIRST("open_rate__1") FILTER (WHERE "open_rate__1" IS NOT NULL) as "open_rate__1",
    FIRST("click_rate__1") FILTER (WHERE "click_rate__1" IS NOT NULL) as "click_rate__1",
    FIRST("ctor__1") FILTER (WHERE "ctor__1" IS NOT NULL) as "ctor__1",
    CASE WHEN group_set=2 THEN
      "market__2"
      END as "market__2",
    FIRST("sent__2") FILTER (WHERE "sent__2" IS NOT NULL) as "sent__2",
    FIRST("delivered__2") FILTER (WHERE "delivered__2" IS NOT NULL) as "delivered__2",
    FIRST("opened__2") FILTER (WHERE "opened__2" IS NOT NULL) as "opened__2",
    FIRST("clicked__2") FILTER (WHERE "clicked__2" IS NOT NULL) as "clicked__2",
    FIRST("clients__2") FILTER (WHERE "clients__2" IS NOT NULL) as "clients__2",
    FIRST("delivery_rate__2") FILTER (WHERE "delivery_rate__2" IS NOT NULL) as "delivery_rate__2",
    FIRST("open_rate__2") FILTER (WHERE "open_rate__2" IS NOT NULL) as "open_rate__2",
    FIRST("click_rate__2") FILTER (WHERE "click_rate__2" IS NOT NULL) as "click_rate__2",
    FIRST("ctor__2") FILTER (WHERE "ctor__2" IS NOT NULL) as "ctor__2",
    CASE WHEN group_set IN (3,4,5,6,7,8,9,10,11) THEN
      "typology__3"
      END as "typology__3",
    FIRST("sent__3") FILTER (WHERE "sent__3" IS NOT NULL) as "sent__3",
    FIRST("delivered__3") FILTER (WHERE "delivered__3" IS NOT NULL) as "delivered__3",
    FIRST("opened__3") FILTER (WHERE "opened__3" IS NOT NULL) as "opened__3",
    FIRST("clicked__3") FILTER (WHERE "clicked__3" IS NOT NULL) as "clicked__3",
    FIRST("clients__3") FILTER (WHERE "clients__3" IS NOT NULL) as "clients__3",
    FIRST("delivery_rate__3") FILTER (WHERE "delivery_rate__3" IS NOT NULL) as "delivery_rate__3",
    FIRST("open_rate__3") FILTER (WHERE "open_rate__3" IS NOT NULL) as "open_rate__3",
    FIRST("click_rate__3") FILTER (WHERE "click_rate__3" IS NOT NULL) as "click_rate__3",
    FIRST("ctor__3") FILTER (WHERE "ctor__3" IS NOT NULL) as "ctor__3",
    CASE WHEN group_set IN (4,5) THEN
      "yr__4"
      END as "yr__4",
    FIRST("sent__4") FILTER (WHERE "sent__4" IS NOT NULL) as "sent__4",
    FIRST("delivered__4") FILTER (WHERE "delivered__4" IS NOT NULL) as "delivered__4",
    FIRST("opened__4") FILTER (WHERE "opened__4" IS NOT NULL) as "opened__4",
    FIRST("clicked__4") FILTER (WHERE "clicked__4" IS NOT NULL) as "clicked__4",
    FIRST("clients__4") FILTER (WHERE "clients__4" IS NOT NULL) as "clients__4",
    FIRST("delivery_rate__4") FILTER (WHERE "delivery_rate__4" IS NOT NULL) as "delivery_rate__4",
    FIRST("open_rate__4") FILTER (WHERE "open_rate__4" IS NOT NULL) as "open_rate__4",
    FIRST("click_rate__4") FILTER (WHERE "click_rate__4" IS NOT NULL) as "click_rate__4",
    FIRST("ctor__4") FILTER (WHERE "ctor__4" IS NOT NULL) as "ctor__4",
    CASE WHEN group_set=5 THEN
      "market__5"
      END as "market__5",
    FIRST("sent__5") FILTER (WHERE "sent__5" IS NOT NULL) as "sent__5",
    FIRST("delivered__5") FILTER (WHERE "delivered__5" IS NOT NULL) as "delivered__5",
    FIRST("opened__5") FILTER (WHERE "opened__5" IS NOT NULL) as "opened__5",
    FIRST("clicked__5") FILTER (WHERE "clicked__5" IS NOT NULL) as "clicked__5",
    FIRST("clients__5") FILTER (WHERE "clients__5" IS NOT NULL) as "clients__5",
    FIRST("delivery_rate__5") FILTER (WHERE "delivery_rate__5" IS NOT NULL) as "delivery_rate__5",
    FIRST("open_rate__5") FILTER (WHERE "open_rate__5" IS NOT NULL) as "open_rate__5",
    FIRST("click_rate__5") FILTER (WHERE "click_rate__5" IS NOT NULL) as "click_rate__5",
    FIRST("ctor__5") FILTER (WHERE "ctor__5" IS NOT NULL) as "ctor__5",
    CASE WHEN group_set IN (6,7,8,9,10,11) THEN
      "tier__6"
      END as "tier__6",
    FIRST("sent__6") FILTER (WHERE "sent__6" IS NOT NULL) as "sent__6",
    FIRST("delivered__6") FILTER (WHERE "delivered__6" IS NOT NULL) as "delivered__6",
    FIRST("opened__6") FILTER (WHERE "opened__6" IS NOT NULL) as "opened__6",
    FIRST("clicked__6") FILTER (WHERE "clicked__6" IS NOT NULL) as "clicked__6",
    FIRST("clients__6") FILTER (WHERE "clients__6" IS NOT NULL) as "clients__6",
    FIRST("delivery_rate__6") FILTER (WHERE "delivery_rate__6" IS NOT NULL) as "delivery_rate__6",
    FIRST("open_rate__6") FILTER (WHERE "open_rate__6" IS NOT NULL) as "open_rate__6",
    FIRST("click_rate__6") FILTER (WHERE "click_rate__6" IS NOT NULL) as "click_rate__6",
    FIRST("ctor__6") FILTER (WHERE "ctor__6" IS NOT NULL) as "ctor__6",
    CASE WHEN group_set IN (7,8) THEN
      "yr__7"
      END as "yr__7",
    FIRST("sent__7") FILTER (WHERE "sent__7" IS NOT NULL) as "sent__7",
    FIRST("delivered__7") FILTER (WHERE "delivered__7" IS NOT NULL) as "delivered__7",
    FIRST("opened__7") FILTER (WHERE "opened__7" IS NOT NULL) as "opened__7",
    FIRST("clicked__7") FILTER (WHERE "clicked__7" IS NOT NULL) as "clicked__7",
    FIRST("clients__7") FILTER (WHERE "clients__7" IS NOT NULL) as "clients__7",
    FIRST("delivery_rate__7") FILTER (WHERE "delivery_rate__7" IS NOT NULL) as "delivery_rate__7",
    FIRST("open_rate__7") FILTER (WHERE "open_rate__7" IS NOT NULL) as "open_rate__7",
    FIRST("click_rate__7") FILTER (WHERE "click_rate__7" IS NOT NULL) as "click_rate__7",
    FIRST("ctor__7") FILTER (WHERE "ctor__7" IS NOT NULL) as "ctor__7",
    CASE WHEN group_set=8 THEN
      "market__8"
      END as "market__8",
    FIRST("sent__8") FILTER (WHERE "sent__8" IS NOT NULL) as "sent__8",
    FIRST("delivered__8") FILTER (WHERE "delivered__8" IS NOT NULL) as "delivered__8",
    FIRST("opened__8") FILTER (WHERE "opened__8" IS NOT NULL) as "opened__8",
    FIRST("clicked__8") FILTER (WHERE "clicked__8" IS NOT NULL) as "clicked__8",
    FIRST("clients__8") FILTER (WHERE "clients__8" IS NOT NULL) as "clients__8",
    FIRST("delivery_rate__8") FILTER (WHERE "delivery_rate__8" IS NOT NULL) as "delivery_rate__8",
    FIRST("open_rate__8") FILTER (WHERE "open_rate__8" IS NOT NULL) as "open_rate__8",
    FIRST("click_rate__8") FILTER (WHERE "click_rate__8" IS NOT NULL) as "click_rate__8",
    FIRST("ctor__8") FILTER (WHERE "ctor__8" IS NOT NULL) as "ctor__8",
    CASE WHEN group_set IN (9,10,11) THEN
      "campaign__9"
      END as "campaign__9",
    FIRST("sent__9") FILTER (WHERE "sent__9" IS NOT NULL) as "sent__9",
    FIRST("delivered__9") FILTER (WHERE "delivered__9" IS NOT NULL) as "delivered__9",
    FIRST("opened__9") FILTER (WHERE "opened__9" IS NOT NULL) as "opened__9",
    FIRST("clicked__9") FILTER (WHERE "clicked__9" IS NOT NULL) as "clicked__9",
    FIRST("clients__9") FILTER (WHERE "clients__9" IS NOT NULL) as "clients__9",
    FIRST("delivery_rate__9") FILTER (WHERE "delivery_rate__9" IS NOT NULL) as "delivery_rate__9",
    FIRST("open_rate__9") FILTER (WHERE "open_rate__9" IS NOT NULL) as "open_rate__9",
    FIRST("click_rate__9") FILTER (WHERE "click_rate__9" IS NOT NULL) as "click_rate__9",
    FIRST("ctor__9") FILTER (WHERE "ctor__9" IS NOT NULL) as "ctor__9",
    CASE WHEN group_set IN (10,11) THEN
      "yr__10"
      END as "yr__10",
    FIRST("sent__10") FILTER (WHERE "sent__10" IS NOT NULL) as "sent__10",
    FIRST("delivered__10") FILTER (WHERE "delivered__10" IS NOT NULL) as "delivered__10",
    FIRST("opened__10") FILTER (WHERE "opened__10" IS NOT NULL) as "opened__10",
    FIRST("clicked__10") FILTER (WHERE "clicked__10" IS NOT NULL) as "clicked__10",
    FIRST("clients__10") FILTER (WHERE "clients__10" IS NOT NULL) as "clients__10",
    FIRST("delivery_rate__10") FILTER (WHERE "delivery_rate__10" IS NOT NULL) as "delivery_rate__10",
    FIRST("open_rate__10") FILTER (WHERE "open_rate__10" IS NOT NULL) as "open_rate__10",
    FIRST("click_rate__10") FILTER (WHERE "click_rate__10" IS NOT NULL) as "click_rate__10",
    FIRST("ctor__10") FILTER (WHERE "ctor__10" IS NOT NULL) as "ctor__10",
    COALESCE(LIST({
      "market": "market__11", 
      "sent": "sent__11", 
      "delivered": "delivered__11", 
      "opened": "opened__11", 
      "clicked": "clicked__11", 
      "clients": "clients__11", 
      "delivery_rate": "delivery_rate__11", 
      "open_rate": "open_rate__11", 
      "click_rate": "click_rate__11", 
      "ctor": "ctor__11"}  ORDER BY  "sent__11" DESC NULLS LAST) FILTER (WHERE group_set=11),[]) as "by_market__10"
  FROM __stage0
  GROUP BY 1,11,21,31,41,51,61,71,81,91,101
)
, __stage2 AS (
  SELECT 
    CASE WHEN group_set=8 THEN 7 WHEN group_set=10 THEN 9 ELSE group_set END as group_set,
    FIRST("sent__0") FILTER (WHERE "sent__0" IS NOT NULL) as "sent__0",
    FIRST("delivered__0") FILTER (WHERE "delivered__0" IS NOT NULL) as "delivered__0",
    FIRST("opened__0") FILTER (WHERE "opened__0" IS NOT NULL) as "opened__0",
    FIRST("clicked__0") FILTER (WHERE "clicked__0" IS NOT NULL) as "clicked__0",
    FIRST("clients__0") FILTER (WHERE "clients__0" IS NOT NULL) as "clients__0",
    FIRST("delivery_rate__0") FILTER (WHERE "delivery_rate__0" IS NOT NULL) as "delivery_rate__0",
    FIRST("open_rate__0") FILTER (WHERE "open_rate__0" IS NOT NULL) as "open_rate__0",
    FIRST("click_rate__0") FILTER (WHERE "click_rate__0" IS NOT NULL) as "click_rate__0",
    FIRST("ctor__0") FILTER (WHERE "ctor__0" IS NOT NULL) as "ctor__0",
    CASE WHEN group_set IN (1,2) THEN
      "yr__1"
      END as "yr__1",
    FIRST("sent__1") FILTER (WHERE "sent__1" IS NOT NULL) as "sent__1",
    FIRST("delivered__1") FILTER (WHERE "delivered__1" IS NOT NULL) as "delivered__1",
    FIRST("opened__1") FILTER (WHERE "opened__1" IS NOT NULL) as "opened__1",
    FIRST("clicked__1") FILTER (WHERE "clicked__1" IS NOT NULL) as "clicked__1",
    FIRST("clients__1") FILTER (WHERE "clients__1" IS NOT NULL) as "clients__1",
    FIRST("delivery_rate__1") FILTER (WHERE "delivery_rate__1" IS NOT NULL) as "delivery_rate__1",
    FIRST("open_rate__1") FILTER (WHERE "open_rate__1" IS NOT NULL) as "open_rate__1",
    FIRST("click_rate__1") FILTER (WHERE "click_rate__1" IS NOT NULL) as "click_rate__1",
    FIRST("ctor__1") FILTER (WHERE "ctor__1" IS NOT NULL) as "ctor__1",
    CASE WHEN group_set=2 THEN
      "market__2"
      END as "market__2",
    FIRST("sent__2") FILTER (WHERE "sent__2" IS NOT NULL) as "sent__2",
    FIRST("delivered__2") FILTER (WHERE "delivered__2" IS NOT NULL) as "delivered__2",
    FIRST("opened__2") FILTER (WHERE "opened__2" IS NOT NULL) as "opened__2",
    FIRST("clicked__2") FILTER (WHERE "clicked__2" IS NOT NULL) as "clicked__2",
    FIRST("clients__2") FILTER (WHERE "clients__2" IS NOT NULL) as "clients__2",
    FIRST("delivery_rate__2") FILTER (WHERE "delivery_rate__2" IS NOT NULL) as "delivery_rate__2",
    FIRST("open_rate__2") FILTER (WHERE "open_rate__2" IS NOT NULL) as "open_rate__2",
    FIRST("click_rate__2") FILTER (WHERE "click_rate__2" IS NOT NULL) as "click_rate__2",
    FIRST("ctor__2") FILTER (WHERE "ctor__2" IS NOT NULL) as "ctor__2",
    CASE WHEN group_set IN (3,4,5,6,7,8,9,10,11) THEN
      "typology__3"
      END as "typology__3",
    FIRST("sent__3") FILTER (WHERE "sent__3" IS NOT NULL) as "sent__3",
    FIRST("delivered__3") FILTER (WHERE "delivered__3" IS NOT NULL) as "delivered__3",
    FIRST("opened__3") FILTER (WHERE "opened__3" IS NOT NULL) as "opened__3",
    FIRST("clicked__3") FILTER (WHERE "clicked__3" IS NOT NULL) as "clicked__3",
    FIRST("clients__3") FILTER (WHERE "clients__3" IS NOT NULL) as "clients__3",
    FIRST("delivery_rate__3") FILTER (WHERE "delivery_rate__3" IS NOT NULL) as "delivery_rate__3",
    FIRST("open_rate__3") FILTER (WHERE "open_rate__3" IS NOT NULL) as "open_rate__3",
    FIRST("click_rate__3") FILTER (WHERE "click_rate__3" IS NOT NULL) as "click_rate__3",
    FIRST("ctor__3") FILTER (WHERE "ctor__3" IS NOT NULL) as "ctor__3",
    CASE WHEN group_set IN (4,5) THEN
      "yr__4"
      END as "yr__4",
    FIRST("sent__4") FILTER (WHERE "sent__4" IS NOT NULL) as "sent__4",
    FIRST("delivered__4") FILTER (WHERE "delivered__4" IS NOT NULL) as "delivered__4",
    FIRST("opened__4") FILTER (WHERE "opened__4" IS NOT NULL) as "opened__4",
    FIRST("clicked__4") FILTER (WHERE "clicked__4" IS NOT NULL) as "clicked__4",
    FIRST("clients__4") FILTER (WHERE "clients__4" IS NOT NULL) as "clients__4",
    FIRST("delivery_rate__4") FILTER (WHERE "delivery_rate__4" IS NOT NULL) as "delivery_rate__4",
    FIRST("open_rate__4") FILTER (WHERE "open_rate__4" IS NOT NULL) as "open_rate__4",
    FIRST("click_rate__4") FILTER (WHERE "click_rate__4" IS NOT NULL) as "click_rate__4",
    FIRST("ctor__4") FILTER (WHERE "ctor__4" IS NOT NULL) as "ctor__4",
    CASE WHEN group_set=5 THEN
      "market__5"
      END as "market__5",
    FIRST("sent__5") FILTER (WHERE "sent__5" IS NOT NULL) as "sent__5",
    FIRST("delivered__5") FILTER (WHERE "delivered__5" IS NOT NULL) as "delivered__5",
    FIRST("opened__5") FILTER (WHERE "opened__5" IS NOT NULL) as "opened__5",
    FIRST("clicked__5") FILTER (WHERE "clicked__5" IS NOT NULL) as "clicked__5",
    FIRST("clients__5") FILTER (WHERE "clients__5" IS NOT NULL) as "clients__5",
    FIRST("delivery_rate__5") FILTER (WHERE "delivery_rate__5" IS NOT NULL) as "delivery_rate__5",
    FIRST("open_rate__5") FILTER (WHERE "open_rate__5" IS NOT NULL) as "open_rate__5",
    FIRST("click_rate__5") FILTER (WHERE "click_rate__5" IS NOT NULL) as "click_rate__5",
    FIRST("ctor__5") FILTER (WHERE "ctor__5" IS NOT NULL) as "ctor__5",
    CASE WHEN group_set IN (6,7,8,9,10,11) THEN
      "tier__6"
      END as "tier__6",
    FIRST("sent__6") FILTER (WHERE "sent__6" IS NOT NULL) as "sent__6",
    FIRST("delivered__6") FILTER (WHERE "delivered__6" IS NOT NULL) as "delivered__6",
    FIRST("opened__6") FILTER (WHERE "opened__6" IS NOT NULL) as "opened__6",
    FIRST("clicked__6") FILTER (WHERE "clicked__6" IS NOT NULL) as "clicked__6",
    FIRST("clients__6") FILTER (WHERE "clients__6" IS NOT NULL) as "clients__6",
    FIRST("delivery_rate__6") FILTER (WHERE "delivery_rate__6" IS NOT NULL) as "delivery_rate__6",
    FIRST("open_rate__6") FILTER (WHERE "open_rate__6" IS NOT NULL) as "open_rate__6",
    FIRST("click_rate__6") FILTER (WHERE "click_rate__6" IS NOT NULL) as "click_rate__6",
    FIRST("ctor__6") FILTER (WHERE "ctor__6" IS NOT NULL) as "ctor__6",
    CASE WHEN group_set IN (7,8) THEN
      "yr__7"
      END as "yr__7",
    FIRST("sent__7") FILTER (WHERE "sent__7" IS NOT NULL) as "sent__7",
    FIRST("delivered__7") FILTER (WHERE "delivered__7" IS NOT NULL) as "delivered__7",
    FIRST("opened__7") FILTER (WHERE "opened__7" IS NOT NULL) as "opened__7",
    FIRST("clicked__7") FILTER (WHERE "clicked__7" IS NOT NULL) as "clicked__7",
    FIRST("clients__7") FILTER (WHERE "clients__7" IS NOT NULL) as "clients__7",
    FIRST("delivery_rate__7") FILTER (WHERE "delivery_rate__7" IS NOT NULL) as "delivery_rate__7",
    FIRST("open_rate__7") FILTER (WHERE "open_rate__7" IS NOT NULL) as "open_rate__7",
    FIRST("click_rate__7") FILTER (WHERE "click_rate__7" IS NOT NULL) as "click_rate__7",
    FIRST("ctor__7") FILTER (WHERE "ctor__7" IS NOT NULL) as "ctor__7",
    COALESCE(LIST({
      "market": "market__8", 
      "sent": "sent__8", 
      "delivered": "delivered__8", 
      "opened": "opened__8", 
      "clicked": "clicked__8", 
      "clients": "clients__8", 
      "delivery_rate": "delivery_rate__8", 
      "open_rate": "open_rate__8", 
      "click_rate": "click_rate__8", 
      "ctor": "ctor__8"}  ORDER BY  "sent__8" DESC NULLS LAST) FILTER (WHERE group_set=8),[]) as "by_market__7",
    CASE WHEN group_set IN (9,10,11) THEN
      "campaign__9"
      END as "campaign__9",
    FIRST("sent__9") FILTER (WHERE "sent__9" IS NOT NULL) as "sent__9",
    FIRST("delivered__9") FILTER (WHERE "delivered__9" IS NOT NULL) as "delivered__9",
    FIRST("opened__9") FILTER (WHERE "opened__9" IS NOT NULL) as "opened__9",
    FIRST("clicked__9") FILTER (WHERE "clicked__9" IS NOT NULL) as "clicked__9",
    FIRST("clients__9") FILTER (WHERE "clients__9" IS NOT NULL) as "clients__9",
    FIRST("delivery_rate__9") FILTER (WHERE "delivery_rate__9" IS NOT NULL) as "delivery_rate__9",
    FIRST("open_rate__9") FILTER (WHERE "open_rate__9" IS NOT NULL) as "open_rate__9",
    FIRST("click_rate__9") FILTER (WHERE "click_rate__9" IS NOT NULL) as "click_rate__9",
    FIRST("ctor__9") FILTER (WHERE "ctor__9" IS NOT NULL) as "ctor__9",
    COALESCE(LIST({
      "yr": "yr__10", 
      "sent": "sent__10", 
      "delivered": "delivered__10", 
      "opened": "opened__10", 
      "clicked": "clicked__10", 
      "clients": "clients__10", 
      "delivery_rate": "delivery_rate__10", 
      "open_rate": "open_rate__10", 
      "click_rate": "click_rate__10", 
      "ctor": "ctor__10", 
      "by_market": "by_market__10"}  ORDER BY  "sent__10" DESC NULLS LAST) FILTER (WHERE group_set=10),[]) as "by_year__9"
  FROM __stage1
  GROUP BY 1,11,21,31,41,51,61,71,82
)
, __stage3 AS (
  SELECT 
    CASE WHEN group_set=5 THEN 4 WHEN group_set=7 THEN 6 WHEN group_set=9 THEN 6 ELSE group_set END as group_set,
    FIRST("sent__0") FILTER (WHERE "sent__0" IS NOT NULL) as "sent__0",
    FIRST("delivered__0") FILTER (WHERE "delivered__0" IS NOT NULL) as "delivered__0",
    FIRST("opened__0") FILTER (WHERE "opened__0" IS NOT NULL) as "opened__0",
    FIRST("clicked__0") FILTER (WHERE "clicked__0" IS NOT NULL) as "clicked__0",
    FIRST("clients__0") FILTER (WHERE "clients__0" IS NOT NULL) as "clients__0",
    FIRST("delivery_rate__0") FILTER (WHERE "delivery_rate__0" IS NOT NULL) as "delivery_rate__0",
    FIRST("open_rate__0") FILTER (WHERE "open_rate__0" IS NOT NULL) as "open_rate__0",
    FIRST("click_rate__0") FILTER (WHERE "click_rate__0" IS NOT NULL) as "click_rate__0",
    FIRST("ctor__0") FILTER (WHERE "ctor__0" IS NOT NULL) as "ctor__0",
    CASE WHEN group_set IN (1,2) THEN
      "yr__1"
      END as "yr__1",
    FIRST("sent__1") FILTER (WHERE "sent__1" IS NOT NULL) as "sent__1",
    FIRST("delivered__1") FILTER (WHERE "delivered__1" IS NOT NULL) as "delivered__1",
    FIRST("opened__1") FILTER (WHERE "opened__1" IS NOT NULL) as "opened__1",
    FIRST("clicked__1") FILTER (WHERE "clicked__1" IS NOT NULL) as "clicked__1",
    FIRST("clients__1") FILTER (WHERE "clients__1" IS NOT NULL) as "clients__1",
    FIRST("delivery_rate__1") FILTER (WHERE "delivery_rate__1" IS NOT NULL) as "delivery_rate__1",
    FIRST("open_rate__1") FILTER (WHERE "open_rate__1" IS NOT NULL) as "open_rate__1",
    FIRST("click_rate__1") FILTER (WHERE "click_rate__1" IS NOT NULL) as "click_rate__1",
    FIRST("ctor__1") FILTER (WHERE "ctor__1" IS NOT NULL) as "ctor__1",
    CASE WHEN group_set=2 THEN
      "market__2"
      END as "market__2",
    FIRST("sent__2") FILTER (WHERE "sent__2" IS NOT NULL) as "sent__2",
    FIRST("delivered__2") FILTER (WHERE "delivered__2" IS NOT NULL) as "delivered__2",
    FIRST("opened__2") FILTER (WHERE "opened__2" IS NOT NULL) as "opened__2",
    FIRST("clicked__2") FILTER (WHERE "clicked__2" IS NOT NULL) as "clicked__2",
    FIRST("clients__2") FILTER (WHERE "clients__2" IS NOT NULL) as "clients__2",
    FIRST("delivery_rate__2") FILTER (WHERE "delivery_rate__2" IS NOT NULL) as "delivery_rate__2",
    FIRST("open_rate__2") FILTER (WHERE "open_rate__2" IS NOT NULL) as "open_rate__2",
    FIRST("click_rate__2") FILTER (WHERE "click_rate__2" IS NOT NULL) as "click_rate__2",
    FIRST("ctor__2") FILTER (WHERE "ctor__2" IS NOT NULL) as "ctor__2",
    CASE WHEN group_set IN (3,4,5,6,7,8,9,10,11) THEN
      "typology__3"
      END as "typology__3",
    FIRST("sent__3") FILTER (WHERE "sent__3" IS NOT NULL) as "sent__3",
    FIRST("delivered__3") FILTER (WHERE "delivered__3" IS NOT NULL) as "delivered__3",
    FIRST("opened__3") FILTER (WHERE "opened__3" IS NOT NULL) as "opened__3",
    FIRST("clicked__3") FILTER (WHERE "clicked__3" IS NOT NULL) as "clicked__3",
    FIRST("clients__3") FILTER (WHERE "clients__3" IS NOT NULL) as "clients__3",
    FIRST("delivery_rate__3") FILTER (WHERE "delivery_rate__3" IS NOT NULL) as "delivery_rate__3",
    FIRST("open_rate__3") FILTER (WHERE "open_rate__3" IS NOT NULL) as "open_rate__3",
    FIRST("click_rate__3") FILTER (WHERE "click_rate__3" IS NOT NULL) as "click_rate__3",
    FIRST("ctor__3") FILTER (WHERE "ctor__3" IS NOT NULL) as "ctor__3",
    CASE WHEN group_set IN (4,5) THEN
      "yr__4"
      END as "yr__4",
    FIRST("sent__4") FILTER (WHERE "sent__4" IS NOT NULL) as "sent__4",
    FIRST("delivered__4") FILTER (WHERE "delivered__4" IS NOT NULL) as "delivered__4",
    FIRST("opened__4") FILTER (WHERE "opened__4" IS NOT NULL) as "opened__4",
    FIRST("clicked__4") FILTER (WHERE "clicked__4" IS NOT NULL) as "clicked__4",
    FIRST("clients__4") FILTER (WHERE "clients__4" IS NOT NULL) as "clients__4",
    FIRST("delivery_rate__4") FILTER (WHERE "delivery_rate__4" IS NOT NULL) as "delivery_rate__4",
    FIRST("open_rate__4") FILTER (WHERE "open_rate__4" IS NOT NULL) as "open_rate__4",
    FIRST("click_rate__4") FILTER (WHERE "click_rate__4" IS NOT NULL) as "click_rate__4",
    FIRST("ctor__4") FILTER (WHERE "ctor__4" IS NOT NULL) as "ctor__4",
    COALESCE(LIST({
      "market": "market__5", 
      "sent": "sent__5", 
      "delivered": "delivered__5", 
      "opened": "opened__5", 
      "clicked": "clicked__5", 
      "clients": "clients__5", 
      "delivery_rate": "delivery_rate__5", 
      "open_rate": "open_rate__5", 
      "click_rate": "click_rate__5", 
      "ctor": "ctor__5"}  ORDER BY  "sent__5" DESC NULLS LAST) FILTER (WHERE group_set=5),[]) as "by_market__4",
    CASE WHEN group_set IN (6,7,8,9,10,11) THEN
      "tier__6"
      END as "tier__6",
    FIRST("sent__6") FILTER (WHERE "sent__6" IS NOT NULL) as "sent__6",
    FIRST("delivered__6") FILTER (WHERE "delivered__6" IS NOT NULL) as "delivered__6",
    FIRST("opened__6") FILTER (WHERE "opened__6" IS NOT NULL) as "opened__6",
    FIRST("clicked__6") FILTER (WHERE "clicked__6" IS NOT NULL) as "clicked__6",
    FIRST("clients__6") FILTER (WHERE "clients__6" IS NOT NULL) as "clients__6",
    FIRST("delivery_rate__6") FILTER (WHERE "delivery_rate__6" IS NOT NULL) as "delivery_rate__6",
    FIRST("open_rate__6") FILTER (WHERE "open_rate__6" IS NOT NULL) as "open_rate__6",
    FIRST("click_rate__6") FILTER (WHERE "click_rate__6" IS NOT NULL) as "click_rate__6",
    FIRST("ctor__6") FILTER (WHERE "ctor__6" IS NOT NULL) as "ctor__6",
    COALESCE(LIST({
      "yr": "yr__7", 
      "sent": "sent__7", 
      "delivered": "delivered__7", 
      "opened": "opened__7", 
      "clicked": "clicked__7", 
      "clients": "clients__7", 
      "delivery_rate": "delivery_rate__7", 
      "open_rate": "open_rate__7", 
      "click_rate": "click_rate__7", 
      "ctor": "ctor__7", 
      "by_market": "by_market__7"}  ORDER BY  "sent__7" DESC NULLS LAST) FILTER (WHERE group_set=7),[]) as "by_year__6",
    COALESCE(LIST({
      "campaign": "campaign__9", 
      "sent": "sent__9", 
      "delivered": "delivered__9", 
      "opened": "opened__9", 
      "clicked": "clicked__9", 
      "clients": "clients__9", 
      "delivery_rate": "delivery_rate__9", 
      "open_rate": "open_rate__9", 
      "click_rate": "click_rate__9", 
      "ctor": "ctor__9", 
      "by_year": "by_year__9"}  ORDER BY  "sent__9" DESC NULLS LAST) FILTER (WHERE group_set=9),[]) as "by_campaign__6"
  FROM __stage2
  GROUP BY 1,11,21,31,41,52
)
, __stage4 AS (
  SELECT 
    CASE WHEN group_set=2 THEN 1 WHEN group_set=4 THEN 3 WHEN group_set=6 THEN 3 ELSE group_set END as group_set,
    FIRST("sent__0") FILTER (WHERE "sent__0" IS NOT NULL) as "sent__0",
    FIRST("delivered__0") FILTER (WHERE "delivered__0" IS NOT NULL) as "delivered__0",
    FIRST("opened__0") FILTER (WHERE "opened__0" IS NOT NULL) as "opened__0",
    FIRST("clicked__0") FILTER (WHERE "clicked__0" IS NOT NULL) as "clicked__0",
    FIRST("clients__0") FILTER (WHERE "clients__0" IS NOT NULL) as "clients__0",
    FIRST("delivery_rate__0") FILTER (WHERE "delivery_rate__0" IS NOT NULL) as "delivery_rate__0",
    FIRST("open_rate__0") FILTER (WHERE "open_rate__0" IS NOT NULL) as "open_rate__0",
    FIRST("click_rate__0") FILTER (WHERE "click_rate__0" IS NOT NULL) as "click_rate__0",
    FIRST("ctor__0") FILTER (WHERE "ctor__0" IS NOT NULL) as "ctor__0",
    CASE WHEN group_set IN (1,2) THEN
      "yr__1"
      END as "yr__1",
    FIRST("sent__1") FILTER (WHERE "sent__1" IS NOT NULL) as "sent__1",
    FIRST("delivered__1") FILTER (WHERE "delivered__1" IS NOT NULL) as "delivered__1",
    FIRST("opened__1") FILTER (WHERE "opened__1" IS NOT NULL) as "opened__1",
    FIRST("clicked__1") FILTER (WHERE "clicked__1" IS NOT NULL) as "clicked__1",
    FIRST("clients__1") FILTER (WHERE "clients__1" IS NOT NULL) as "clients__1",
    FIRST("delivery_rate__1") FILTER (WHERE "delivery_rate__1" IS NOT NULL) as "delivery_rate__1",
    FIRST("open_rate__1") FILTER (WHERE "open_rate__1" IS NOT NULL) as "open_rate__1",
    FIRST("click_rate__1") FILTER (WHERE "click_rate__1" IS NOT NULL) as "click_rate__1",
    FIRST("ctor__1") FILTER (WHERE "ctor__1" IS NOT NULL) as "ctor__1",
    COALESCE(LIST({
      "market": "market__2", 
      "sent": "sent__2", 
      "delivered": "delivered__2", 
      "opened": "opened__2", 
      "clicked": "clicked__2", 
      "clients": "clients__2", 
      "delivery_rate": "delivery_rate__2", 
      "open_rate": "open_rate__2", 
      "click_rate": "click_rate__2", 
      "ctor": "ctor__2"}  ORDER BY  "sent__2" DESC NULLS LAST) FILTER (WHERE group_set=2),[]) as "by_market__1",
    CASE WHEN group_set IN (3,4,5,6,7,8,9,10,11) THEN
      "typology__3"
      END as "typology__3",
    FIRST("sent__3") FILTER (WHERE "sent__3" IS NOT NULL) as "sent__3",
    FIRST("delivered__3") FILTER (WHERE "delivered__3" IS NOT NULL) as "delivered__3",
    FIRST("opened__3") FILTER (WHERE "opened__3" IS NOT NULL) as "opened__3",
    FIRST("clicked__3") FILTER (WHERE "clicked__3" IS NOT NULL) as "clicked__3",
    FIRST("clients__3") FILTER (WHERE "clients__3" IS NOT NULL) as "clients__3",
    FIRST("delivery_rate__3") FILTER (WHERE "delivery_rate__3" IS NOT NULL) as "delivery_rate__3",
    FIRST("open_rate__3") FILTER (WHERE "open_rate__3" IS NOT NULL) as "open_rate__3",
    FIRST("click_rate__3") FILTER (WHERE "click_rate__3" IS NOT NULL) as "click_rate__3",
    FIRST("ctor__3") FILTER (WHERE "ctor__3" IS NOT NULL) as "ctor__3",
    COALESCE(LIST({
      "yr": "yr__4", 
      "sent": "sent__4", 
      "delivered": "delivered__4", 
      "opened": "opened__4", 
      "clicked": "clicked__4", 
      "clients": "clients__4", 
      "delivery_rate": "delivery_rate__4", 
      "open_rate": "open_rate__4", 
      "click_rate": "click_rate__4", 
      "ctor": "ctor__4", 
      "by_market": "by_market__4"}  ORDER BY  "sent__4" DESC NULLS LAST) FILTER (WHERE group_set=4),[]) as "by_year__3",
    COALESCE(LIST({
      "tier": "tier__6", 
      "sent": "sent__6", 
      "delivered": "delivered__6", 
      "opened": "opened__6", 
      "clicked": "clicked__6", 
      "clients": "clients__6", 
      "delivery_rate": "delivery_rate__6", 
      "open_rate": "open_rate__6", 
      "click_rate": "click_rate__6", 
      "ctor": "ctor__6", 
      "by_year": "by_year__6", 
      "by_campaign": "by_campaign__6"}  ORDER BY  "sent__6" DESC NULLS LAST) FILTER (WHERE group_set=6),[]) as "by_tier__3"
  FROM __stage3
  GROUP BY 1,11,22
)
SELECT
  MAX(CASE WHEN group_set=0 THEN "sent__0" END) as "sent",
  MAX(CASE WHEN group_set=0 THEN "delivered__0" END) as "delivered",
  MAX(CASE WHEN group_set=0 THEN "opened__0" END) as "opened",
  MAX(CASE WHEN group_set=0 THEN "clicked__0" END) as "clicked",
  MAX(CASE WHEN group_set=0 THEN "clients__0" END) as "clients",
  MAX(CASE WHEN group_set=0 THEN "delivery_rate__0" END) as "delivery_rate",
  MAX(CASE WHEN group_set=0 THEN "open_rate__0" END) as "open_rate",
  MAX(CASE WHEN group_set=0 THEN "click_rate__0" END) as "click_rate",
  MAX(CASE WHEN group_set=0 THEN "ctor__0" END) as "ctor",
  COALESCE(LIST({
    "yr": "yr__1", 
    "sent": "sent__1", 
    "delivered": "delivered__1", 
    "opened": "opened__1", 
    "clicked": "clicked__1", 
    "clients": "clients__1", 
    "delivery_rate": "delivery_rate__1", 
    "open_rate": "open_rate__1", 
    "click_rate": "click_rate__1", 
    "ctor": "ctor__1", 
    "by_market": "by_market__1"}  ORDER BY  "sent__1" DESC NULLS LAST) FILTER (WHERE group_set=1),[]) as "by_year",
  COALESCE(LIST({
    "typology": "typology__3", 
    "sent": "sent__3", 
    "delivered": "delivered__3", 
    "opened": "opened__3", 
    "clicked": "clicked__3", 
    "clients": "clients__3", 
    "delivery_rate": "delivery_rate__3", 
    "open_rate": "open_rate__3", 
    "click_rate": "click_rate__3", 
    "ctor": "ctor__3", 
    "by_year": "by_year__3", 
    "by_tier": "by_tier__3"}  ORDER BY  "sent__3" DESC NULLS LAST) FILTER (WHERE group_set=3),[]) as "by_typology"
FROM __stage4

