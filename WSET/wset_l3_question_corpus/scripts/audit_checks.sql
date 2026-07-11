-- Grain: one row per stable quality rule. Severity describes app-readiness impact.
WITH
questions AS (
  SELECT * FROM read_json_auto('data/reviewed/questions.jsonl', format = 'newline_delimited')
),
public_safe AS (
  SELECT * FROM read_json_auto('data/exports/questions_public_safe.jsonl', format = 'newline_delimited')
),
summary AS (
  SELECT
    count(*) AS total_rows,
    count(DISTINCT question_id) AS unique_ids,
    count(*) FILTER (
      WHERE question_id IS NULL OR source_id IS NULL OR source_url IS NULL
         OR language IS NULL OR normalized_text IS NULL OR extraction_confidence IS NULL
    ) AS missing_required,
    count(*) FILTER (WHERE human_review_status = 'fact_check_required') AS pdf_damage,
    count(*) FILTER (WHERE human_review_status = 'rejected') AS rejected,
    count(*) FILTER (WHERE human_review_status = 'human_reviewed') AS human_reviewed,
    count(*) FILTER (WHERE language = 'ja') AS japanese_rows
  FROM questions
),
leaks AS (
  SELECT count(*) AS leaking_rows
  FROM public_safe
  WHERE raw_text IS NOT NULL OR normalized_text IS NOT NULL OR answer_text IS NOT NULL
)
SELECT 'Required lineage fields' AS check_name,
       missing_required || ' missing required values' AS evidence,
       CASE WHEN missing_required = 0 THEN 'pass' ELSE 'critical' END AS severity,
       'high' AS confidence FROM summary
UNION ALL
SELECT 'Stable ID uniqueness', unique_ids || '/' || total_rows || ' unique',
       CASE WHEN unique_ids = total_rows THEN 'pass' ELSE 'critical' END, 'high' FROM summary
UNION ALL
SELECT 'Public-safe text leakage', leaking_rows || ' leaking rows',
       CASE WHEN leaking_rows = 0 THEN 'pass' ELSE 'critical' END, 'high' FROM leaks
UNION ALL
SELECT 'PDF extraction damage', pdf_damage || ' character-spacing-damaged candidates',
       'high', 'high' FROM summary
UNION ALL
SELECT 'False positives / fragments', rejected || ' candidates rejected by screening',
       'medium', 'medium' FROM summary
UNION ALL
SELECT 'Japanese coverage', japanese_rows || ' safely ingested Japanese candidates',
       CASE WHEN japanese_rows = 0 THEN 'high' ELSE 'pass' END, 'high' FROM summary
UNION ALL
SELECT 'Human review coverage', human_reviewed || '/' || total_rows || ' human-reviewed',
       CASE WHEN human_reviewed = 0 THEN 'high' ELSE 'medium' END, 'high' FROM summary;
