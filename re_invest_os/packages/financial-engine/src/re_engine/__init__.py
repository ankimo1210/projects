"""re_invest_os 計算エンジン。

すべて純粋関数で構成される。I/O・LLM呼び出し・グローバル状態を含まない。
仕様: docs/architecture/calculation_engine_spec.md
"""

ENGINE_VERSION = "0.1.0"

from re_engine import constants, models  # noqa: E402

__all__ = ["ENGINE_VERSION", "constants", "models"]
