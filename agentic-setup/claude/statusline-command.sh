#!/usr/bin/env bash
# Claude Code status line.
# Reads the JSON payload Claude Code pipes to stdin and prints a single line:
#   <model> | <dir> <branch> | <ctx bar> <used>/<window> (<pct>%) <auto-compact> | <effort> | $<cost>
#
# The context bar is measured against the *auto-compact window* (the point where
# the conversation gets summarized), not the raw model context window, since that
# is the limit a session actually runs into first.
#
# Auto-compact state is NOT part of the stdin payload, so it is resolved here by
# merging the settings chain (user -> project -> local -> managed) the same way
# Claude Code layers it, then clamping to the model's context window.

input=$(cat)

j() { echo "$input" | jq -r "$1 // empty"; }

# --- Fields -----------------------------------------------------------------
model=$(j '.model.display_name')
cur_dir=$(j '.workspace.current_dir')
total_tokens=$(j '.context_window.total_input_tokens')
ctx_size=$(j '.context_window.context_window_size')
used_pct=$(j '.context_window.used_percentage')
effort=$(j '.effort.level')
cost=$(j '.cost.total_cost_usd')

# --- Colors (mid-tone, readable on light and dark terminals; no dim) ---------
C_MODEL='\033[1;36m'   # bold cyan
C_DIR='\033[34m'       # blue
C_BRANCH='\033[35m'    # magenta
C_EFFORT='\033[33m'    # yellow
C_COST='\033[32m'      # green
C_AC_ON='\033[36m'     # cyan
C_AC_OFF='\033[31m'    # red
C_SEP='\033[90m'       # bright black (separators)
RESET='\033[0m'

fmt_tokens() {
  # Compact "12.3k" / "1.0M" formatting for a token count.
  awk -v n="$1" 'BEGIN {
    if (n >= 1000000)   { v = n/1000000; u = "M" }
    else if (n >= 1000) { v = n/1000;    u = "k" }
    else                { printf "%d", n; exit }
    if (v == int(v)) printf "%d%s", v, u; else printf "%.1f%s", v, u
  }'
}

pct_color() {
  # Green / yellow / red for a 0-100 usage percentage.
  p=${1%%.*}
  if   [ "${p:-0}" -ge 80 ] 2>/dev/null; then printf '%s' '\033[31m'
  elif [ "${p:-0}" -ge 50 ] 2>/dev/null; then printf '%s' '\033[33m'
  else                                        printf '%s' '\033[32m'
  fi
}

# --- Auto-compact settings --------------------------------------------------
# Later files win; managed settings sit last because policy overrides everything.
ac_enabled=""
ac_window=""
ac_files=()
for f in \
  "$HOME/.claude/settings.json" \
  "${cur_dir:-.}/.claude/settings.json" \
  "${cur_dir:-.}/.claude/settings.local.json" \
  "/etc/claude-code/managed-settings.json"
do
  [ -r "$f" ] && ac_files+=("$f")
done

