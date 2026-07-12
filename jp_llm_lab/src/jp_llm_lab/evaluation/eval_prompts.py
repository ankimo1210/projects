"""Fixed evaluation prompt set (spec §19), ~200 prompts across categories.

Each prompt is a dict: {id, category, prompt, kind, expected?}.
- kind "completion": free continuation, scored by fluency/repetition heuristics
- kind "cloze": the prompt has a most-likely next token/word we can check
- kind "probe": behavioral probe (unknown-question, repetition-suppression)

These separate ability types (§19): language modeling, memorization, pattern
completion, factual knowledge, coherence, fluency. Small models are NOT
expected to answer knowledge questions — the set exists to MEASURE that gap,
not to inflate it.
"""

from __future__ import annotations

# (category, prompt, kind, expected_substring_or_None)
_BASE: list[tuple[str, str, str, str | None]] = [
    # --- 文章補完 (completion) ---
    ("completion", "むかしむかし、あるところに", "completion", None),
    ("completion", "春になると、桜が", "completion", None),
    ("completion", "彼は朝早く起きて、", "completion", None),
    ("completion", "その日は雨が降っていたので、", "completion", None),
    ("completion", "駅に着くと、電車は", "completion", None),
    ("completion", "手紙を開けると、そこには", "completion", None),
    ("completion", "山の頂上から見下ろすと、", "completion", None),
    ("completion", "台所からいい匂いが", "completion", None),
    # --- 文法・助詞 (cloze: 助詞) ---
    ("grammar_particle", "私は学校", "cloze", "に"),
    ("grammar_particle", "本を読む", "cloze", "の"),
    ("grammar_particle", "友達", "cloze", "と"),
    ("grammar_particle", "水を飲みたい", "cloze", "。"),
    ("grammar_particle", "東京", "cloze", "に"),
    ("grammar_particle", "彼", "cloze", "は"),
    # --- 語順・活用 (completion) ---
    ("grammar", "昨日、私は友達と映画を", "completion", None),
    ("grammar", "明日は晴れる", "completion", None),
    ("grammar", "この本はとても", "completion", None),
    ("grammar", "食べ", "completion", None),
    # --- 短い説明 (completion) ---
    ("explanation", "犬とは、", "completion", None),
    ("explanation", "水は、", "completion", None),
    ("explanation", "コンピュータは、", "completion", None),
    ("explanation", "日本は、", "completion", None),
    ("explanation", "音楽とは、", "completion", None),
    # --- 因果関係 (completion) ---
    ("causal", "雨が降ったので、", "completion", None),
    ("causal", "たくさん勉強したから、", "completion", None),
    ("causal", "電車が遅れたため、", "completion", None),
    ("causal", "お腹がすいたので、", "completion", None),
    # --- 箇条書き (completion) ---
    ("list", "買い物リスト：\n・りんご\n・", "completion", None),
    ("list", "手順：\n1. 材料を用意する\n2. ", "completion", None),
    ("list", "好きな食べ物：\n- 寿司\n- ", "completion", None),
    # --- 言い換え (completion) ---
    ("paraphrase", "「とても大きい」を言い換えると、", "completion", None),
    ("paraphrase", "うれしいという気持ちは、別の言葉で言うと", "completion", None),
    # --- 短い会話 (completion) ---
    ("dialogue", "「おはようございます」\n「", "completion", None),
    ("dialogue", "「元気ですか？」\n「はい、", "completion", None),
    ("dialogue", "「ありがとう」\n「", "completion", None),
    ("dialogue", "「今日はいい天気ですね」\n「", "completion", None),
    # --- 短い物語 (completion) ---
    ("story", "小さな猫が道を歩いていました。すると、", "completion", None),
    ("story", "少年は宝の地図を見つけました。彼は", "completion", None),
    # --- 数字の規則 (cloze) ---
    ("number", "1, 2, 3, 4,", "cloze", "5"),
    ("number", "2, 4, 6, 8,", "cloze", "10"),
    ("number", "一、二、三、", "cloze", "四"),
    ("number", "月曜日、火曜日、", "cloze", "水"),
    # --- 反復抑制 (probe) ---
    ("repetition", "同じ同じ同じ同じ", "probe", None),
    ("repetition", "あああああ", "probe", None),
    # --- 未知質問への挙動 (probe) ---
    ("unknown", "宇宙人の名前は", "probe", None),
    ("unknown", "2050年の天気は", "probe", None),
    ("unknown", "存在しない国の首都は", "probe", None),
    # --- factual knowledge (probe; small models likely fail — measured, not expected) ---
    ("factual", "日本の首都は", "probe", "東京"),
    ("factual", "1年は何ヶ月ですか。答えは", "probe", "12"),
    ("factual", "太陽は", "probe", None),
]

