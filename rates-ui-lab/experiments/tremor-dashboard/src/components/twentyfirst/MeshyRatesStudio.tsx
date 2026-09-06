// UI composition inspired by meshyflix.com. All geometry comes from local JGB fixtures.
"use client"

import base from "@/data/rates/jgb-demo.json"
import missing from "@/data/rates/jgb-demo-missing.json"
import negative from "@/data/rates/jgb-demo-negative.json"
import flat from "@/data/rates/jgb-demo-flat.json"
import { formatBp, formatYield, validateDataset } from "@/lib/rates/metrics"
import { buildRatesMesh, ratesCsv } from "@/lib/rates/mesh"
import type { RatesDataset } from "@/lib/rates/types"
import { buildRatesViewModel } from "@/lib/rates/view-model"
import { useReducedMotion } from "motion/react"
import Link from "next/link"
import { useMemo, useState } from "react"
import { RatesMeshScene, type MeshMode } from "./RatesMeshScene"
import styles from "./MeshyRatesStudio.module.css"

const specimens = [
  { id: "base", name: "Baseline", label: "標準カーブ", note: "いつものJGBカーブを、奥行きとともに。", data: validateDataset(base) },
  { id: "missing", name: "Missing observations", label: "欠損カーブ", note: "欠けた観測点は、面の隙間として残す。", data: validateDataset(missing) },
  { id: "negative", name: "Below zero", label: "負金利カーブ", note: "短い年限がゼロを下回る形を見る。", data: validateDataset(negative) },
  { id: "flat", name: "Flat across tenors", label: "フラットカーブ", note: "同じ日の年限間スプレッドはゼロ。", data: validateDataset(flat) },
] as const

function CurveThumbnail({ data }: { data: RatesDataset }) {
  let connected = false
  const path = data.snapshots.at(-1)!.points.map(point => {
    if (point.yieldPct === null) { connected = false; return "" }
    const command = connected ? "L" : "M"
    connected = true
    return `${command}${12 + ((point.tenorYears - 2) / 38) * 226},${83 - ((point.yieldPct + 0.5) / 3.5) * 68}`
  }).join(" ")
  return (
    <svg viewBox="0 0 250 100" aria-hidden="true" className={styles.thumbnail}>
      {[20, 45, 70, 95].map(y => <path key={y} d={`M0 ${y} H250`} stroke="currentColor" opacity="0.1" />)}
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      {data.snapshots.at(-1)!.points.filter(point => point.yieldPct !== null).map(point => (
        <circle key={point.tenorYears} cx={12 + ((point.tenorYears - 2) / 38) * 226} cy={83 - ((point.yieldPct! + 0.5) / 3.5) * 68} r="3" fill="currentColor" />
      ))}
    </svg>
  )
}

