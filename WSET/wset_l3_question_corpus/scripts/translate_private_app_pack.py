from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.build_private_app_pack import (
    DEFAULT_OUTPUT,
    TRANSLATION_CACHE,
    build_pack,
    question_fingerprint,
    translatable_content,
)
from wset_corpus.utils import ROOT, read_jsonl

DEFAULT_MODEL = "translategemma:12b"
DEFAULT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
GLOSSARY_PATH = ROOT / "data" / "translation_glossary.json"
DIRECT_MARKER = re.compile(r"⟦(\d{4})⟧")
QUESTION_OPENING = re.compile(
    r"^(?:give|describe|explain|state|identify|list|name|compare|outline|"
    r"what|which|how|why|where|when|is|are|can|does|do|would|should)\b",
    re.I,
)
ENGLISH_TO_JAPANESE_REQUIREMENTS: tuple[tuple[re.Pattern[str], re.Pattern[str]], ...] = (
    (re.compile(r"\bacidic\b|\bacidity\b", re.I), re.compile(r"酸味")),
    (re.compile(r"\btannic\b|\btannins?\b", re.I), re.compile(r"タンニン")),
    (re.compile(r"\bdry\b|\bdrier\b", re.I), re.compile(r"辛口|乾燥")),
    (re.compile(r"\boff-dry\b", re.I), re.compile(r"やや辛口")),
    (re.compile(r"\bmedium-dry\b", re.I), re.compile(r"中辛口")),
    (re.compile(r"\bmedium-sweet\b", re.I), re.compile(r"中甘口")),
    (re.compile(r"\bstill wines?\b", re.I), re.compile(r"スティルワイン")),
    (re.compile(r"\bsparkling wines?\b", re.I), re.compile(r"スパークリングワイン")),
    (re.compile(r"\bfortified wines?\b", re.I), re.compile(r"酒精強化ワイン")),
    (re.compile(r"\bresidual sugar\b", re.I), re.compile(r"残糖")),
    (re.compile(r"\bfermentation\b", re.I), re.compile(r"発酵")),
    (re.compile(r"\bmalolactic conversion\b", re.I), re.compile(r"マロラクティック変換")),
    (re.compile(r"\bsediment\b", re.I), re.compile(r"澱")),
    (re.compile(r"\bdecant(?:ed|ing)?\b", re.I), re.compile(r"デキャンタージュ")),
    (re.compile(r"\btraditional method\b", re.I), re.compile(r"トラディショナル方式")),
    (re.compile(r"\briddling\b|\bremuage\b", re.I), re.compile(r"動瓶")),
    (re.compile(r"\bnoble rot\b|\bbotrytis\b", re.I), re.compile(r"貴腐")),
    (
        re.compile(r"\bappellations?\b", re.I),
        re.compile(r"アペラシオン|原産地呼称|AOC"),
    ),
    (re.compile(r"\bwarm\b", re.I), re.compile(r"温|暖")),
    (re.compile(r"\bcold\b", re.I), re.compile(r"冷")),
    (re.compile(r"\bsweet(?:er|ness)?\b", re.I), re.compile(r"甘")),
    (re.compile(r"\bbitter(?:ness)?\b", re.I), re.compile(r"苦")),
    (
        re.compile(r"\bfruit(?:y|iness)?\b", re.I),
        re.compile(r"果実|果物|ブドウ|フルーツ|フルーティ"),
    ),
    (re.compile(r"\balcohol\b", re.I), re.compile(r"アルコール")),
    (re.compile(r"\bbody\b", re.I), re.compile(r"ボディ|コク")),
    (re.compile(r"\bpneumatic press\b", re.I), re.compile(r"ニューマティックプレス")),
    (
        re.compile(r"\bsemi-carbonic maceration\b", re.I),
        re.compile(r"半炭酸ガス浸漬法"),
    ),
    (re.compile(r"\bcarbonic maceration\b", re.I), re.compile(r"炭酸ガス浸漬法")),
)
JAPANESE_TO_ENGLISH_REQUIREMENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("酸味", re.compile(r"acid", re.I)),
    ("タンニン", re.compile(r"tanni(?:n|c)", re.I)),
    ("辛口", re.compile(r"\bdry\b|\bdrier\b", re.I)),
    ("スパークリングワイン", re.compile(r"sparkling wine", re.I)),
    ("スティルワイン", re.compile(r"still wine", re.I)),
    ("酒精強化ワイン", re.compile(r"fortified wine", re.I)),
    ("残糖", re.compile(r"residual sugar", re.I)),
    ("発酵", re.compile(r"fermentation", re.I)),
    ("貴腐", re.compile(r"noble rot|botrytis", re.I)),
    ("澱", re.compile(r"lees|sediment", re.I)),
)
ENGLISH_TO_JAPANESE_OVERRIDES = {
    "An oxidatively aged dry fortified wine.": "酸化熟成させた辛口の酒精強化ワイン。",
    "What can happen when a red wine is served too warm?": (
        "赤ワインを温かすぎる温度で提供すると、どう感じられるか？"
    ),
    "Blue cheese must only be served with dry red wine.": (
        "ブルーチーズには辛口赤ワインだけを合わせなければならない。"
    ),
    "For off-dry to sweet carbonated sparkling wines": (
        "やや辛口から甘口の炭酸ガス注入方式スパークリングワインに用いる。"
    ),
    "DouroMoselNorthern Rhône": "ドウロ、モーゼル、北ローヌ",
    "Farms only its own vines and bottles solely estate fruit": (
        "自社畑のみを耕作し、自社畑で収穫したブドウだけを瓶詰めする。"
    ),
}


