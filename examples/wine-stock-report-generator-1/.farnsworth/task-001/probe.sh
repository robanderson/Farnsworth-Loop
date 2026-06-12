#!/usr/bin/env bash
# Probe harness for one applied candidate. Run from repo root.
set -u
R=/home/user/wsr-run/task-001-review
cd "$R" || exit 99
echo "============ TESTS (unittest discover) ============"
python3 -m unittest discover -s tests 2>&1 | tail -25
echo "tests-exit=${PIPESTATUS[0]}"
echo "============ compileall ============"
python3 -m compileall -q wine_stock_reporter 2>&1; echo "compile-exit=$?"
echo "============ no-interactive run ============"
rm -f r.md
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --output r.md 2>err.txt; echo "run-exit=$?"
echo "--- stderr ---"; cat err.txt
echo "--- report exists? lines: ---"; wc -l r.md 2>/dev/null
echo "--- section headers ---"; grep -n '^#' r.md 2>/dev/null
echo "============ piped EOF interactive ============"
rm -f stock-report.md
printf '' | python3 -m wine_stock_reporter examples/stock_sample.csv 2>eof_err.txt; echo "eof-exit=$?"
echo "--- eof stderr (last 5) ---"; tail -5 eof_err.txt
echo "--- default output written? ---"; ls -la stock-report.md 2>/dev/null
echo "============ --help ============"
python3 -m wine_stock_reporter --help >/dev/null 2>&1; echo "help-exit=$?"
echo "============ unknown flag ============"
python3 -m wine_stock_reporter examples/stock_sample.csv --bogus 2>/dev/null; echo "unknown-exit=$?"
echo "============ missing file ============"
python3 -m wine_stock_reporter /no/such/file.csv --no-interactive 2>mf.txt; echo "missing-exit=$?"
echo "--- stderr ---"; cat mf.txt
echo "============ missing column ============"
printf 'Type1,Item,Description,Lot,OnHand,Warehouse,Allocated,Pending,Units\nFinished Goods,1,FV 22 CHR EP NZ 750ml/12p,L1,10,WH,0,0,Cases\n' > /tmp/missingcol.csv
python3 -m wine_stock_reporter /tmp/missingcol.csv --no-interactive 2>mc.txt; echo "misscol-exit=$?"
echo "--- stderr ---"; cat mc.txt
echo "============ basis switch (OnHand) ============"
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --basis OnHand --output ron.md 2>/dev/null; echo "onhand-exit=$?"
echo "--- diff avail vs onhand report (count differing lines) ---"; diff r.md ron.md | grep -c '^[<>]'
echo "============ group-by none ============"
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --group-by none --output rnone.md 2>/dev/null; echo "none-exit=$?"
grep -c '^## Stock by' rnone.md 2>/dev/null
echo "============ no-dry-goods ============"
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --no-dry-goods --output rndg.md 2>/dev/null; echo "ndg-exit=$?"
echo "--- dry goods section present without flag? with flag? ---"
grep -c -i 'Dry Goods Summary' r.md 2>/dev/null
grep -c -i 'Dry Goods Summary' rndg.md 2>/dev/null
echo "============ low-stock-threshold sweep ============"
python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --low-stock-threshold 100 --output rlow.md 2>/dev/null
diff r.md rlow.md | grep -c '^[<>]'
echo "============ group-by pack_size / market / vintage / lot ============"
for g in vintage market pack_size lot; do
  python3 -m wine_stock_reporter examples/stock_sample.csv --no-interactive --group-by $g --output rg_$g.md 2>g_$g.txt; echo "$g-exit=$? "; grep -m1 '^## Stock by' rg_$g.md 2>/dev/null
done
echo "============ DONE ============"
