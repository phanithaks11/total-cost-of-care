# Build Execution Evidence — Luminos Health TCOC

Generated on 2026-10-27 03:22 UTC by running `evidence/collect_build_evidence` against the live workspace.
All values come from live queries, MLflow, the Model Serving endpoint, Lakebase and the Apps API. All source data is synthetic, and only aggregated results are included (no member- or patient-level rows).

| File | Evidence |
| --- | --- |
| `01_pipeline_run.md` | Lakeflow Spark Declarative Pipeline update history and row counts for all bronze/silver/gold datasets |
| `02_gold_and_dashboard_queries.md` | Results of the gold-layer queries that back the AI/BI dashboard |
| `03_ml_model_and_forecast.md` | Registered model versions, LightGBM vs baseline metrics, feature importances, holdout validation, forecast output |
| `04_serving_endpoint_scoring.md` | Live scoring request and response from the Model Serving endpoint |
| `05_lakebase_and_app.md` | Lakebase table row counts read by the app, and Databricks App deployment status |
| `06_ml_notebook_run_log.md` | Text log of the forecast notebook's cell outputs |

Files present: `01_pipeline_run.md`, `02_gold_and_dashboard_queries.md`, `03_ml_model_and_forecast.md`, `04_serving_endpoint_scoring.md`, `05_lakebase_and_app.md`, `06_ml_notebook_run_log.md`