def load_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") not in {1, 2}:
        raise ValueError(f"Unsupported source pack schema: {payload.get('schemaVersion')}")
    return payload


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {
        str(record["id"]): normalize_cached_record(record) for record in read_jsonl(path)
    }


def write_cache(path: Path, records: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for identifier in sorted(records):
            record = normalize_cached_record(records[identifier])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary.replace(path)


def glossary_text(source_language: str, target_language: str) -> str:
    glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    if source_language == "en" and target_language == "ja":
        pairs = glossary.items()
    elif source_language == "ja" and target_language == "en":
        pairs = ((japanese, english) for english, japanese in glossary.items())
    else:
        raise ValueError(f"Unsupported language pair: {source_language}-{target_language}")
    return ", ".join(f"{source}={target}" for source, target in pairs)


def system_prompt(source_language: str, target_language: str) -> str:
    language_names = {"en": "English", "ja": "Japanese"}
    return (
        "You are a professional WSET Level 3 wine translator. "
        f"Translate every translatable JSON string value from "
        f"{language_names[source_language]} to natural, concise "
        f"{language_names[target_language]}. "
        "Keep JSON keys and item IDs unchanged. Preserve array length and ordering, "
        "proper nouns, appellations, grape varieties, numbers, units, symbols, and HTML. "
        "Do not answer or correct the study question. Do not add explanations. "
        "Specifically translate the prompt, answer, explanation, and every choice; "
        "never copy an English sentence into a Japanese field or vice versa. "
        "Use established wine terminology and the mandatory glossary. "
        "Return one JSON object with an items array only. No markdown. "
        f"Mandatory glossary: {glossary_text(source_language, target_language)}"
    )


def extract_response_content(response: dict[str, Any]) -> str:
    message = response.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("Ollama response did not contain message.content")
    content = message["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    return content


def ollama_translate(
    items: list[dict[str, Any]],
    *,
    source_language: str,
    target_language: str,
    model: str,
    endpoint: str,
    timeout: int,
) -> list[dict[str, Any]]:
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt(source_language, target_language)},
            {
                "role": "user",
                "content": json.dumps({"items": items}, ensure_ascii=False),
            },
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 16384},
        "keep_alive": "30m",
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    translated = json.loads(extract_response_content(payload))
    result = translated.get("items")
    if not isinstance(result, list):
        raise ValueError("Translation response did not contain an items list")
    return result


def extract_direct_translation(content: str) -> str:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    if (
        isinstance(payload, list)
        and len(payload) == 1
        and isinstance(payload[0], dict)
        and isinstance(payload[0].get("text"), str)
    ):
        return str(payload[0]["text"])
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        return str(payload["text"])
    return content


