import { memo, useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { ALL_HAND_LABELS_GRID, GRID_SIZE } from '@gto/domain';
import {
  parsePreflopChartPack,
  type PreflopChart,
  type PreflopChartPack,
} from '@gto/packs';
import rawPack from '../../fixtures/packs/preflop-charts.dev.v1.json';

// Per-action fill colors. First non-fold action dominates the visual read:
// aggressive actions (R/3B/4B) hot, calls green, folds near-background.
const ACTION_COLORS: Record<string, string> = {
  R: '#e11d48',
  '3B': '#e11d48',
  '4B': '#e11d48',
  C: '#10b981',
  F: '#1e293b',
};

const CELL_GAP = 1;

interface CellProps {
  label: string;
  freqs: number[];
  actions: string[];
  size: number;
  selected: boolean;
  onPress: (index: number) => void;
  index: number;
}

// One grid cell: horizontal stacked segments proportional to action
// frequencies (u8 / 255). memo'd so chart switches only re-render cells
// whose freqs actually changed.
const HandCell = memo(function HandCell({
  label, freqs, actions, size, selected, onPress, index,
}: CellProps) {
  return (
    <Pressable
      onPress={() => onPress(index)}
      style={[{ width: size, height: size }, styles.cell, selected && styles.cellSelected]}
    >
      <View style={StyleSheet.absoluteFill}>
        <View style={styles.cellBar}>
          {actions.map((a, i) => {
            const f = (freqs[i] ?? 0) / 255;
            if (f === 0) return null;
            return (
              <View
                key={a}
                style={{ flex: f, backgroundColor: ACTION_COLORS[a] ?? '#64748b' }}
              />
            );
          })}
        </View>
      </View>
      <Text style={styles.cellText} allowFontScaling={false}>
        {label}
      </Text>
    </Pressable>
  );
});

function ChartGrid({ chart, cellSize }: { chart: PreflopChart; cellSize: number }) {
  const [selected, setSelected] = useState<number | null>(null);
  // Reset selection when switching charts so the detail row never shows a
  // hand/freq pairing from the previous chart.
  useEffect(() => setSelected(null), [chart.id]);

  const rows = useMemo(() => {
    const out = [];
    for (let r = 0; r < GRID_SIZE; r++) {
      out.push(ALL_HAND_LABELS_GRID.slice(r * GRID_SIZE, (r + 1) * GRID_SIZE));
    }
    return out;
  }, []);

  return (
    <View>
      <View style={styles.grid}>
        {rows.map((row, r) => (
          <View key={r} style={styles.gridRow}>
            {row.map((label, c) => {
              const index = r * GRID_SIZE + c;
              return (
                <HandCell
                  key={label}
                  index={index}
                  label={label}
                  freqs={chart.freqs[index]!}
                  actions={chart.actions}
                  size={cellSize}
                  selected={selected === index}
                  onPress={setSelected}
                />
              );
            })}
          </View>
        ))}
      </View>
      <View style={styles.detail}>
        {selected === null ? (
          <Text style={styles.detailHint}>タップでハンドの頻度を表示</Text>
        ) : (
          <Text style={styles.detailText}>
            {ALL_HAND_LABELS_GRID[selected]}{'   '}
            {chart.actions
              .map((a, i) => `${a} ${(((chart.freqs[selected]![i] ?? 0) / 255) * 100).toFixed(1)}%`)
              .join('   ')}
          </Text>
        )}
      </View>
    </View>
  );
}

export default function StudyScreen() {
  const pack: PreflopChartPack = useMemo(() => parsePreflopChartPack(rawPack), []);
  const [chartId, setChartId] = useState(pack.charts[0]!.id);
  const chart = pack.charts.find((c) => c.id === chartId)!;
  const { width } = useWindowDimensions();
  const cellSize = Math.floor((width - 16 - CELL_GAP * (GRID_SIZE - 1)) / GRID_SIZE);

  // Rough perf probe for the P1 render spike: JS time from chart-switch
  // commit to effect flush. Real measurement happens on a physical device.
  const switchStart = useRef(0);
  const [renderMs, setRenderMs] = useState<number | null>(null);
  useEffect(() => {
    if (switchStart.current > 0) {
      setRenderMs(performance.now() - switchStart.current);
      switchStart.current = 0;
    }
  }, [chartId]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Study — Preflop</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>CHART</Text>
        </View>
      </View>
      <Text style={styles.subtitle}>
        {pack.game} — hand-authored, validator-checked (not solver output)
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chips}>
        {pack.charts.map((c) => (
          <Pressable
            key={c.id}
            onPress={() => {
              switchStart.current = performance.now();
              setChartId(c.id);
            }}
            style={[styles.chip, c.id === chartId && styles.chipActive]}
          >
            <Text style={[styles.chipText, c.id === chartId && styles.chipTextActive]}>
              {c.title}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
      <ChartGrid chart={chart} cellSize={cellSize} />
      <View style={styles.legend}>
        {chart.actions.map((a) => (
          <View key={a} style={styles.legendItem}>
            <View style={[styles.legendSwatch, { backgroundColor: ACTION_COLORS[a] ?? '#64748b' }]} />
            <Text style={styles.legendText}>{a}</Text>
          </View>
        ))}
        {renderMs !== null && (
          <Text style={styles.perfText}>switch {renderMs.toFixed(1)} ms</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    paddingTop: 64,
    paddingHorizontal: 8,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    color: '#f8fafc',
    fontSize: 20,
    fontWeight: '700',
  },
  badge: {
    backgroundColor: '#334155',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  badgeText: {
    color: '#cbd5e1',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  subtitle: {
    color: '#64748b',
    fontSize: 11,
    marginTop: 2,
    marginBottom: 8,
  },
  chips: {
    flexGrow: 0,
    marginBottom: 8,
  },
  chip: {
    backgroundColor: '#1e293b',
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginRight: 6,
  },
  chipActive: {
    backgroundColor: '#0ea5e9',
  },
  chipText: {
    color: '#94a3b8',
    fontSize: 12,
  },
  chipTextActive: {
    color: '#f8fafc',
    fontWeight: '600',
  },
  grid: {
    gap: CELL_GAP,
  },
  gridRow: {
    flexDirection: 'row',
    gap: CELL_GAP,
  },
  cell: {
    borderRadius: 2,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cellSelected: {
    borderWidth: 1.5,
    borderColor: '#f8fafc',
  },
  cellBar: {
    flex: 1,
    flexDirection: 'row',
  },
  cellText: {
    color: '#f1f5f9',
    fontSize: 7,
    fontWeight: '600',
  },
  detail: {
    marginTop: 8,
    minHeight: 24,
    alignItems: 'center',
  },
  detailHint: {
    color: '#475569',
    fontSize: 12,
  },
  detailText: {
    color: '#e2e8f0',
    fontSize: 13,
    fontVariant: ['tabular-nums'],
  },
  legend: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginTop: 8,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendSwatch: {
    width: 10,
    height: 10,
    borderRadius: 2,
  },
  legendText: {
    color: '#94a3b8',
    fontSize: 11,
  },
  perfText: {
    color: '#475569',
    fontSize: 10,
    fontVariant: ['tabular-nums'],
  },
});
