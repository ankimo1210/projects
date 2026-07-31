# Whisper ローカル文字起こしメモ (2026-07-29)

## やったこと

`新規録音 23.m4a`(40.6分, 日本語会話)を mlx-whisper でローカル文字起こし。
結果は `~/Downloads/新規録音23_文字起こし.txt`(625セグメント, タイムスタンプ付き)。

## 構成のポイント

- モデル: `mlx-community/whisper-large-v3-turbo`(Apple Silicon GPU 最適化)
- ffmpeg 不要構成:
  - m4a → WAV 変換は macOS 標準の `afconvert`
  - WAV 読み込みは stdlib `wave` + numpy(mlx_whisper のデフォルトは ffmpeg を要求するため配列で直接渡す)
- `language="ja"` を明示、`condition_on_previous_text=False` で長尺音声の繰り返し幻覚を抑制
- 実行は `uv run --no-project --with mlx-whisper python transcribe.py`(恒久インストールなし)

## 実行手順

```sh
afconvert -f WAVE -d LEI16@16000 -c 1 input.m4a rec23_16k.wav
uv run --no-project --with mlx-whisper python transcribe.py
```

(`transcribe.py` 内の `WAV` / 出力ファイル名は決め打ちなので、別ファイルに使うときは書き換えるか CLI 引数化する)

## 性能・品質

- 処理本体は約75秒(実時間の約33倍速)。初回のみモデルDLに約15分(~1.6GB, HF キャッシュに保存済み)
- 会話の流れは良好。同時発話・固有名詞に誤認識あり。話者分離は不可

## 次に試す候補

- 精度比較: `large-v3`(非turbo)、Qwen3-ASR、kotoba-whisper
- 話者分離: WhisperX + pyannote