def direct_request(
    texts: list[str],
    *,
    source_language: str,
    target_language: str,
    model: str,
    endpoint: str,
    timeout: int,
) -> list[str]:
    def protected(value: str) -> str:
        prepared = re.sub(r"(?<=[a-z])(?=[A-Z])", "; ", value)
        if QUESTION_OPENING.search(prepared.strip()) or prepared.rstrip().endswith("?"):
            return f"Study question wording: “{prepared}”"
        return f"Study answer wording: “{prepared}”"

    marked = (
        protected(texts[0])
        if len(texts) == 1
        else "\n".join(
            f"⟦{index:04d}⟧ {protected(value)}"
            for index, value in enumerate(texts)
        )
    )
    message = json.dumps(
        [
            {
                "type": "text",
                "source_lang_code": source_language,
                "target_lang_code": target_language,
                "text": marked,
            }
        ],
        ensure_ascii=False,
    )
    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": min(1_600, max(128, int(len(marked) * 1.5))),
        },
        "keep_alive": "30m",
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    translated = extract_direct_translation(extract_response_content(payload))
    matches = list(DIRECT_MARKER.finditer(translated))
    if len(texts) == 1 and not matches and translated.strip():
        return [normalize_wine_terms(translated.strip(), target_language)]
    if [int(match.group(1)) for match in matches] != list(range(len(texts))):
        raise ValueError("TranslateGemma output markers did not match the request")
    values: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(translated)
        value = translated[match.end() : end].strip()
        if not value:
            raise ValueError(f"Blank direct translation at segment {index}")
        values.append(normalize_wine_terms(value, target_language))
    return values


def normalize_wine_terms(text: str, target_language: str) -> str:
    if text.startswith("この質問文"):
        quoted_sections = re.findall(r"「([^」]+)」", text)
        if quoted_sections:
            text = quoted_sections[-1].strip()
    elif text.startswith(("この文章", "この文の翻訳", "このテキスト")):
        quoted_sections = re.findall(r"「([^」]+)」", text)
        if quoted_sections:
            text = quoted_sections[0].strip()
    quoted = re.search(r"^[^\n「]{0,60}「([^」]+)」\s*$", text.strip())
    if quoted:
        text = quoted.group(1).strip()
    labeled_text = re.search(
        r"(?:\*\*)?(?:Text|テキスト)(?:\*\*)?\s*[:：]\s*([^\n]+)",
        text,
        flags=re.I,
    )
    if labeled_text and ("\n" in text or text.lstrip().startswith(("*", "Here's"))):
        text = labeled_text.group(1).strip()
    if "**Translation:**" in text:
        text = text.split("**Translation:**", 1)[1].strip()
        text = text.split("\n\n", 1)[0].strip()
    elif re.search(r"(?:^|\n)Translation:\s*", text, flags=re.I):
        text = re.split(r"(?:^|\n)Translation:\s*", text, maxsplit=1, flags=re.I)[-1]
        text = text.split("\n\n", 1)[0].strip()
    text = text.strip('"“”「」')
    text = re.sub(r"^\*+\s*|\s*\*+$", "", text).strip()
    text = re.sub(
        r"^(?:Text|テキスト|解答のヒント|回答|答え)\s*[:：]\s*",
        "",
        text.strip(),
        flags=re.I,
    )
    if target_language != "ja":
        return text
    if text.startswith(("Okay,", "Sure,")) and "\n\n" in text:
        text = text.rsplit("\n\n", 1)[-1].strip()
    replacements = {
        "タンニク": "タンニン",
        "タニク": "タンニン",
        "タニン": "タンニン",
        "澱（せんでい）": "澱",
        "澱(せんでい)": "澱",
        "沈殿物": "澱",
        "ドライなワイン": "辛口ワイン",
        "ドライな赤ワイン": "辛口の赤ワイン",
        "ドライな白ワイン": "辛口の白ワイン",
        "伝統的な方法": "トラディショナル方式",
        "伝統的な製法": "トラディショナル方式",
        "伝統方式": "トラディショナル方式",
        "リドリング（レミュワージュ）": "動瓶（ルミュアージュ）",
        "リドリング(レミュワージュ)": "動瓶（ルミュアージュ）",
        "リドリング": "動瓶",
        "澱（澱）": "澱",
        "静置ワイン": "スティルワイン",
        "静かなワイン": "スティルワイン",
        "デカンターに入れる": "デキャンタージュする",
        "デカンタージュ": "デキャンタージュ",
        "デカンティング": "デキャンタージュ",
        "デキャンティング": "デキャンタージュ",
        "デカントする": "デキャンタージュする",
        "デカントされる": "デキャンタージュされる",
        "酸性の料理": "酸味のある料理",
        "高酸性": "高い酸味",
        "高酸度": "高い酸味",
        "低酸性": "低い酸味",
        "残留糖分": "残糖",
        "渋みが強く辛口の赤ワイン": "タンニンが強い辛口の赤ワイン",
        "ワインの苦味や渋みを和らげる": "ワインの苦味やタンニンを弱く感じさせる",
        "麝香葡萄": "マスカット",
        "ペニアティックプレス": "ニューマティックプレス",
        "セミ・カーボニックマセレーション": "半炭酸ガス浸漬法",
        "セミカーボニックマセレーション": "半炭酸ガス浸漬法",
        "セミカーボニックマセラシオン": "半炭酸ガス浸漬法",
        "カーボニックマセレーション": "炭酸ガス浸漬法",
        "炭酸ワイン": "スパークリングワイン",
        "より酸っぱく、渋みを感じさせ": "より辛口で酸味を強く感じさせ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(
        r"セミ[・ ]?カーボニックマセラシオン",
        "半炭酸ガス浸漬法",
        text,
    )
    text = re.sub(r"カーボニックマセラシオン", "炭酸ガス浸漬法", text)
    text = text.replace("炭酸マセレーション", "炭酸ガス浸漬法")
    if len(text) >= 2 and text.startswith("「") and text.endswith("」"):
        text = text[1:-1].strip()
    return text


