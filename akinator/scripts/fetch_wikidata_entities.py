"""Fetch ~200 real notable people + ~200 fictional/anime characters from
Wikidata via SPARQL, writing one raw JSON list to data/raw/.

Polite usage: explicit User-Agent, sleep between the two queries, LIMIT caps.
On failure, leaves any existing cache untouched."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402

WDQS = "https://query.wikidata.org/sparql"
USER_AGENT = "akinator-mvp/0.1 (local hobby project; https://github.com/ankimo1210)"

# Bound the candidate scan to humans holding one of the occupations we actually
# map (P106 index), then take the top-N by sitelinks in a subquery so the heavy
# OPTIONAL joins + GROUP_CONCAT only run over those N rows. A full
# "all humans by sitelinks" scan 504s on the public endpoint; this is both
# cheaper and guarantees every fetched person has a question-relevant occupation.
_SEED_OCCUPATIONS = (
    "wd:Q169470 wd:Q33999 wd:Q177220 wd:Q82955 wd:Q36180 "
    "wd:Q937857 wd:Q639669 wd:Q1028181 wd:Q170790 wd:Q2526255"
)

REAL_PEOPLE_QUERY = """
SELECT ?item ?sl ?itemLabel ?itemLabelEn ?desc ?img ?gender ?birth ?death
       (GROUP_CONCAT(DISTINCT ?occ; separator="|") AS ?occs)
       (GROUP_CONCAT(DISTINCT ?cit; separator="|") AS ?cits)
WHERE {
  {
    SELECT ?item (MAX(?s) AS ?sl) WHERE {
      VALUES ?seedocc { %s }
      ?item wdt:P106 ?seedocc ;
            wdt:P31 wd:Q5 ;
            wikibase:sitelinks ?s .
      FILTER(?s > 50)
    }
    GROUP BY ?item
    ORDER BY DESC(?sl)
    LIMIT 200
  }
  OPTIONAL { ?item wdt:P21 ?gender. }
  OPTIONAL { ?item wdt:P106 ?occ. }
  OPTIONAL { ?item wdt:P27 ?cit. }
  OPTIONAL { ?item wdt:P569 ?birth. }
  OPTIONAL { ?item wdt:P570 ?death. }
  OPTIONAL { ?item wdt:P18 ?img. }
  OPTIONAL { ?item schema:description ?desc. FILTER(LANG(?desc)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel. FILTER(LANG(?itemLabel)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabelEn. FILTER(LANG(?itemLabelEn)="en") }
}
GROUP BY ?item ?sl ?itemLabel ?itemLabelEn ?desc ?img ?gender ?birth ?death
ORDER BY DESC(?sl)
""" % _SEED_OCCUPATIONS

FICTIONAL_QUERY = """
SELECT ?item ?sl ?itemLabel ?itemLabelEn ?desc ?img ?gender
       (GROUP_CONCAT(DISTINCT ?inst; separator="|") AS ?insts)
WHERE {
  {
    SELECT ?item ?sl WHERE {
      ?item wdt:P31 ?anyinst .
      VALUES ?anyinst { wd:Q15632617 wd:Q95074 }   # fictional human / fictional character
      ?item wikibase:sitelinks ?sl .
      FILTER(?sl > 30)
    }
    ORDER BY DESC(?sl)
    LIMIT 200
  }
  ?item wdt:P31 ?inst .
  VALUES ?inst { wd:Q15632617 wd:Q95074 }
  OPTIONAL { ?item wdt:P21 ?gender. }
  OPTIONAL { ?item wdt:P18 ?img. }
  OPTIONAL { ?item schema:description ?desc. FILTER(LANG(?desc)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel. FILTER(LANG(?itemLabel)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabelEn. FILTER(LANG(?itemLabelEn)="en") }
}
GROUP BY ?item ?sl ?itemLabel ?itemLabelEn ?desc ?img ?gender
ORDER BY DESC(?sl)
"""


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _year(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        # handles leading '-' for BCE and 'T...' suffix
        head = iso.split("T")[0]
        sign = -1 if head.startswith("-") else 1
        return sign * int(head.lstrip("-").split("-")[0])
    except (ValueError, IndexError):
        return None


_RETRYABLE = {429, 500, 502, 503, 504}


def _run_query(client: httpx.Client, query: str, *, attempts: int = 5) -> list[dict]:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            resp = client.get(
                WDQS, params={"query": query, "format": "json"},
                headers={"User-Agent": USER_AGENT,
                         "Accept": "application/sparql-results+json"},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["results"]["bindings"]
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            retryable = isinstance(e, httpx.TransportError) or status in _RETRYABLE
            if retryable and i < attempts - 1:
                # WDQS rate-limits to ~1 req/min during outages; wait it out.
                wait = 70 if status == 429 else 30
                print(f"  WDQS {status or type(e).__name__}; retrying in {wait}s "
                      f"({i + 1}/{attempts})", flush=True)
                time.sleep(wait)
                last_exc = e
                continue
            raise
    assert last_exc is not None
    raise last_exc


def _v(row: dict, key: str) -> str | None:
    cell = row.get(key)
    return cell["value"] if cell else None


def _split(row: dict, key: str) -> list[str]:
    raw = _v(row, key)
    return [p for p in raw.split("|") if p] if raw else []


def fetch() -> list[dict]:
    out: list[dict] = []
    with httpx.Client() as client:
        for row in _run_query(client, REAL_PEOPLE_QUERY):
            out.append({
                "id": _qid(_v(row, "item")),
                "name_ja": _v(row, "itemLabel"),
                "name_en": _v(row, "itemLabelEn"),
                "aliases": [],
                "description": _v(row, "desc"),
                "image_url": _v(row, "img"),
                "instance_of": ["Q5"],
                "gender": _qid(_v(row, "gender")) if _v(row, "gender") else None,
                "occupations": [_qid(u) for u in _split(row, "occs")],
                "countries": [_qid(u) for u in _split(row, "cits")],
                "birth_year": _year(_v(row, "birth")),
                "death_year": _year(_v(row, "death")),
                "in_anime": False,
            })
        # Space the second query out — the public endpoint rate-limits to
        # ~1 req/min when it is under load.
        time.sleep(65)
        for row in _run_query(client, FICTIONAL_QUERY):
            out.append({
                "id": _qid(_v(row, "item")),
                "name_ja": _v(row, "itemLabel"),
                "name_en": _v(row, "itemLabelEn"),
                "aliases": [],
                "description": _v(row, "desc"),
                "image_url": _v(row, "img"),
                "instance_of": [_qid(u) for u in _split(row, "insts")],
                "gender": _qid(_v(row, "gender")) if _v(row, "gender") else None,
                "occupations": [],
                "countries": [],
                "birth_year": None,
                "death_year": None,
                "in_anime": True,
            })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-fetch even if cache exists")
    args = parser.parse_args()
    out_path = config.RAW_DIR / "wikidata_entities.json"
    if out_path.exists() and not args.refresh:
        print(f"cache exists at {out_path}; use --refresh to re-fetch")
        return
    data = fetch()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"fetched {len(data)} raw entities -> {out_path}")


if __name__ == "__main__":
    main()