function downloadDataset(data: RatesDataset, id: string) {
  const url = URL.createObjectURL(new Blob([ratesCsv(data)], { type: "text/csv;charset=utf-8" }))
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `jgb-${id}-${data.snapshots.length}-observations.csv`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function MeshyRatesStudio() {
  const [selectedId, setSelectedId] = useState<string>("base")
  const [mode, setMode] = useState<MeshMode>("surface")
  const [rotate, setRotate] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [resetKey, setResetKey] = useState(0)
  const reducedMotion = useReducedMotion() === true
  const selected = specimens.find(item => item.id === selectedId)!
  const dataset = selected.data
  const mesh = useMemo(() => buildRatesMesh(dataset), [dataset])
  const firstDate = dataset.snapshots[0].date
  const lastDate = dataset.snapshots.at(-1)!.date
  const model = useMemo(() => buildRatesViewModel(dataset, lastDate, dataset.snapshots.at(-2)!.date), [dataset, lastDate])
  const tenYear = model.kpis.find(kpi => kpi.id === "tenY")!
  const spread = model.kpis.find(kpi => kpi.id === "twoTen")!

  function resetView() { setZoom(1); setRotate(false); setResetKey(key => key + 1) }

  return (
    <div className={styles.shell} lang="ja">
      <header className={styles.header}>
        <a href="#mesh-top" className={styles.brand}><span className={styles.mark} aria-hidden="true">◇</span> Rates / Mesh Studio</a>
        <nav aria-label="Mesh Studio ナビゲーション" className={styles.nav}>
          <a href="#mesh-collection">Collection</a>
          <Link href="/rates-21st?view=prism">Prism</Link>
          <Link href="/rates-21st?view=massive&rows=1000000">1M data lab ↗</Link>
        </nav>
      </header>

      <section className={styles.hero} id="mesh-top">
        <div className={styles.intro}>
          <p className={styles.eyebrow}><span className={styles.dot} /> Meshyflix inspired / 03</p>
          <h1>See the curve.<br />Explore the mesh.</h1>
          <p className={styles.lead}>数字の並びから、<br />金利の形が見えてくる。</p>
          <div className={styles.brief}>
            <p className={styles.mono}>DATA BRIEF</p>
            <p>JGBの60観測日、2Yから40Yまでの7年限。日付・年限・利回りを、ひとつの立体へ。</p>
            <div className={styles.tags}><span>SYNTHETIC</span><span>JPY / JGB</span><span>{selected.name}</span></div>
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={() => downloadDataset(dataset, selected.id)}>Download CSV <span aria-hidden="true">↓</span></button>
            <a href="https://meshyflix.com/" target="_blank" rel="noreferrer" className={styles.source}>Source website ↗</a>
          </div>
        </div>

        <div className={styles.preview}>
          <div className={styles.previewTop}><span className={styles.mono}>LIVE GEOMETRY</span><span className={styles.status}>LOCAL / DEMO</span></div>
          <div className={styles.canvasWrap}>
            <RatesMeshScene data={mesh} mode={mode} autoRotate={rotate && !reducedMotion} zoom={zoom} resetKey={resetKey} dates={[firstDate, lastDate]} />
          </div>
          <div className={styles.viewTools}>
            <div role="group" aria-label="メッシュの表示方法" className={styles.modes}>
              {([['surface', 'Surface'], ['wireframe', 'Wireframe'], ['points', 'Points']] as const).map(([value, label]) => (
                <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)}>{label}</button>
              ))}
            </div>
            <div className={styles.cameraTools}>
              <button type="button" aria-label="縮小" disabled={zoom <= 0.7} onClick={() => setZoom(value => Math.max(0.7, value - 0.15))}>−</button>
              <button type="button" aria-label="拡大" disabled={zoom >= 1.75} onClick={() => setZoom(value => Math.min(1.75, value + 0.15))}>+</button>
              <button type="button" aria-label="視点をリセット" onClick={resetView}>↺</button>
              <button type="button" aria-label="自動回転" aria-pressed={rotate && !reducedMotion} disabled={reducedMotion} onClick={() => setRotate(value => !value)}>Auto</button>
            </div>
          </div>
          <p className={styles.hint}>ドラッグで回転 · ＋／−で拡大縮小{reducedMotion ? " · 自動回転はOS設定により停止" : ""}</p>
        </div>
      </section>

      <dl className={styles.metrics} aria-live="polite">
        <div><dt>10Y YIELD</dt><dd data-testid="meshy-ten-year">{formatYield(tenYear.value)}</dd></div>
        <div><dt>2S10S SPREAD</dt><dd data-testid="meshy-spread">{formatBp(spread.value)}</dd></div>
        <div><dt>VERTICES / 有効観測点</dt><dd data-testid="meshy-vertices">{mesh.vertexCount}</dd></div>
        <div><dt>TRIANGLES / 描画面</dt><dd data-testid="meshy-triangles">{mesh.triangleCount}</dd></div>
        <div><dt>OBSERVATION WINDOW</dt><dd className={styles.smallValue}>{firstDate}<br />→ {lastDate}</dd></div>
      </dl>

      <section id="mesh-collection" className={styles.collection}>
        <div className={styles.collectionHeading}>
          <div><p className={styles.eyebrow}>THE CURVE COLLECTION</p><h2>Same lens. Different shapes.</h2></div>
          <p>ケースを選んで、立体と指標を切り替える。<br />同じ軸スケールで違いを比較できます。</p>
        </div>
        <div className={styles.cards}>
          {specimens.map((item, index) => (
            <button key={item.id} type="button" aria-label={`${item.label}を表示`} aria-pressed={selected.id === item.id} className={styles.card} onClick={() => setSelectedId(item.id)}>
              <span className={styles.cardTop}><span>0{index + 1} / {item.label}</span><span aria-hidden="true">{selected.id === item.id ? "●" : "↗"}</span></span>
              <CurveThumbnail data={item.data} />
              <strong>{item.name}</strong><span className={styles.cardNote}>{item.note}</span>
            </button>
          ))}
        </div>
      </section>

      <section className={styles.manifest} aria-label="表示データの定義">
        <div><p className={styles.eyebrow}>WHAT THE MESH SHOWS</p><h2>A surface you can inspect.</h2><p>各頂点はひとつの観測値。面は隣接する4点が揃う場所だけを接続します。欠損をゼロで埋めたり、年限の間隔を均等にしたりしません。</p></div>
        <dl><div><dt>X / TENOR</dt><dd>2, 5, 7, 10, 20, 30, 40 years</dd></div><div><dt>Y / YIELD</dt><dd>利回り % · 全ケースで共通スケール</dd></div><div><dt>Z / DATE</dt><dd>暦日で配置 · 土日の間隔を保持</dd></div><div><dt>MISSING</dt><dd>{mesh.missingCount} points · 接する面は非表示</dd></div></dl>
      </section>
      <footer className={styles.footer}><span>RATES UI LAB / MESHYFLIX STUDY</span><span>合成データ · ローカルでのUI比較</span><Link href="/rates-21st">Back to overview ↗</Link></footer>
    </div>
  )
}