def normalize_cached_record(record: dict[str, Any]) -> dict[str, Any]:
    japanese = record.get("ja")
    if not isinstance(japanese, dict):
        return record
    normalized = dict(record)
    normalized_japanese = dict(japanese)
    for field in ("prompt", "answer", "explanation"):
        value = normalized_japanese.get(field)
        if isinstance(value, str):
            normalized_japanese[field] = normalize_wine_terms(value, "ja")
    choices = normalized_japanese.get("choices")
    if isinstance(choices, list):
        normalized_japanese["choices"] = [
            normalize_wine_terms(str(choice), "ja") for choice in choices
        ]
    normalized["ja"] = normalized_japanese
    return normalized


def has_target_script(source: str, translated: str, target_language: str) -> bool:
    if target_language == "ja" and len(re.findall(r"[A-Za-z]{2,}", source)) >= 3:
        return bool(re.search(r"[ぁ-んァ-ヶ一-龯]", translated))
    if target_language == "en" and len(re.findall(r"[ぁ-んァ-ヶ一-龯]", source)) >= 3:
        return not bool(re.search(r"[ぁ-んァ-ヶ一-龯]", translated))
    return True


def is_overexpanded(source: str, translated: str) -> bool:
    return len(translated) > max(240, int(len(source) * 2.5)) or (
        "**" in translated and "**" not in source
    )


def preserves_required_content(
    source: str, translated: str, target_language: str
) -> bool:
    source_numbers = re.findall(
        r"(?<![A-Za-z])\d+(?:[.,]\d+)*%?(?![A-Za-z])", source
    )
    if any(number not in translated for number in source_numbers):
        return False
    if target_language == "ja":
        return all(
            not source_pattern.search(source) or target_pattern.search(translated)
            for source_pattern, target_pattern in ENGLISH_TO_JAPANESE_REQUIREMENTS
        )
    return all(
        source_term not in source or target_pattern.search(translated)
        for source_term, target_pattern in JAPANESE_TO_ENGLISH_REQUIREMENTS
    )


def preserves_numbers(source: str, translated: str) -> bool:
    source_numbers = re.findall(
        r"(?<![A-Za-z])\d+(?:[.,]\d+)*%?(?![A-Za-z])", source
    )
    return all(number in translated for number in source_numbers)


