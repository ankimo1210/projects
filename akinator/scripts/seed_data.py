"""Offline seed dataset — a fallback for when the live Wikidata SPARQL endpoint
(WDQS) is unavailable.

This is NOT the canonical dataset. The design sources ~400 entities live from
Wikidata; this is a small, hand-curated set of well-known people/characters with
verifiable attributes, run through the SAME normalize + question-generation
pipeline as the real fetch. It exists so the app is playable out of the box and
so the engine can be exercised end-to-end while WDQS is down.

Regenerate the real dataset (overwrites this) once WDQS is healthy:
    uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py --refresh
    uv run --no-sync python akinator/scripts/build_questions.py

Entities use descriptive `seed_*` ids (not Wikidata QIDs) to be honest about
provenance; images are omitted. Attribute QIDs (gender/occupation/country/
instance_of) reuse the same maps as normalize.py so the pipeline maps them to
question-ready feature values.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.build import build_from_raw  # noqa: E402

MALE = "Q6581097"
FEMALE = "Q6581072"
HUMAN = ["Q5"]
FICTIONAL = ["Q15632617"]  # fictional human

# occupation QIDs (mapped in normalize.py)
PHYSICIST, ACTOR, SINGER, POLITICIAN = "Q169470", "Q33999", "Q177220", "Q82955"
WRITER, ATHLETE, MUSICIAN, PAINTER = "Q36180", "Q937857", "Q639669", "Q1028181"
MATHEMATICIAN, DIRECTOR = "Q170790", "Q2526255"
# country QIDs (mapped in normalize.py)
JP, DE, US, UK, FR, IT, RU = "Q17", "Q183", "Q30", "Q145", "Q142", "Q38", "Q159"


def _p(sid, ja, en, occs, countries, gender, birth, death, instance=HUMAN, anime=False):
    return {
        "id": sid, "name_ja": ja, "name_en": en, "aliases": [],
        "description": en, "image_url": None, "instance_of": instance,
        "gender": gender, "occupations": occs, "countries": countries,
        "birth_year": birth, "death_year": death, "in_anime": anime,
    }


def _fic(sid, ja, en, gender, anime=True):
    return {
        "id": sid, "name_ja": ja, "name_en": en, "aliases": [],
        "description": en, "image_url": None, "instance_of": FICTIONAL,
        "gender": gender, "occupations": [], "countries": [],
        "birth_year": None, "death_year": None, "in_anime": anime,
    }


SEED = [
    # --- real people ---
    _p("seed_einstein", "アルベルト・アインシュタイン", "Albert Einstein",
       [PHYSICIST, MATHEMATICIAN], [DE, US], MALE, 1879, 1955),
    _p("seed_newton", "アイザック・ニュートン", "Isaac Newton",
       [PHYSICIST, MATHEMATICIAN], [UK], MALE, 1643, 1727),
    _p("seed_curie", "マリ・キュリー", "Marie Curie",
       [PHYSICIST], [FR], FEMALE, 1867, 1934),
    _p("seed_beethoven", "ベートーヴェン", "Ludwig van Beethoven",
       [MUSICIAN], [DE], MALE, 1770, 1827),
    _p("seed_bach", "バッハ", "Johann Sebastian Bach",
       [MUSICIAN], [DE], MALE, 1685, 1750),
    _p("seed_monet", "クロード・モネ", "Claude Monet",
       [PAINTER], [FR], MALE, 1840, 1926),
    _p("seed_picasso", "パブロ・ピカソ", "Pablo Picasso",
       [PAINTER], [FR], MALE, 1881, 1973),
    _p("seed_shakespeare", "シェイクスピア", "William Shakespeare",
       [WRITER], [UK], MALE, 1564, 1616),
    _p("seed_dickens", "チャールズ・ディケンズ", "Charles Dickens",
       [WRITER], [UK], MALE, 1812, 1870),
    _p("seed_tolstoy", "トルストイ", "Leo Tolstoy",
       [WRITER], [RU], MALE, 1828, 1910),
    _p("seed_dostoevsky", "ドストエフスキー", "Fyodor Dostoevsky",
       [WRITER], [RU], MALE, 1821, 1881),
    _p("seed_davinci", "レオナルド・ダ・ヴィンチ", "Leonardo da Vinci",
       [PAINTER], [IT], MALE, 1452, 1519),
    _p("seed_lincoln", "リンカーン", "Abraham Lincoln",
       [POLITICIAN], [US], MALE, 1809, 1865),
    _p("seed_washington", "ジョージ・ワシントン", "George Washington",
       [POLITICIAN], [US], MALE, 1732, 1799),
    _p("seed_churchill", "チャーチル", "Winston Churchill",
       [POLITICIAN, WRITER], [UK], MALE, 1874, 1965),
    _p("seed_napoleon", "ナポレオン", "Napoleon Bonaparte",
       [POLITICIAN], [FR], MALE, 1769, 1821),
    _p("seed_obama", "バラク・オバマ", "Barack Obama",
       [POLITICIAN], [US], MALE, 1961, None),
    _p("seed_merkel", "アンゲラ・メルケル", "Angela Merkel",
       [POLITICIAN], [DE], FEMALE, 1954, None),
    _p("seed_tomhanks", "トム・ハンクス", "Tom Hanks",
       [ACTOR], [US], MALE, 1956, None),
    _p("seed_hepburn", "オードリー・ヘプバーン", "Audrey Hepburn",
       [ACTOR], [UK], FEMALE, 1929, 1993),
    _p("seed_mjackson", "マイケル・ジャクソン", "Michael Jackson",
       [SINGER, MUSICIAN], [US], MALE, 1958, 2009),
    _p("seed_madonna", "マドンナ", "Madonna",
       [SINGER], [US], FEMALE, 1958, None),
    _p("seed_miyazaki", "宮崎駿", "Hayao Miyazaki",
       [DIRECTOR], [JP], MALE, 1941, None),
    _p("seed_kurosawa", "黒澤明", "Akira Kurosawa",
       [DIRECTOR], [JP], MALE, 1910, 1998),
    _p("seed_messi", "リオネル・メッシ", "Lionel Messi",
       [ATHLETE], [], MALE, 1987, None),
    # --- fictional characters ---
    _fic("seed_goku", "孫悟空", "Son Goku", MALE),
    _fic("seed_naruto", "うずまきナルト", "Naruto Uzumaki", MALE),
    _fic("seed_luffy", "モンキー・D・ルフィ", "Monkey D. Luffy", MALE),
    _fic("seed_usagi", "セーラームーン", "Sailor Moon", FEMALE),
    _fic("seed_doraemon", "ドラえもん", "Doraemon", None),
    _fic("seed_pikachu", "ピカチュウ", "Pikachu", None),
    _fic("seed_mickey", "ミッキーマウス", "Mickey Mouse", MALE, anime=False),
    _fic("seed_harrypotter", "ハリー・ポッター", "Harry Potter", MALE, anime=False),
    _fic("seed_holmes", "シャーロック・ホームズ", "Sherlock Holmes", MALE, anime=False),
    _fic("seed_superman", "スーパーマン", "Superman", MALE, anime=False),
]


def main() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = config.RAW_DIR / "seed_entities.json"
    import json
    raw_path.write_text(json.dumps(SEED, ensure_ascii=False, indent=2), encoding="utf-8")
    n_ent, n_q = build_from_raw(raw_path, config.ENTITIES_PATH, config.QUESTIONS_PATH)
    print(f"seed: wrote {n_ent} entities, {n_q} questions")


if __name__ == "__main__":
    main()
