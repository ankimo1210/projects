from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from scripts.build_private_app_pack import (  # noqa: E402
    DEFAULT_OUTPUT,
    TRANSLATION_CACHE,
    build_pack,
    question_fingerprint,
)
from scripts.translate_private_app_pack import (  # noqa: E402
    apply_source_overrides_to_record,
    cache_record_is_acceptable,
    load_cache,
    load_pack,
    normalize_for_source,
    normalize_wine_terms,
    original_content,
    write_cache,
)

MODEL_BY_DIRECTION = {
    ("en", "ja"): "staka/fugumt-en-ja",
    ("ja", "en"): "staka/fugumt-ja-en",
}


def load_model(source_language: str, target_language: str) -> tuple[Any, Any, str]:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    model_name = MODEL_BY_DIRECTION[(source_language, target_language)]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)
    model.eval()
    return tokenizer, model, device


def translate_texts(
    texts: list[str],
    *,
    tokenizer: Any,
    model: Any,
    device: str,
    batch_size: int,
) -> list[str]:
    import torch

    indexed = sorted(enumerate(texts), key=lambda item: len(item[1]))
    translated = [""] * len(texts)
    for offset in range(0, len(indexed), batch_size):
        batch = indexed[offset : offset + batch_size]
        encoded = tokenizer(
            [text for _, text in batch],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to(device)
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=512,
                num_beams=1,
                do_sample=False,
            )
        values = tokenizer.batch_decode(generated, skip_special_tokens=True)
        for (index, _), value in zip(batch, values, strict=True):
            translated[index] = value.strip()
    return translated


def translate_questions(
    questions: list[dict[str, Any]],
    *,
    source_language: str,
    target_language: str,
    tokenizer: Any,
    model: Any,
    device: str,
    batch_size: int,
) -> dict[str, dict[str, Any]]:
    paths: list[tuple[int, str, int | None]] = []
    texts: list[str] = []
    originals = [original_content(question) for question in questions]
    for question_index, content in enumerate(originals):
        for field in ("prompt", "answer", "explanation"):
            value = content.get(field)
            if isinstance(value, str):
                paths.append((question_index, field, None))
                texts.append(value)
        for choice_index, value in enumerate(content.get("choices") or []):
            paths.append((question_index, "choices", choice_index))
            texts.append(str(value))

    values = translate_texts(
        texts,
        tokenizer=tokenizer,
        model=model,
        device=device,
        batch_size=batch_size,
    )
    targets: list[dict[str, Any]] = [
        {
            "prompt": None,
            "answer": None,
            "explanation": None,
            "choices": [None] * len(content.get("choices") or []),
        }
        for content in originals
    ]
    for (question_index, field, choice_index), source, value in zip(
        paths, texts, values, strict=True
    ):
        value = normalize_wine_terms(value, target_language)
        value = normalize_for_source(source, value, target_language)
        if choice_index is None:
            targets[question_index][field] = value
        else:
            targets[question_index]["choices"][choice_index] = value

    result: dict[str, dict[str, Any]] = {}
    for question, source, target in zip(questions, originals, targets, strict=True):
        correct_index = question.get("correctAnswerIndex")
        if (
            isinstance(correct_index, int)
            and 0 <= correct_index < len(target["choices"])
            and source.get("answer") is not None
        ):
            target["answer"] = target["choices"][correct_index]
        languages = (
            {"en": source, "ja": target}
            if source_language == "en"
            else {"en": target, "ja": source}
        )
        identifier = str(question["id"])
        result[identifier] = {
            "id": identifier,
            "sourceFingerprint": question_fingerprint(question),
            **languages,
            "model": MODEL_BY_DIRECTION[(source_language, target_language)],
            "status": "machine_translated_fast_pass",
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast local FuguMT app-pack translation")
    parser.add_argument("--pack", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=TRANSLATION_CACHE)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--question-chunk", type=int, default=500)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()

    pack = load_pack(args.pack)
    questions = list(pack["questions"])
    cache = load_cache(args.cache)
    questions_by_id = {str(question["id"]): question for question in questions}
    for identifier in list(cache):
        if identifier in questions_by_id:
            cache[identifier] = apply_source_overrides_to_record(
                questions_by_id[identifier], cache[identifier]
            )

    for source_language, target_language in (("en", "ja"), ("ja", "en")):
        pending = [
            question
            for question in questions
            if str(question.get("language") or "en") == source_language
            and not (
                (record := cache.get(str(question["id"])))
                and record.get("sourceFingerprint") == question_fingerprint(question)
                and cache_record_is_acceptable(question, record)
            )
        ]
        if not pending:
            continue
        tokenizer, model, device = load_model(source_language, target_language)
        for offset in range(0, len(pending), args.question_chunk):
            chunk = pending[offset : offset + args.question_chunk]
            cache.update(
                translate_questions(
                    chunk,
                    source_language=source_language,
                    target_language=target_language,
                    tokenizer=tokenizer,
                    model=model,
                    device=device,
                    batch_size=args.batch_size,
                )
            )
            write_cache(args.cache, cache)
            print(
                f"{source_language}->{target_language}: "
                f"{min(offset + len(chunk), len(pending))}/{len(pending)}; "
                f"cache {len(cache)}/{len(questions)}",
                flush=True,
            )
        del model

    if args.finalize:
        payload = build_pack(args.pack)
        print(
            f"rebuilt schema v{payload['schemaVersion']} with "
            f"{payload['questionCount']} questions",
            flush=True,
        )


if __name__ == "__main__":
    main()