def translation_is_acceptable(
    source: str, translated: str, target_language: str
) -> bool:
    return (
        has_target_script(source, translated, target_language)
        and not is_overexpanded(source, translated)
        and preserves_numbers(source, translated)
    )


def normalize_for_source(
    source: str, translated: str, target_language: str
) -> str:
    if target_language == "ja" and source in ENGLISH_TO_JAPANESE_OVERRIDES:
        return ENGLISH_TO_JAPANESE_OVERRIDES[source]
    return translated


def direct_translate_items(
    items: list[dict[str, Any]],
    *,
    source_language: str,
    target_language: str,
    model: str,
    endpoint: str,
    timeout: int,
    max_batch_chars: int,
    max_batch_segments: int,
    fallback_model: str | None,
) -> list[dict[str, Any]]:
    segment_paths: list[tuple[int, str, int | None]] = []
    source_segments: list[str] = []
    for item_index, item in enumerate(items):
        for field in ("prompt", "answer", "explanation"):
            value = item.get(field)
            if isinstance(value, str):
                segment_paths.append((item_index, field, None))
                source_segments.append(value)
        for choice_index, value in enumerate(item.get("choices") or []):
            segment_paths.append((item_index, "choices", choice_index))
            source_segments.append(str(value))

    translated_segments: list[str] = []
    offset = 0
    while offset < len(source_segments):
        end = offset
        characters = 0
        while end < len(source_segments) and end - offset < max_batch_segments:
            next_size = len(source_segments[end]) + 10
            if end > offset and characters + next_size > max_batch_chars:
                break
            characters += next_size
            end += 1
        translated_segments.extend(
            direct_request_adaptive(
                source_segments[offset:end],
                source_language=source_language,
                target_language=target_language,
                model=model,
                endpoint=endpoint,
                timeout=timeout,
            )
        )
        offset = end

    for index, (source, translated) in enumerate(
        zip(source_segments, translated_segments, strict=True)
    ):
        translated = normalize_for_source(source, translated, target_language)
        translated_segments[index] = translated
        if translation_is_acceptable(source, translated, target_language):
            continue
        translated_segments[index] = direct_request(
            [source],
            source_language=source_language,
            target_language=target_language,
            model=model,
            endpoint=endpoint,
            timeout=timeout,
        )[0]
        translated_segments[index] = normalize_for_source(
            source, translated_segments[index], target_language
        )
        if not translation_is_acceptable(
            source, translated_segments[index], target_language
        ) and fallback_model:
            translated_segments[index] = direct_request(
                [source],
                source_language=source_language,
                target_language=target_language,
                model=fallback_model,
                endpoint=endpoint,
                timeout=timeout,
            )[0]
            translated_segments[index] = normalize_for_source(
                source, translated_segments[index], target_language
            )
        if not translation_is_acceptable(
            source, translated_segments[index], target_language
        ):
            raise ValueError(
                "Translation QA failed at segment "
                f"{index}: source={source[:160]!r}; "
                f"translated={translated_segments[index][:160]!r}"
            )

    translated_items = [
        {
            "id": item["id"],
            "prompt": None,
            "answer": None,
            "explanation": None,
            "choices": [None] * len(item.get("choices") or []),
        }
        for item in items
    ]
    for (item_index, field, choice_index), value in zip(
        segment_paths, translated_segments, strict=True
    ):
        if choice_index is None:
            translated_items[item_index][field] = value
        else:
            translated_items[item_index]["choices"][choice_index] = value
    return translated_items


def direct_request_adaptive(
    texts: list[str],
    *,
    source_language: str,
    target_language: str,
    model: str,
    endpoint: str,
    timeout: int,
) -> list[str]:
    try:
        return direct_request(
            texts,
            source_language=source_language,
            target_language=target_language,
            model=model,
            endpoint=endpoint,
            timeout=timeout,
        )
    except ValueError:
        if len(texts) == 1:
            raise
        midpoint = len(texts) // 2
        return direct_request_adaptive(
            texts[:midpoint],
            source_language=source_language,
            target_language=target_language,
            model=model,
            endpoint=endpoint,
            timeout=timeout,
        ) + direct_request_adaptive(
            texts[midpoint:],
            source_language=source_language,
            target_language=target_language,
            model=model,
            endpoint=endpoint,
            timeout=timeout,
        )


