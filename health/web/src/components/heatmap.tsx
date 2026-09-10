import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { DataState } from "./data-state";
export function Heatmap({
  rows,
  title,
  coverage = false,
}: {
  rows: { date: string; value: number | null }[];
  title: string;
  coverage?: boolean;
}) {
  const max = rows.reduce((m, r) => Math.max(m, r.value ?? 0), 1);
  return (
    <Card className="full-span">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          {coverage
            ? "歩数の記録あり／欠損。未装着と未同期は区別できません。"
            : "日ごとの歩数。セルに触れると日付と値を確認できます。"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length ? (
          <>
            <div className="calendar-scroll">
              <div
                className="calendar-grid"
                style={{
                  gridTemplateColumns: `repeat(${Math.ceil((rows.length + ((new Date(rows[0].date).getUTCDay() + 6) % 7)) / 7)}, 15px)`,
                }}
              >
                {Array.from(
                  { length: (new Date(rows[0].date).getUTCDay() + 6) % 7 },
                  (_, i) => (
                    <span key={`space${i}`} />
                  ),
                )}
                {rows.map((r) => (
                  <span
                    tabIndex={0}
                    className={`calendar-cell ${r.value === null ? "missing" : ""}`}
                    key={r.date}
                    style={
                      r.value === null
                        ? {}
                        : {
                            background: `var(--sequential-${coverage ? 9 : Math.min(13, 1 + Math.floor((r.value / max) * 12))})`,
                          }
                    }
                    title={`${r.date}: ${r.value === null ? "欠損" : coverage ? "記録あり" : r.value.toLocaleString() + "歩"}`}
                    aria-label={`${r.date} ${r.value === null ? "欠損" : coverage ? "記録あり" : r.value + "歩"}`}
                  />
                ))}
              </div>
            </div>
            <div className="chart-note">
              {rows[0].date} — {rows.at(-1)?.date} ・破線は欠損
              {!coverage && " ・淡色から濃色へ歩数が増加"}
            </div>
          </>
        ) : (
          <DataState />
        )}
      </CardContent>
    </Card>
  );
}