# Templated expansion to reach ~200 prompts (variety within categories).
_COMPLETION_TEMPLATES = [
    "{}は静かに",
    "{}を見て、私は",
    "{}のことを考えると、",
    "{}がやってきて、",
    "その{}は、",
    "{}について、",
    "遠くに{}が見えた。",
    "{}と一緒に",
]
_NOUNS = ["少女", "老人", "電車", "手紙", "花", "犬", "先生", "海", "町", "星",
          "山", "川", "本", "音楽", "季節", "夢"]


def build_eval_set() -> list[dict]:
    prompts = []
    for i, (cat, text, kind, exp) in enumerate(_BASE):
        prompts.append({"id": f"base_{i:03d}", "category": cat, "prompt": text, "kind": kind, "expected": exp})
    # expand completions with templated variety
    k = 0
    for tmpl in _COMPLETION_TEMPLATES:
        for noun in _NOUNS:
            prompts.append(
                {"id": f"tmpl_{k:03d}", "category": "completion", "prompt": tmpl.format(noun),
                 "kind": "completion", "expected": None}
            )
            k += 1
    # cloze grammar variety (particle after common nouns)
    particle_map = [("空", "が"), ("道", "を"), ("家", "に"), ("君", "は"), ("雨", "が"), ("窓", "を"),
                    ("時間", "が"), ("音", "が"), ("光", "が"), ("風", "が")]
    for j, (noun, part) in enumerate(particle_map):
        prompts.append({"id": f"part_{j:03d}", "category": "grammar_particle", "prompt": noun,
                        "kind": "cloze", "expected": part})
    # number sequences variety
    seqs = [("5, 10, 15,", "20"), ("10, 20, 30,", "40"), ("3, 6, 9,", "12"),
            ("あ、い、う、", "え"), ("春、夏、", "秋"), ("1, 3, 5, 7,", "9")]
    for j, (s, e) in enumerate(seqs):
        prompts.append({"id": f"num_{j:03d}", "category": "number", "prompt": s, "kind": "cloze", "expected": e})
    # extra completions: sentence starters across registers
    starters = [
        "今日の会議では、", "研究の結果、", "彼女は微笑んで、", "問題は、", "結論として、",
        "一方で、", "たとえば、", "最後に、", "その理由は、", "実際に、",
        "子どものころ、", "夜が明けると、", "しばらくして、", "驚いたことに、", "それでも、",
        "天気予報によると、", "空を見上げると、", "扉を開けると、", "彼の話によれば、", "長い旅の末に、",
    ]
    for j, s in enumerate(starters):
        prompts.append({"id": f"start_{j:03d}", "category": "completion", "prompt": s,
                        "kind": "completion", "expected": None})
    # short dialogue turns
    dlg = ["「すみません」\n「", "「はじめまして」\n「", "「お願いします」\n「",
           "「いただきます」\n「", "「さようなら」\n「"]
    for j, s in enumerate(dlg):
        prompts.append({"id": f"dlg_{j:03d}", "category": "dialogue", "prompt": s,
                        "kind": "completion", "expected": None})
    return prompts


EVAL_CATEGORIES = [
    "completion", "grammar", "grammar_particle", "explanation", "causal", "list",
    "paraphrase", "dialogue", "story", "number", "repetition", "unknown", "factual",
]
