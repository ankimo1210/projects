from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path

from .safety import confirm_output_dir, safe_filename
from .utils import get_logger

logger = get_logger(__name__)

_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;
     max-width:800px;margin:0 auto;padding:1em;background:#f0f0f0}
h1{font-size:1.05em;color:#555;padding:.6em .8em;background:#fff;
   border-radius:10px;margin-bottom:.8em;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.msg{display:flex;margin:.35em 0;align-items:flex-end;gap:.5em}
.msg.me{flex-direction:row-reverse}
.balloon{max-width:68%;background:#fff;border-radius:18px 18px 18px 4px;
         padding:.45em .8em;box-shadow:0 1px 2px rgba(0,0,0,.1);
         font-size:.92em;white-space:pre-wrap;word-break:break-word;line-height:1.45}
.msg.me .balloon{background:#c6f0c2;border-radius:18px 18px 4px 18px}
.sender{font-size:.7em;color:#888;margin-bottom:.15em}
.ts{font-size:.68em;color:#bbb;align-self:flex-end;white-space:nowrap;padding-bottom:.25em}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #ddd;padding:.4em .8em;text-align:left}
th{background:#eee}
td:last-child{text-align:right}
a{color:#07a}
.badge{display:inline-block;font-size:.72em;padding:.1em .45em;border-radius:6px;
       margin-right:.3em;background:#e0e0e0;color:#666}
.badge.dm{background:#d6eaff;color:#366}
.badge.grp{background:#ffecd6;color:#743}
"""

# ZCONTENTTYPE → 表示テキスト
_CTYPE_LABEL: dict[str, str] = {
    "1": "📷 画像",
    "2": "🎥 動画",
    "5": "🎁 その他",
    "6": "📞 通話",
    "7": "🎫 スタンプ",
    "111": "📎 添付",
    "112": "📷 画像",
}


def _detect_format(fieldnames: list[str]) -> str:
    """Return 'named' if CSV has chat_name/sender_name, else 'normalized'."""
    if "chat_name" in fieldnames and "sender_name" in fieldnames:
        return "named"
    return "normalized"


def _read_messages(messages_csv: Path) -> tuple[list[dict], str]:
    with messages_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fmt = _detect_format(reader.fieldnames or [])
    return rows, fmt


def _render_page(title: str, body: str) -> str:
    return (
        f'<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def _ctype_text(ctype: str, raw_text: str) -> str:
    label = _CTYPE_LABEL.get(ctype, "")
    if label:
        return label + (f" {html.escape(raw_text)}" if raw_text else "")
    return html.escape(raw_text)


def _bubble(msg: dict, fmt: str) -> str:
    if fmt == "named":
        sender_name = msg.get("sender_name") or "(自分)"
        is_me = sender_name == "(自分)"
        ts_raw = msg.get("timestamp_iso") or ""
        ctype = str(msg.get("content_type") or "0")
        raw_text = str(msg.get("text") or "")
    else:
        sender_name = msg.get("sender_id") or "(自分)"
        is_me = not msg.get("sender_id")
        ts_raw = msg.get("timestamp_iso_guess") or msg.get("timestamp_raw") or ""
        ctype = str(msg.get("message_type") or "0")
        raw_text = str(msg.get("text") or "")

    ts = html.escape(ts_raw[:16].replace("T", " ")) if ts_raw else ""
    text = _ctype_text(ctype, raw_text)
    cls = "msg me" if is_me else "msg"
    sender_html = "" if is_me else f'<div class="sender">{html.escape(sender_name)}</div>'

    return (
        f'<div class="{cls}">'
        f'<div><{sender_html}<div class="balloon">{text}</div></div>'
        f'<div class="ts">{ts}</div>'
        f"</div>\n"
    )


def render(
    messages_csv: Path,
    out_dir: Path,
    split_by_chat: bool = True,
) -> Path:
    if not messages_csv.exists():
        raise FileNotFoundError(f"Messages CSV not found: {messages_csv}")

    html_dir = confirm_output_dir(out_dir / "html")
    messages, fmt = _read_messages(messages_csv)
    logger.info("CSV format detected: %s (%d rows)", fmt, len(messages))

    if not messages:
        logger.warning("No messages found in %s", messages_csv)

    chat_key = "chat_name" if fmt == "named" else "chat_id"
    chat_type_key = "chat_type" if fmt == "named" else None

    if split_by_chat:
        by_chat: dict[str, list[dict]] = defaultdict(list)
        for msg in messages:
            by_chat[str(msg.get(chat_key) or "unknown")].append(msg)

        # Sort by message count descending
        sorted_chats = sorted(by_chat.items(), key=lambda x: len(x[1]), reverse=True)

        index_rows: list[tuple[str, str, int, str]] = []
        for chat_id, msgs in sorted_chats:
            fname = f"chat_{safe_filename(chat_id)}.html"
            ctype_label = msgs[0].get(chat_type_key, "") if chat_type_key else ""
            icon = "💬" if ctype_label == "1対1" else ("👥" if ctype_label == "グループ" else "💬")
            header = f"<h1>{icon} {html.escape(chat_id)}</h1>\n"
            bubbles = "".join(_bubble(m, fmt) for m in msgs)
            back = '<p style="margin-top:1em"><a href="index.html">← 一覧に戻る</a></p>'
            (html_dir / fname).write_text(
                _render_page(chat_id, header + bubbles + back),
                encoding="utf-8",
            )
            index_rows.append((chat_id, ctype_label, len(msgs), fname))

        rows_html = "\n".join(
            f"<tr>"
            f'<td><span class="badge {"dm" if t == "1対1" else "grp"}">{t or "?"}</span>'
            f'<a href="{html.escape(f)}">{html.escape(n)}</a></td>'
            f"<td>{c:,}</td></tr>"
            for n, t, c, f in index_rows
        )
        index_body = (
            "<h1>💬 LINE メッセージ一覧</h1>\n"
            "<table><tr><th>チャット名</th><th>件数</th></tr>\n"
            f"{rows_html}\n</table>"
        )
    else:
        body = "<h1>LINE Messages</h1>\n" + "".join(_bubble(m, fmt) for m in messages)
        single = html_dir / "messages.html"
        single.write_text(_render_page("LINE Messages", body), encoding="utf-8")
        index_body = (
            "<h1>LINE Message Export</h1>\n"
            f'<p>総件数: {len(messages):,}件 <a href="messages.html">すべて表示</a></p>'
        )

    index_path = html_dir / "index.html"
    index_path.write_text(_render_page("LINE Export Index", index_body), encoding="utf-8")
    logger.info("HTML written to %s (%d chats)", html_dir, len(index_rows) if split_by_chat else 1)
    return index_path
