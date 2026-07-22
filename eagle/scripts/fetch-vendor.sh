#!/usr/bin/env bash
# Fetch and pin vendor repos. First run records SHAs into vendor/manifest.json;
# later runs verify the checkout matches the manifest.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor
MANIFEST=vendor/manifest.json

fetch() { # name url
  local name=$1 url=$2 dir=vendor/$1 sha
  if [[ ! -d $dir/.git ]]; then
    git clone --depth 1 "$url" "$dir"
  fi
  sha=$(git -C "$dir" rev-parse HEAD)
  if [[ -f $MANIFEST ]] && command -v jq >/dev/null; then
    want=$(jq -r ".\"$name\".sha // empty" "$MANIFEST")
    if [[ -n $want && $want != "$sha" ]]; then
      # Upstream HEAD moved past our pin; try to restore it. GitHub allows
      # fetching a full SHA directly even when it isn't a branch tip.
      git -C "$dir" fetch --depth 1 origin "$want" && git -C "$dir" checkout "$want" || true
      sha=$(git -C "$dir" rev-parse HEAD)
      if [[ $want != "$sha" ]]; then
        echo "ERROR: $name at $sha, manifest pins $want" >&2; exit 1
      fi
    fi
  fi
  echo "$name $sha"
}

A=$(fetch virtualagc https://github.com/virtualagc/virtualagc.git)
B=$(fetch Apollo-11 https://github.com/chrislgarry/Apollo-11.git)

if [[ ! -f $MANIFEST ]]; then
  jq -n --arg a "${A#* }" --arg b "${B#* }" '{
    "virtualagc": {url:"https://github.com/virtualagc/virtualagc.git", sha:$a},
    "Apollo-11":  {url:"https://github.com/chrislgarry/Apollo-11.git",  sha:$b}
  }' > "$MANIFEST"
  echo "wrote $MANIFEST"
fi