def validate_batch(
    source_items: list[dict[str, Any]],
    translated_items: list[dict[str, Any]],
    target_language: str,
) -> dict[str, dict[str, Any]]:
    source_by_id = {str(item["id"]): item for item in source_items}
    translated_by_id = {str(item.get("id")): item for item in translated_items}
    if set(source_by_id) != set(translated_by_id):
        raise ValueError("Translation response IDs did not match the request")
    validated: dict[str, dict[str, Any]] = {}
    for identifier, source in source_by_id.items():
        translated = translated_by_id[identifier]
        if not isinstance(translated.get("prompt"), str) or not translated["prompt"].strip():
            raise ValueError(f"Missing translated prompt for {identifier}")
        for optional in ("answer", "explanation"):
            if source.get(optional) is not None and not isinstance(
                translated.get(optional), str
            ):
                raise ValueError(f"Missing translated {optional} for {identifier}")
        source_choices = source.get("choices") or []
        translated_choices = translated.get("choices")
        if not isinstance(translated_choices, list) or len(translated_choices) != len(
            source_choices
        ):
            raise ValueError(f"Choice count changed for {identifier}")
        if not all(isinstance(choice, str) and choice.strip() for choice in translated_choices):
            raise ValueError(f"Blank translated choice for {identifier}")
        translated_strings = [
            translated["prompt"],
            *(
                [translated["answer"]]
                if isinstance(translated.get("answer"), str)
                else []
            ),
            *(
                [translated["explanation"]]
                if isinstance(translated.get("explanation"), str)
                else []
            ),
            *translated_choices,
        ]
        source_strings = [
            source["prompt"],
            *([source["answer"]] if isinstance(source.get("answer"), str) else []),
            *(
                [source["explanation"]]
                if isinstance(source.get("explanation"), str)
                else []
            ),
            *source_choices,
        ]
        for source_text, translated_text in zip(
            source_strings, translated_strings, strict=True
        ):
            assert isinstance(translated_text, str)
            ascii_words = re.findall(r"[A-Za-z]{2,}", source_text)
            japanese_chars = re.findall(r"[ぁ-んァ-ヶ一-龯]", translated_text)
            if target_language == "ja" and len(ascii_words) >= 3 and not japanese_chars:
                raise ValueError(f"English text remained in Japanese output for {identifier}")
            if (
                target_language == "en"
                and len(re.findall(r"[ぁ-んァ-ヶ一-龯]", source_text)) >= 3
                and re.search(r"[ぁ-んァ-ヶ一-龯]", translated_text)
            ):
                raise ValueError(f"Japanese text remained in English output for {identifier}")
        validated[identifier] = {
            "prompt": translated["prompt"].strip(),
            "answer": (
                translated.get("answer", "").strip()
                if source.get("answer") is not None
                else None
            ),
            "explanation": (
                translated.get("explanation", "").strip()
                if source.get("explanation") is not None
                else None
            ),
            "choices": [str(choice).strip() for choice in translated_choices],
        }
    return validated


def original_content(question: dict[str, Any]) -> dict[str, Any]:
    translations = question.get("translations")
    language = str(question.get("language") or "en")
    if isinstance(translations, dict) and isinstance(translations.get(language), dict):
        return translations[language]
    return translatable_content(question)


def request_item(question: dict[str, Any]) -> dict[str, Any]:
    return {"id": question["id"], **original_content(question)}