if [ ${#ac_files[@]} -gt 0 ]; then
  ac_json=$(jq -s '
    reduce .[] as $s ({};
      . + ($s | {autoCompactEnabled, autoCompactWindow}
              | with_entries(select(.value != null))))
  ' "${ac_files[@]}" 2>/dev/null)
  ac_enabled=$(echo "$ac_json" | jq -r '.autoCompactEnabled // empty' 2>/dev/null)
  ac_window=$(echo "$ac_json" | jq -r '.autoCompactWindow // empty' 2>/dev/null)
fi

# Env var beats every settings file.
[ -n "$CLAUDE_CODE_AUTO_COMPACT_WINDOW" ] && ac_window="$CLAUDE_CODE_AUTO_COMPACT_WINDOW"
case "$DISABLE_AUTO_COMPACT$DISABLE_COMPACT" in
  ""|0|00) ;;
  *) ac_enabled="false" ;;
esac

# --- Model ------------------------------------------------------------------
out="${C_MODEL}${model:-?}${RESET}"

# --- Directory + git branch -------------------------------------------------
if [ -n "$cur_dir" ]; then
  out="${out} ${C_SEP}|${RESET} ${C_DIR}${cur_dir##*/}${RESET}"
  branch=$(git -C "$cur_dir" branch --show-current 2>/dev/null)
  if [ -n "$branch" ]; then
    dirty=""
    [ -n "$(git -C "$cur_dir" status --porcelain -uno 2>/dev/null | head -c1)" ] && dirty="*"
    out="${out} ${C_BRANCH}(${branch}${dirty})${RESET}"
  fi
fi

# --- Context window bar (measured against the auto-compact window) ----------
if [ -n "$total_tokens" ] && [ -n "$ctx_size" ]; then
  # Effective limit = auto-compact window clamped to the model window.
  limit=$ctx_size
  if [ "$ac_enabled" != "false" ] && [ -n "$ac_window" ]; then
    [ "$ac_window" -lt "$ctx_size" ] 2>/dev/null && limit=$ac_window
  fi

  used_fmt=$(fmt_tokens "$total_tokens")
  size_fmt=$(fmt_tokens "$limit")

  if [ "$limit" = "$ctx_size" ] && [ -n "$used_pct" ]; then
    pct=${used_pct%%.*}
  else
    pct=$(awk -v t="$total_tokens" -v s="$limit" 'BEGIN{printf "%d", (s>0)?100*t/s:0}')
  fi
  [ -z "$pct" ] && pct=0

  if   [ "$pct" -ge 80 ]; then bar_color='\033[31m'   # red
  elif [ "$pct" -ge 50 ]; then bar_color='\033[33m'   # yellow
  else                         bar_color='\033[32m'   # green
  fi

  filled=$(( (pct + 5) / 10 ))
  [ "$filled" -gt 10 ] && filled=10
  [ "$filled" -lt 0 ] && filled=0
  bar=""
  for i in $(seq 1 10); do
    if [ "$i" -le "$filled" ]; then bar="${bar}\xe2\x96\x88"; else bar="${bar}\xe2\x96\x91"; fi
  done

  out="${out} ${C_SEP}|${RESET} ${bar_color}${bar}${RESET} ${used_fmt}/${size_fmt} (${pct}%)"

  # Auto-compact marker: cyan "AC" when on, red "AC:off" when disabled.
  if [ "$ac_enabled" = "false" ]; then
    out="${out} ${C_AC_OFF}\xe2\x9f\xb3 AC:off${RESET}"
  else
    ac_tag="AC"
    [ "$limit" != "$ctx_size" ] && ac_tag="AC@${size_fmt}"
    out="${out} ${C_AC_ON}\xe2\x9f\xb3 ${ac_tag}${RESET}"
  fi
fi

# --- Rate limits (5h / 7d subscription budget) ------------------------------
rl_5h=$(j '.rate_limits.five_hour.used_percentage')
rl_7d=$(j '.rate_limits.seven_day.used_percentage')
if [ -n "$rl_5h" ] || [ -n "$rl_7d" ]; then
  rl=""
  [ -n "$rl_5h" ] && rl="$(pct_color "$rl_5h")5h ${rl_5h%%.*}%${RESET}"
  if [ -n "$rl_7d" ]; then
    [ -n "$rl" ] && rl="${rl} ${C_SEP}\xc2\xb7${RESET} "
    rl="${rl}$(pct_color "$rl_7d")7d ${rl_7d%%.*}%${RESET}"
  fi
  # U+23F1 has emoji presentation, so terminals draw it two cells wide while the
  # layout counts one — the trailing space keeps it off the following text.
  out="${out} ${C_SEP}|${RESET} ${C_SEP}\xe2\x8f\xb1${RESET} ${rl}"
fi

# --- Effort -----------------------------------------------------------------
[ -n "$effort" ] && out="${out} ${C_SEP}|${RESET} ${C_EFFORT}\xe2\x9a\xa1${effort}${RESET}"

# --- Session cost -----------------------------------------------------------
if [ -n "$cost" ]; then
  cost_fmt=$(awk -v c="$cost" 'BEGIN{ if (c+0 > 0) printf "%.2f", c }')
  [ -n "$cost_fmt" ] && out="${out} ${C_SEP}|${RESET} ${C_COST}\$${cost_fmt}${RESET}"
fi

printf "%b" "$out"
