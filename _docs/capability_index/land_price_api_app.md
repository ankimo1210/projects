# Land Price API App Capability Index

## Run Local App

Relevant files:
- `land_price_api_app/app.py`
- `land_price_api_app/run_local.sh`
- `land_price_api_app/config.py`

Do not inspect:
- `_data/`
- parquet files
- duckdb files
- geojson files
- logs

Validation:
- run the local app only if requested
- otherwise run import checks or targeted tests

## Sync Public Notice Land Prices

Relevant files:
- `land_price_api_app/sync_public_notice.py`
- `land_price_api_app/api_client.py`
- `land_price_api_app/normalize.py`
- `land_price_api_app/db.py`
- `land_price_api_app/config.py`

Validation:
- do not run full backfill unless explicitly requested
- run targeted smoke checks only

## Trade Price Sync

Relevant files:
- `land_price_api_app/sync_trade_prices.py`
- `land_price_api_app/geocode_trade_prices.py`
- `land_price_api_app/db.py`
- `land_price_api_app/config.py`

## Property Scraper

Relevant files:
- `land_price_api_app/property_scraper.py`
- `land_price_api_app/collect_search_results.py`
- `land_price_api_app/collect_listings_batch.py`
- `land_price_api_app/tests/test_property_scraper.py`
- `land_price_api_app/tests/fixtures/`

Validation:
- `pytest land_price_api_app/tests/test_property_scraper.py -q`