def cache_record_is_acceptable(
    question: dict[str, Any], record: dict[str, Any]
) -> bool:
    source_language = str(question.get("language") or "en")
    target_language = "ja" if source_language == "en" else "en"
    source = original_content(question)
    translated = record.get(target_language)
    if not isinstance(translated, dict):
        return False
    source_strings = [
        source.get("prompt"),
        source.get("answer"),
        source.get("explanation"),
        *(source.get("choices") or []),
    ]
    translated_choices = translated.get("choices")
    if not isinstance(translated_choices, list) or len(translated_choices) != len(
        source.get("choices") or []
    ):
        return False
    translated_strings = [
        translated.get("prompt"),
        translated.get("answer"),
        translated.get("explanation"),
        *translated_choices,
    ]
    for source_text, translated_text in zip(
        source_strings, translated_strings, strict=True
    ):
        if source_text is None:
            if translated_text is not None:
                return False
            continue
        if not isinstance(translated_text, str) or not translation_is_acceptable(
            str(source_text), translated_text, target_language
        ):
            return False
    return True


def apply_source_overrides_to_record(
    question: dict[str, Any], record: dict[str, Any]
) -> dict[str, Any]:
    source_language = str(question.get("language") or "en")
    target_language = "ja" if source_language == "en" else "en"
    source = original_content(question)
    translated = record.get(target_language)
    if not isinstance(translated, dict):
        return record
    normalized = dict(record)
    normalized_target = dict(translated)
    for field in ("prompt", "answer", "explanation"):
        source_value = source.get(field)
        translated_value = normalized_target.get(field)
        if isinstance(source_value, str) and isinstance(translated_value, str):
            normalized_target[field] = normalize_for_source(
                source_value, translated_value, target_language
            )
    source_choices = source.get("choices") or []
    translated_choices = normalized_target.get("choices")
    if isinstance(translated_choices, list) and len(translated_choices) == len(
        source_choices
    ):
        normalized_target["choices"] = [
            normalize_for_source(str(source_value), str(translated_value), target_language)
            for source_value, translated_value in zip(
                source_choices, translated_choices, strict=True
            )
        ]
    normalized[target_language] = normalized_target
    return normalized


def translate_batch_with_retries(
    items: list[dict[str, Any]],
    *,
    source_language: str,
    target_language: str,
    model: str,
    endpoint: str,
    timeout: int,
    backend: str,
    max_batch_chars: int,
    max_batch_segments: int,
    fallback_model: str | None,
) -> dict[str, dict[str, Any]]:
    error: Exception | None = None
    for attempt in range(1, 4):
        try:
            if backend == "translategemma":
                translated = direct_translate_items(
                    items,
                    source_language=source_language,
                    target_language=target_language,
                    model=model,
                    endpoint=endpoint,
                    timeout=timeout,
                    max_batch_chars=max_batch_chars,
                    max_batch_segments=max_batch_segments,
                    fallback_model=fallback_model,
                )
            else:
                translated = ollama_translate(
                    items,
                    source_language=source_language,
                    target_language=target_language,
                    model=model,
                    endpoint=endpoint,
                    timeout=timeout,
                )
            return validate_batch(items, translated, target_language)
        except (ValueError, json.JSONDecodeError, urllib.error.URLError) as caught:
            error = caught
            print(f"retry {attempt}/3 after translation error: {caught}", flush=True)
            time.sleep(attempt)
    raise RuntimeError(f"Translation failed after 3 attempts: {error}")


