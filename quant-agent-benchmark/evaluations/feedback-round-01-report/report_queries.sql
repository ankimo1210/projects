SELECT model, phase, json_extract(document,'$.total_score') AS score,
 json_extract(document,'$.category_scores') AS categories,
 json_extract(document,'$.quantitative_diagnostics') AS metrics,
 json_array_length(json_extract(document,'$.hidden_tests.passed')) AS checks_passed,
 json_extract(document,'$.failed_test_identifiers') AS failed_checks
FROM main.evaluations ORDER BY model, phase;

SELECT model, phase, json_extract(document,'$.work_minutes') AS minutes,
 json_extract(document,'$.total_tokens') AS tokens,
 json_extract(document,'$.uncached_input') AS uncached_input,
 json_extract(document,'$.cache_read_input') AS cache_read_input,
 json_extract(document,'$.cache_write_5m') AS cache_write_5m,
 json_extract(document,'$.cache_write_1h') AS cache_write_1h,
 json_extract(document,'$.output_total') AS output_tokens,
 json_extract(document,'$.usd_standard') AS usd_standard,
 json_extract(document,'$.usd_fast_scenario') AS usd_fast_scenario
FROM main.usage ORDER BY model, phase;
