from __future__ import annotations

from .models import TableCandidates, TableInfo

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "messages": [
        "text",
        "message",
        "content",
        "chat",
        "talk",
        "sender",
        "from",
        "created",
        "timestamp",
        "date",
        "type",
    ],
    "rooms": ["chat", "room", "group", "mid", "name", "title"],
    "contacts": ["contact", "member", "user", "mid", "name", "display"],
    "attachments": ["media", "image", "video", "audio", "file", "path", "attachment"],
}

_TOP_N = 3


def _score(table: TableInfo, keywords: list[str]) -> int:
    col_names = [c.name.lower() for c in table.columns]
    score = sum(1 for kw in keywords if any(kw in cn for cn in col_names))
    if table.row_count is not None and table.row_count > 1000:
        score += 2
    return score


def classify(tables: list[TableInfo]) -> TableCandidates:
    def top(category: str) -> list[str]:
        kws = _CATEGORY_KEYWORDS[category]
        scored = [(t.name, _score(t, kws)) for t in tables]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, s in scored[:_TOP_N] if s > 0]

    return TableCandidates(
        messages=top("messages"),
        rooms=top("rooms"),
        contacts=top("contacts"),
        attachments=top("attachments"),
    )


def guess_message_columns(col_names: list[str]) -> dict[str, str | None]:
    """Heuristically map standard field names to actual column names."""
    lower = {c.lower(): c for c in col_names}

    def find(*candidates: str) -> str | None:
        for kw in candidates:
            for col_lower, col_orig in lower.items():
                if kw in col_lower:
                    return col_orig
        return None

    return {
        "message_id": find("z_pk", "rowid", "id", "msgid", "message_id"),
        "chat_id": find("chatid", "chat_id", "roomid", "room_id", "groupid"),
        "sender_id": find("sender", "from", "authorid", "author_id", "user_id"),
        "timestamp": find("timestamp", "created", "date", "time", "sent"),
        "text": find("text", "message", "content", "body"),
        "type": find("type", "msgtype", "message_type"),
    }
