S=${ETF_PE_WORKDIR:-./work}
for d in 20250630 20250731 20250829 20250930 20251031 20251128 20251230 20260130 20260227 20260331 20260430 20260529 20260630 20260731 20260831; do
  for p in "251897/ishares-nikkei-225-etf:1329" "279438/fund:1475"; do
    path=${p%%:*}; code=${p##*:}
    out=$S/jp_hold/${code}_$d.csv
    [ -s $out ] && continue
    curl -sL -A 'Mozilla/5.0' -o $out "https://www.blackrock.com/jp/individual/ja/products/$path/1480664184455.ajax?fileType=csv&fileName=${code}_holdings&dataType=fund&asOfDate=$d"
    echo "$code $d $(wc -c < $out) $(head -c 40 $out | tr -d '\r\n')"
    sleep 1.5
  done
done
echo HOLD-DONE
