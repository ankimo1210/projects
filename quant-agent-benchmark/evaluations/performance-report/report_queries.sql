-- scores
SELECT e.model, json_extract(e.document, '$.total_score') AS score,
       c.key AS category, CAST(c.value AS REAL) AS category_score,
       CASE c.key WHEN 'numerical_correctness' THEN 30
         WHEN 'quantitative_model_quality' THEN 20
         WHEN 'hidden_scenario_robustness' THEN 15
         WHEN 'software_engineering_reproducibility' THEN 15
         WHEN 'data_quality_handling' THEN 10 ELSE 5 END AS category_maximum,
       CAST(c.value AS REAL) / CASE c.key WHEN 'numerical_correctness' THEN 30
         WHEN 'quantitative_model_quality' THEN 20
         WHEN 'hidden_scenario_robustness' THEN 15
         WHEN 'software_engineering_reproducibility' THEN 15
         WHEN 'data_quality_handling' THEN 10 ELSE 5 END AS attainment
FROM main.raw_evaluations e, json_each(e.document, '$.category_scores') c
ORDER BY score DESC, category;

-- precision
WITH diagnostic_rows AS (
  SELECT model, 'main' AS scope, json_extract(document, '$.quantitative_diagnostics') AS metrics
  FROM main.raw_evaluations
  UNION ALL
  SELECT e.model, s.key, s.value
  FROM main.raw_evaluations e, json_each(e.document, '$.quantitative_diagnostics.hidden_scenarios') s
)
SELECT model, scope, metrics,
       json_extract(metrics, '$.zero_rate_rmse_bps') AS zero_rmse_bps,
       json_extract(metrics, '$.forward_rate_rmse_bps') AS forward_rmse_bps,
       100.0 * json_extract(metrics, '$.dv01_median_relative_error') AS dv01_relative_error_percent,
       RANK() OVER (PARTITION BY scope ORDER BY json_extract(metrics, '$.zero_rate_rmse_bps')) AS zero_error_rank
FROM diagnostic_rows ORDER BY scope, zero_error_rank;

-- usage
SELECT model,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(minutes AS REAL) ELSE 0 END) AS work_minutes,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(api_responses AS INTEGER) ELSE 0 END) AS work_api_responses,
 SUM(CAST(api_responses AS INTEGER)) AS session_api_responses,
 SUM(CAST(total_tokens AS INTEGER)) AS session_total_tokens,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) ELSE 0 END) AS uncached_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(cache_read_input AS INTEGER) ELSE 0 END) AS cache_read_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(cache_creation_input AS INTEGER) ELSE 0 END) AS cache_creation_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) + CAST(cache_read_input AS INTEGER) + CAST(cache_creation_input AS INTEGER) ELSE 0 END) AS input_total,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_nonreasoning AS INTEGER) ELSE 0 END) AS output_nonreasoning,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_reasoning AS INTEGER) ELSE 0 END) AS output_reasoning,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_nonreasoning AS INTEGER) + CAST(output_reasoning AS INTEGER) ELSE 0 END) AS output_total,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) + CAST(cache_read_input AS INTEGER) + CAST(cache_creation_input AS INTEGER) + CAST(output_nonreasoning AS INTEGER) + CAST(output_reasoning AS INTEGER) ELSE 0 END) AS total_tokens,
 1.0 * SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_total AS INTEGER) ELSE 0 END) /
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(api_responses AS INTEGER) ELSE 0 END) AS output_per_api
FROM main.raw_user_turns GROUP BY model ORDER BY total_tokens;

-- qa
WITH pytest_counts AS (
 SELECT p.model, CAST(trim(substr(json_extract(p.document, '$.stdout'),
   instr(json_extract(p.document, '$.stdout'), ' passed') - 3, 3)) AS INTEGER) AS pytest_passed,
   json_extract(p.document, '$.returncode') AS pytest_exit_code
 FROM main.raw_pytest p
)
SELECT e.model, p.pytest_passed, p.pytest_exit_code,
 SUM(CASE WHEN json_extract(c.value, '$.passed') = 1 THEN 1 ELSE 0 END) AS hidden_passed,
 COUNT(*) AS hidden_checks,
 (SELECT COUNT(*) FROM json_each(e.document, '$.quantitative_diagnostics.hidden_scenarios') s WHERE json_extract(s.value, '$.valid') = 1) AS valid_scenarios
FROM main.raw_evaluations e JOIN pytest_counts p ON p.model = e.model,
 json_each(e.document, '$.hidden_tests.details') c
GROUP BY e.model ORDER BY e.model;
