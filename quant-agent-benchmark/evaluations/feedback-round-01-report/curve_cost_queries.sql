SELECT g.dataset, g.case_id, round(g.years,9) AS years, v.model,
 round(100*linear_interp(g.years,v.maturities,v.zero_rates),6) AS zero_percent,
 round(100*linear_interp(g.years,v.maturities,v.forward_rates),6) AS forward_percent
FROM main.display_grid AS g JOIN main.curve_vectors AS v ON v.case_id=g.case_id
ORDER BY g.dataset,g.years,v.model;

SELECT model, split, instrument_type, count(*) AS instruments,
 sqrt(avg(error*error)) AS rmse FROM main.pricing_errors
GROUP BY model,split,instrument_type ORDER BY model,split,instrument_type;

SELECT model, representation, selection, experiment, adopted, remaining FROM main.approach_records ORDER BY model;

SELECT json_extract(summary,'$.model') AS model,
 json_extract(usage,'$.initial.usd_standard')+json_extract(usage,'$.feedback_all.usd_standard') AS cost,
 json_extract(usage,'$.initial.work_minutes')+json_extract(usage,'$.feedback_all.work_minutes') AS minutes,
 json_extract(summary,'$.zero_final') AS main_bp,
 json_extract(summary,'$.scenario_zero_final') AS test_bp,
 json_extract(summary,'$.scenario_forward_final') AS forward_bp,
 json_extract(summary,'$.additional_usd') AS extra_cost,
 json_extract(summary,'$.zero_initial')-json_extract(summary,'$.zero_final') AS gain_bp,
 (json_extract(summary,'$.zero_initial')-json_extract(summary,'$.zero_final'))/json_extract(summary,'$.additional_usd') AS gain_per_dollar,
 10 AS scenarios,
 json_extract(usage,'$.initial.total_tokens')+json_extract(usage,'$.feedback_all.total_tokens') AS tokens
FROM main.cost_inputs;
