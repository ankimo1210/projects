# akinator

Local Akinator-style guesser. Entities are sourced from Wikidata (no hand-built
dataset); the engine is a probabilistic candidate updater, not a fixed tree.

## Run

```bash
cd ~/projects && make install            # once, installs workspace .venv
# (re)build data from Wikidata — optional, processed/ is committed:
uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py
uv run --no-sync python akinator/scripts/build_questions.py
# serve
uv run --no-sync uvicorn app.main:app --app-dir akinator --reload --port 8100
# tests
uv run --no-sync pytest akinator/tests -v
```

Open http://localhost:8100/ to play. `/debug/{game_id}` shows engine internals.
