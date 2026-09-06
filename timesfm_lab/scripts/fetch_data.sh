#!/usr/bin/env bash
# Download the public benchmark datasets into _data/ (about 440 MB unpacked).
# Sources: Monash TSF Repository (Zenodo) and ETDataset (GitHub).
set -euo pipefail
cd "$(dirname "$0")/../_data"

dl() {
  local id="$1" out="$2"
  [ -f "$out" ] && { echo "skip $out"; return; }
  local url
  url=$(curl -s "https://zenodo.org/api/records/$id" \
        | python -c "import json,sys;print(json.load(sys.stdin)['files'][0]['links']['self'])")
  echo "fetch $out"
  curl -sL -o "$out" "$url"
}

dl 4656140 electricity_hourly.zip
dl 4656132 traffic_hourly.zip
dl 4656144 solar_10_minutes.zip
dl 4654822 weather.zip
dl 4656058 saugeenday.zip
for f in *.zip; do unzip -o -q "$f"; done

for f in ETTh1 ETTh2; do
  [ -f "$f.csv" ] || curl -sL -o "$f.csv" \
    "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/$f.csv"
done
echo "done: $(du -sh . | cut -f1)"
