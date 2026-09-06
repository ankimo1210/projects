// Original rates-specific implementation based on BEVEL UI's public Prism Hero
// concept (MIT). Registry source code is not bundled; see docs/sources.md.
"use client"

import { formatBp, formatYield } from "@/lib/rates/metrics"
import type { buildRatesViewModel } from "@/lib/rates/view-model"
import {
  Environment,
  Lightformer,
  MeshTransmissionMaterial,
  Stars,
} from "@react-three/drei"
import { Canvas, useFrame } from "@react-three/fiber"
import { motion, useReducedMotion } from "motion/react"
import Link from "next/link"
import {
  Component,
  type ErrorInfo,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import {
  CanvasTexture,
  Mesh,
  SRGBColorSpace,
  type Texture,
} from "three"

type RatesView = ReturnType<typeof buildRatesViewModel>

interface QualityTier {
  name: "low" | "medium" | "high"
  dpr: [number, number]
  samples: number
  resolution: number
}

function qualityForWidth(width: number): QualityTier {
  if (width < 640) {
    return { name: "low", dpr: [1, 1.2], samples: 3, resolution: 256 }
  }
  if (width < 1280) {
    return { name: "medium", dpr: [1, 1.45], samples: 5, resolution: 384 }
  }
  return { name: "high", dpr: [1, 1.7], samples: 6, resolution: 512 }
}

function useQualityTier() {
  const [quality, setQuality] = useState<QualityTier>(() =>
    qualityForWidth(typeof window === "undefined" ? 1280 : window.innerWidth),
  )
  useEffect(() => {
    function update() {
      setQuality(qualityForWidth(window.innerWidth))
    }
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [])
  return quality
}

function createHeadlineTexture(): Texture {
  const canvas = document.createElement("canvas")
  canvas.width = 2048
  canvas.height = 768
  const context = canvas.getContext("2d")
  if (!context) throw new Error("Canvas 2D is unavailable")

  context.clearRect(0, 0, canvas.width, canvas.height)
  context.fillStyle = "#ede8df"
  context.textAlign = "center"
  context.textBaseline = "middle"
  context.font = "170px Georgia, 'Times New Roman', serif"
  context.fillText("JGB REFRACTION", canvas.width / 2, canvas.height / 2)

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.needsUpdate = true
  return texture
}

function HeadlinePlane() {
  const texture = useMemo(createHeadlineTexture, [])
  useEffect(() => () => texture.dispose(), [texture])

  return (
    <mesh position={[0, 0, -2.5]} scale={[9.6, 3.6, 1]}>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial map={texture} transparent toneMapped={false} />
    </mesh>
  )
}

function RefractivePrism({
  quality,
  reducedMotion,
  scrollProgress,
}: {
  quality: QualityTier
  reducedMotion: boolean
  scrollProgress: React.MutableRefObject<number>
}) {
  const prism = useRef<Mesh>(null)

  useFrame((state, delta) => {
    if (!prism.current || reducedMotion) return
    const targetY = scrollProgress.current * Math.PI * 1.25 + state.pointer.x * 0.18
    const targetX = 0.24 + scrollProgress.current * 0.45 - state.pointer.y * 0.12
    prism.current.rotation.y += (targetY - prism.current.rotation.y) * Math.min(1, delta * 2.4)
    prism.current.rotation.x += (targetX - prism.current.rotation.x) * Math.min(1, delta * 2.4)
    prism.current.rotation.z += delta * 0.045
  })

  return (
    <group position={[0, 0.12, 0]}>
      <mesh ref={prism} rotation={[0.24, 0.4, -0.08]}>
        <dodecahedronGeometry args={[1.62, 0]} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={0.45}
          samples={quality.samples}
          resolution={quality.resolution}
          transmission={1}
          thickness={0.75}
          roughness={0.08}
          ior={1.32}
          chromaticAberration={0.1}
          anisotropy={0.12}
          distortion={0.18}
          distortionScale={0.35}
          temporalDistortion={reducedMotion ? 0 : 0.06}
          color="#f2eee7"
        />
      </mesh>
    </group>
  )
}

function PrismScene({
  quality,
  reducedMotion,
  scrollProgress,
}: {
  quality: QualityTier
  reducedMotion: boolean
  scrollProgress: React.MutableRefObject<number>
}) {
  return (
    <>
      <color attach="background" args={["#08080b"]} />
      <ambientLight intensity={0.8} />
      <directionalLight position={[4, 5, 5]} intensity={2.2} color="#fff5df" />
      <pointLight position={[-4, -2, 3]} intensity={10} color="#5577ff" />
      <pointLight position={[4, 0, 2]} intensity={8} color="#ff8f5d" />
      <Environment resolution={128}>
        <Lightformer
          form="rect"
          intensity={3.5}
          color="#fff4df"
          position={[0, 5, -4]}
          rotation={[Math.PI / 2, 0, 0]}
          scale={[8, 8, 1]}
        />
        <Lightformer
          form="rect"
          intensity={3}
          color="#6f8cff"
          position={[-5, 0, 2]}
          rotation={[0, Math.PI / 2, 0]}
          scale={[7, 2, 1]}
        />
        <Lightformer
          form="rect"
          intensity={2.5}
          color="#ff9a66"
          position={[5, -1, 1]}
          rotation={[0, -Math.PI / 2, 0]}
          scale={[6, 2, 1]}
        />
      </Environment>
      <Stars
        radius={24}
        depth={12}
        count={220}
        factor={1.2}
        saturation={0.5}
        fade
        speed={reducedMotion ? 0 : 0.15}
      />
      <HeadlinePlane />
      <RefractivePrism
        quality={quality}
        reducedMotion={reducedMotion}
        scrollProgress={scrollProgress}
      />
    </>
  )
}

function StaticPrism() {
  return (
    <div className="absolute inset-0 flex items-center justify-center" role="img" aria-label="静止したプリズム">
      <div
        className="h-64 w-64 rotate-12 bg-gradient-to-br from-cyan-200/80 via-white/20 to-orange-300/70 shadow-[0_0_100px_rgba(122,152,255,0.25)]"
        style={{ clipPath: "polygon(24% 0, 82% 12%, 100% 54%, 68% 100%, 12% 84%, 0 32%)" }}
      />
    </div>
  )
}

class WebGLErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Prism WebGL fallback", error, info.componentStack)
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

export function PrismRatesHero({ model }: { model: RatesView }) {
  const heroRef = useRef<HTMLElement>(null)
  const scrollProgress = useRef(0)
  const prefersReducedMotion = useReducedMotion() === true
  const quality = useQualityTier()
  const [isVisible, setIsVisible] = useState(true)
  const tenYear = model.kpis.find((kpi) => kpi.id === "tenY")!
  const twoTen = model.kpis.find((kpi) => kpi.id === "twoTen")!
  const fiveThirty = model.kpis.find((kpi) => kpi.id === "fiveThirty")!

  useEffect(() => {
    const hero = heroRef.current
    if (!hero) return
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry?.isIntersecting ?? false),
      { rootMargin: "120px" },
    )
    observer.observe(hero)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (prefersReducedMotion) {
      scrollProgress.current = 0.32
      return
    }
    let frame = 0
    function update() {
      frame = 0
      const hero = heroRef.current
      if (!hero) return
      const bounds = hero.getBoundingClientRect()
      const distance = Math.max(1, bounds.height - window.innerHeight)
      scrollProgress.current = Math.min(1, Math.max(0, -bounds.top / distance))
    }
    function onScroll() {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => {
      window.removeEventListener("scroll", onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [prefersReducedMotion])

  return (
    <div className="-m-4 bg-[#08080b] text-[#ede8df] sm:-mx-6 sm:-mb-10 sm:-mt-10 lg:-mx-10 lg:-mt-7" lang="ja">
      <section
        ref={heroRef}
        className="relative h-[125vh] min-h-[760px]"
        data-testid="prism-stage"
        data-motion={prefersReducedMotion ? "static" : "animated"}
        data-quality={quality.name}
      >
        <div className="sticky top-0 h-screen min-h-[680px] overflow-hidden">
          <WebGLErrorBoundary fallback={<StaticPrism />}>
            <Canvas
              className="!absolute inset-0"
              camera={{ position: [0, 0, 7], fov: 35 }}
              dpr={quality.dpr}
              frameloop={isVisible && !prefersReducedMotion ? "always" : "demand"}
              gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
              fallback={<StaticPrism />}
            >
              <PrismScene
                quality={quality}
                reducedMotion={prefersReducedMotion}
                scrollProgress={scrollProgress}
              />
            </Canvas>
          </WebGLErrorBoundary>

          <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(8,8,11,0.12)_55%,rgba(8,8,11,0.88)_100%)]" />
          <div className="absolute inset-0 z-20 flex flex-col p-5 sm:p-8 lg:p-10">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <motion.div
                initial={prefersReducedMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7 }}
              >
                <p className="font-mono text-[10px] uppercase tracking-[0.34em] text-amber-300">
                  Rates UI Lab / BEVEL UI study
                </p>
                <h1 className="mt-3 text-2xl font-medium tracking-tight text-[#ede8df] sm:text-3xl">
                  JGB Refraction
                </h1>
              </motion.div>
              <nav className="pointer-events-auto flex flex-wrap items-center gap-2" aria-label="Prism表示ナビゲーション">
                <span className="rounded-full border border-white/25 bg-white/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-white">
                  Prism
                </span>
                <Link href="/rates-21st" className="rounded-full border border-white/15 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-white/65 transition hover:bg-white/10 hover:text-white">
                  Overview
                </Link>
                <Link href="/rates-21st?view=massive&rows=1000000" className="rounded-full border border-white/15 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-white/65 transition hover:bg-white/10 hover:text-white">
                  Massive
                </Link>
              </nav>
            </div>

            <div
              className="mt-4 flex gap-4 font-mono text-[9px] uppercase tracking-wider text-white/60 sm:hidden"
              data-testid="prism-mobile-metrics"
            >
              <span>10Y {formatYield(tenYear.value)}</span>
              <span>2s10s {formatBp(twoTen.value)}</span>
            </div>

            <div className="mt-auto flex flex-col items-center pb-28 text-center sm:pb-12">
              <motion.div
                initial={prefersReducedMotion ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25, duration: 0.8 }}
                className="max-w-xl"
              >
                <p className="text-sm leading-6 text-[#ede8df]/75 sm:text-base">
                  10Yの水準とカーブの広がりを、実データではない屈折表現として可視化。スクロールとポインターでプリズムが動きます。
                </p>
                <div
                  className="pointer-events-auto mt-6 flex flex-wrap justify-center gap-3"
                  data-testid="prism-actions"
                >
                  <Link href="/rates-21st" className="inline-flex h-11 items-center rounded-full bg-[#ede8df] px-6 font-mono text-[10px] uppercase tracking-[0.18em] text-[#08080b] transition-transform hover:-translate-y-0.5">
                    Open dashboard
                  </Link>
                  <a
                    href="https://21st.dev/@bevelui/components/prism-hero"
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Prism Hero on 21st.dev"
                    className="inline-flex h-11 items-center rounded-full border border-white/25 px-6 font-mono text-[10px] uppercase tracking-[0.18em] text-[#ede8df] transition-colors hover:bg-white/10"
                  >
                    Source pattern
                  </a>
                </div>
              </motion.div>
            </div>

            <div
              className="absolute bottom-5 left-5 right-5 hidden flex-wrap items-end justify-between gap-4 sm:bottom-8 sm:left-8 sm:right-8 sm:flex lg:left-10 lg:right-10"
              data-testid="prism-bottom-meta"
            >
              <div className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-[9px] uppercase tracking-[0.2em] text-white/45">
                <span>Procedural geometry</span>
                <span>Real transmission</span>
                <span>Adaptive quality · {quality.name}</span>
              </div>
              <div className="flex gap-5 border-t border-white/15 pt-3 font-mono text-[10px] tabular-nums text-white/65">
                <span data-testid="prism-ten-year">{formatYield(tenYear.value)}</span>
                <span>2s10s {formatBp(twoTen.value)}</span>
                <span className="hidden sm:inline">5s30s {formatBp(fiveThirty.value)}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 px-5 py-14 sm:px-8 lg:px-10" aria-label="Prism実験の説明">
        <div className="grid gap-8 lg:grid-cols-[1fr_2fr]">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-amber-300">What this tests</p>
            <h2 className="mt-4 text-2xl font-medium tracking-tight">Visual impact versus dashboard utility</h2>
          </div>
          <div className="grid gap-px overflow-hidden rounded-2xl bg-white/10 sm:grid-cols-3">
            {[
              ["Headline", "JGB 10Yを中心に置いた導入画面としての印象"],
              ["Rendering", "端末別DPR・画面外停止・reduced motion"],
              ["Boundary", "分析値の読取りはOverviewとMassive dataへ分離"],
            ].map(([label, value]) => (
              <div key={label} className="bg-[#0d0d11] p-5">
                <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40">{label}</p>
                <p className="mt-3 text-sm leading-6 text-white/75">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