def translate_pack(
    *,
    pack_path: Path,
    cache_path: Path,
    model: str,
    endpoint: str,
    batch_size: int,
    timeout: int,
    limit: int | None,
    retranslate: bool,
    backend: str,
    max_batch_chars: int,
    max_batch_segments: int,
    fallback_model: str | None,
) -> tuple[int, int]:
    pack = load_pack(pack_path)
    questions = list(pack["questions"])
    cache = load_cache(cache_path)
    questions_by_id = {str(question["id"]): question for question in questions}
    for suffix in range(1, 16):
        english_id = f"curated-service-en-{suffix:03d}"
        japanese_id = f"curated-service-ja-{suffix:03d}"
        english_question = questions_by_id.get(english_id)
        japanese_question = questions_by_id.get(japanese_id)
        if english_question is None or japanese_question is None:
            continue
        paired_content = {
            "en": original_content(english_question),
            "ja": original_content(japanese_question),
        }
        for question in (english_question, japanese_question):
            identifier = str(question["id"])
            cache[identifier] = {
                "id": identifier,
                "sourceFingerprint": question_fingerprint(question),
                **paired_content,
                "model": "curated_bilingual_pair",
                "status": "human_reviewed_translation",
            }
    for question in questions:
        identifier = str(question["id"])
        if identifier in cache:
            cache[identifier] = apply_source_overrides_to_record(
                question, cache[identifier]
            )
    write_cache(cache_path, cache)
    pending: list[dict[str, Any]] = []
    for question in questions:
        identifier = str(question["id"])
        cached = cache.get(identifier)
        if not retranslate and (
            cached is not None
            and cached.get("sourceFingerprint") == question_fingerprint(question)
            and isinstance(cached.get("en"), dict)
            and isinstance(cached.get("ja"), dict)
            and cache_record_is_acceptable(question, cached)
        ):
            continue
        pending.append(question)
    if limit is not None:
        pending = pending[:limit]

    completed_now = 0
    for source_language in ("en", "ja"):
        language_questions = [
            question
            for question in pending
            if str(question.get("language") or "en") == source_language
        ]
        target_language = "ja" if source_language == "en" else "en"
        for offset in range(0, len(language_questions), batch_size):
            batch_questions = language_questions[offset : offset + batch_size]
            items = [request_item(question) for question in batch_questions]
            translated = translate_batch_with_retries(
                items,
                source_language=source_language,
                target_language=target_language,
                model=model,
                endpoint=endpoint,
                timeout=timeout,
                backend=backend,
                max_batch_chars=max_batch_chars,
                max_batch_segments=max_batch_segments,
                fallback_model=fallback_model,
            )
            for question in batch_questions:
                identifier = str(question["id"])
                original = original_content(question)
                counterpart = translated[identifier]
                correct_index = question.get("correctAnswerIndex")
                if (
                    isinstance(correct_index, int)
                    and 0 <= correct_index < len(counterpart["choices"])
                    and original.get("answer") is not None
                ):
                    counterpart["answer"] = counterpart["choices"][correct_index]
                languages = (
                    {"en": original, "ja": counterpart}
                    if source_language == "en"
                    else {"en": counterpart, "ja": original}
                )
                cache[identifier] = {
                    "id": identifier,
                    "sourceFingerprint": question_fingerprint(question),
                    **languages,
                    "model": (
                        f"{model}+{fallback_model}-fallback"
                        if backend == "translategemma" and fallback_model
                        else model
                    ),
                    "status": "machine_translated",
                }
                completed_now += 1
            write_cache(cache_path, cache)
            total_valid = sum(
                record.get("sourceFingerprint") == question_fingerprint(question)
                for question in questions
                if (record := cache.get(str(question["id"]))) is not None
            )
            print(
                f"translated {completed_now}/{len(pending)} this run; "
                f"cache {total_valid}/{len(questions)}",
                flush=True,
            )
    return completed_now, len(questions)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate the private app pack with a local Ollama model"
    )
    parser.add_argument("--pack", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=TRANSLATION_CACHE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--backend",
        choices=("translategemma", "ollama-json"),
        default="translategemma",
    )
    parser.add_argument("--max-batch-chars", type=int, default=1_200)
    parser.add_argument("--max-batch-segments", type=int, default=4)
    parser.add_argument("--fallback-model", default="translategemma:4b")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--retranslate",
        action="store_true",
        help="Overwrite matching cached translations",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Rebuild the app pack after translation; schema v2 is used only when complete",
    )
    args = parser.parse_args()
    completed, total = translate_pack(
        pack_path=args.pack,
        cache_path=args.cache,
        model=args.model,
        endpoint=args.endpoint,
        batch_size=args.batch_size,
        timeout=args.timeout,
        limit=args.limit,
        retranslate=args.retranslate,
        backend=args.backend,
        max_batch_chars=args.max_batch_chars,
        max_batch_segments=args.max_batch_segments,
        fallback_model=args.fallback_model or None,
    )
    if args.finalize:
        payload = build_pack(args.pack)
        print(
            f"rebuilt app pack schema v{payload['schemaVersion']} "
            f"with {payload['questionCount']} questions",
            flush=True,
        )
    print(f"completed {completed} translations; source total {total}", flush=True)


if __name__ == "__main__":
    main()
