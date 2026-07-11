-- Grain: one row per source that produced at least one structured candidate.
WITH sources AS (
  SELECT source_id, name
  FROM read_csv_auto('data/exports/sources.csv', header = true)
),
questions AS (
  SELECT * FROM read_json_auto('data/reviewed/questions.jsonl', format = 'newline_delimited')
),
candidate_counts AS (
  SELECT source_id, count(*) AS candidate_count
  FROM questions
  GROUP BY source_id
),
fetched AS (
  SELECT DISTINCT source_id
  FROM read_json_auto('data/raw_private/**/manifest.json')
)
SELECT
  sources.source_id,
  CASE sources.source_id
    WHEN 'sommo_mock_test' THEN 'Sommo'
    WHEN 'portnwine_l3_quiz' THEN 'PortnWine'
    WHEN 'wine_planetary_ja' THEN 'Wine Planetary (JA)'
    WHEN 'acewset_samples' THEN 'AceWSET samples'
    WHEN 'wset_official_specification' THEN 'WSET Specification'
    WHEN 'wset_official_sample_paper' THEN 'WSET Sample Paper'
    WHEN 'wset_official_study_blog_part3' THEN 'WSET Study Blog'
    WHEN 'wset_official_qualification' THEN 'WSET Qualification'
    ELSE sources.name
  END AS source_label,
  coalesce(candidate_counts.candidate_count, 0) AS candidate_count,
  coalesce(candidate_counts.candidate_count, 0) / (SELECT count(*) FROM questions)
    AS share_of_candidates,
  fetched.source_id IS NOT NULL AS fetched,
  0 AS reviewed_count
FROM sources
LEFT JOIN candidate_counts USING (source_id)
LEFT JOIN fetched USING (source_id)
WHERE coalesce(candidate_counts.candidate_count, 0) > 0
ORDER BY candidate_count DESC, sources.source_id;
