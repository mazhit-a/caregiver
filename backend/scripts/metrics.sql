-- Funnel and activation metrics for the pitch. Plain Postgres, read-only; run with
--   psql "$DATABASE_URL" -f backend/scripts/metrics.sql
-- Each query starts with a `-- name: <id>` line (tests/scripts/test_metrics_sql.py runs them all).
-- Event rows carry app time (`app_at`); "sessions" means distinct anonymous sessions.
-- Funnel steps from the browser come from `events` (landing_view, quiz_start, quiz_complete,
-- plan_preview_view, paywall_view); "subscribe" is read from the subscription history (the
-- server's own record), not from a client event. Dates are UTC dates of app time.

-- name: funnel
WITH steps(step_no, step) AS (
    VALUES (1, 'landing_view'), (2, 'quiz_start'), (3, 'quiz_complete'),
           (4, 'plan_preview_view'), (5, 'paywall_view')
),
counts AS (
    SELECT s.step_no, s.step, count(DISTINCT e.session_id) AS sessions
    FROM steps s
    LEFT JOIN events e ON e.name = s.step
    GROUP BY s.step_no, s.step
    UNION ALL
    SELECT 6, 'subscribe', count(DISTINCT session_id)
    FROM subscription_history
    WHERE from_status = 'none' AND to_status IN ('demo', 'active')
)
SELECT step_no, step, sessions,
       round(100.0 * sessions / NULLIF(first_value(sessions) OVER (ORDER BY step_no), 0), 1)
           AS pct_of_landing,
       round(100.0 * sessions / NULLIF(lag(sessions) OVER (ORDER BY step_no), 0), 1)
           AS pct_of_previous_step
FROM counts
ORDER BY step_no;

-- name: d0_lesson_start
-- Share of subscribers who started lesson 1 on the app day they subscribed.
WITH subscribed AS (
    SELECT session_id, min(at)::date AS day0
    FROM subscription_history
    WHERE from_status = 'none' AND to_status IN ('demo', 'active')
    GROUP BY session_id
),
first_lesson AS (
    SELECT l.session_id, lp.started_at::date AS started_day
    FROM lesson_schedule l
    JOIN lesson_progress lp USING (session_id, lesson_id)
    WHERE l.seq = 0
)
SELECT count(*) AS subscribers,
       count(f.session_id) FILTER (WHERE f.started_day = s.day0) AS started_lesson_1_on_day_0,
       round(100.0 * count(f.session_id) FILTER (WHERE f.started_day = s.day0)
             / NULLIF(count(*), 0), 1) AS pct
FROM subscribed s
LEFT JOIN first_lesson f USING (session_id);

-- name: first_roleplay_completed
-- Share of subscribers with at least one finished role-play run (no reply text is stored).
WITH subscribed AS (
    SELECT DISTINCT session_id FROM subscription_history
    WHERE from_status = 'none' AND to_status IN ('demo', 'active')
),
finished AS (
    SELECT DISTINCT session_id FROM roleplay_runs WHERE finished_at IS NOT NULL
)
SELECT count(*) AS subscribers,
       count(f.session_id) AS finished_a_roleplay,
       round(100.0 * count(f.session_id) / NULLIF(count(*), 0), 1) AS pct
FROM subscribed s
LEFT JOIN finished f USING (session_id);

-- name: lesson_1_to_2_start
-- Of the sessions that started the first lesson, how many started the second one.
WITH started AS (
    SELECT l.session_id, l.seq
    FROM lesson_schedule l
    JOIN lesson_progress lp USING (session_id, lesson_id)
    WHERE l.seq IN (0, 1)
)
SELECT count(DISTINCT session_id) FILTER (WHERE seq = 0) AS started_lesson_1,
       count(DISTINCT session_id) FILTER (WHERE seq = 1) AS started_lesson_2,
       round(100.0 * count(DISTINCT session_id) FILTER (WHERE seq = 1)
             / NULLIF(count(DISTINCT session_id) FILTER (WHERE seq = 0), 0), 1) AS pct
FROM started;

-- name: active_days_week_1
-- Distribution of distinct active app days in the first 7 days after subscribing (day 0 to 6).
WITH subscribed AS (
    SELECT session_id, min(at)::date AS day0
    FROM subscription_history
    WHERE from_status = 'none' AND to_status IN ('demo', 'active')
    GROUP BY session_id
),
per_session AS (
    SELECT s.session_id, count(a.day) AS active_days
    FROM subscribed s
    LEFT JOIN active_days a
           ON a.session_id = s.session_id AND a.day >= s.day0 AND a.day < s.day0 + 7
    GROUP BY s.session_id
)
SELECT active_days, count(*) AS sessions
FROM per_session
GROUP BY active_days
ORDER BY active_days;
