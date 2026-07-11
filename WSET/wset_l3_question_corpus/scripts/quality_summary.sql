-- Grain: one report snapshot. Inputs are local private/reviewed/export artifacts.
WITH
sources AS (
  SELECT * FROM read_csv_auto('data/exports/sources.csv', header = true)
),
fetched AS (
  SELECT * FROM read_json_auto('data/raw_private/**/manifest.json')
),
questions AS (
  SELECT * FROM read_json_auto('data/reviewed/questions.jsonl', format = 'newline_delimited')
),
public_safe AS (
  SELECT * FROM read_json_auto('data/exports/questions_public_safe.jsonl', format = 'newline_delimited')
),
patterns AS (
  SELECT * FROM read_json_auto('data/reviewed/question_patterns.jsonl', format = 'newline_delimited')
),
duplicates AS (
  SELECT * FROM read_csv_auto('data/exports/duplicate_clusters.csv', header = true)
)
SELECT
  (SELECT count(*) FROM sources) AS registered_sources,
  (SELECT count(DISTINCT source_id) FROM fetched) AS fetched_sources,
  (SELECT count(*) FROM questions) AS candidate_questions,
  (SELECT count(*) FROM questions WHERE human_review_status = 'machine_screened') AS machine_screened,
  (SELECT count(*) FROM questions WHERE human_review_status = 'fact_check_required') AS fact_check_required,
  (SELECT count(*) FROM questions WHERE human_review_status = 'rejected') AS rejected,
  (SELECT count(*) FROM questions WHERE human_review_status = 'human_reviewed') AS human_reviewed,
  (SELECT count(*) FROM questions WHERE language = 'ja') AS japanese_candidates,
  (SELECT count(*) FROM questions WHERE language = 'en') AS english_candidates,
  (SELECT count(*) FROM questions WHERE answer_text IS NOT NULL) AS answered_candidates,
  (
    SELECT count(*) FROM public_safe
    WHERE raw_text IS NOT NULL OR normalized_text IS NOT NULL OR answer_text IS NOT NULL
  ) AS public_safe_text_leaks,
  (SELECT count(*) FROM patterns) AS original_patterns,
  (SELECT count(*) FROM duplicates) AS duplicate_member_rows;
