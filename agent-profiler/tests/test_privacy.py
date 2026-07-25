from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agent_profiler.privacy import REDACTED, redact, redact_text


def test_redacts_sensitive_keys_and_known_secret_shapes() -> None:
    value = {
        "Authorization": "Bearer abcdefghijklmnop",
        "nested": {
            "api_key": "sk-abcdefghijklmnop",
            "command": "API_TOKEN=top-secret pytest",
        },
        "env": {"NOT_OBVIOUSLY_SECRET": "private-value"},
        "token": "opaque-value",
    }
    result = redact(value)
    assert result["Authorization"] == REDACTED
    assert result["nested"]["api_key"] == REDACTED
    assert "top-secret" not in result["nested"]["command"]
    assert result["env"] == REDACTED
    assert result["token"] == REDACTED


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=100))
def test_redaction_is_idempotent(value: str) -> None:
    assert redact_text(redact_text(value)) == redact_text(value)
