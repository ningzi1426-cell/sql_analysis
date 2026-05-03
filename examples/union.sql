SELECT
    1 AS id
UNION
ALL
SELECT
    2 AS id
FROM
    dual
UNION
ALL
SELECT
    a.id
FROM
    user1 a
UNION
ALL
SELECT
    b.id
FROM
    user1 b