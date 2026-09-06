"use client"

import { Html, Line, OrbitControls } from "@react-three/drei"
import { Canvas, useThree } from "@react-three/fiber"
import { Component, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { BufferAttribute, BufferGeometry, DoubleSide } from "three"
import type { RatesMeshData } from "@/lib/rates/mesh"

export type MeshMode = "surface" | "wireframe" | "points"

function DataMesh({ data, mode }: { data: RatesMeshData; mode: MeshMode }) {
  const geometry = useMemo(() => {
    const next = new BufferGeometry()
    next.setAttribute("position", new BufferAttribute(data.positions, 3))
    next.setAttribute("color", new BufferAttribute(data.colors, 3))
    if (mode !== "points") next.setIndex(new BufferAttribute(data.indices, 1))
    next.computeVertexNormals()
    return next
  }, [data, mode])
  useEffect(() => () => geometry.dispose(), [geometry])

  if (mode === "points") return (
    <points geometry={geometry} dispose={null}>
      <pointsMaterial vertexColors size={0.075} sizeAttenuation />
    </points>
  )
  return (
    <mesh geometry={geometry} dispose={null}>
      <meshStandardMaterial
        vertexColors side={DoubleSide} wireframe={mode === "wireframe"}
        roughness={0.36} metalness={0.25}
      />
    </mesh>
  )
}

function Zoom({ value }: { value: number }) {
  const { camera, invalidate } = useThree()
  useEffect(() => {
    camera.zoom = value
    camera.updateProjectionMatrix()
    invalidate()
  }, [camera, invalidate, value])
  return null
}

function AxisLabel({ position, children }: { position: [number, number, number]; children: ReactNode }) {
  return (
    <Html position={position} center style={{ pointerEvents: "none" }}>
      <span style={{ font: "10px monospace", color: "#a8adb4", whiteSpace: "nowrap" }}>
        {children}
      </span>
    </Html>
  )
}

function Axes({ dates }: { dates: [string, string] }) {
  const floor = -3
  return (
    <group>
      <gridHelper args={[9, 18, "#384035", "#1c2421"]} position={[0, floor, 0]} />
      <Line points={[[-3.8, floor, -2.75], [-3.8, floor, 2.75], [3.8, floor, 2.75]]} color="#738270" lineWidth={1} />
      <Line points={[[-3.8, floor, 2.75], [-3.8, 3, 2.75]]} color="#738270" lineWidth={1} />
      {[2, 10, 20, 30, 40].map(year => (
        <AxisLabel key={year} position={[(year - 21) / 5, floor - 0.2, 3.05]}>{year}Y</AxisLabel>
      ))}
      {[0, 1, 2, 3].map(value => (
        <AxisLabel key={value} position={[-4.25, (value - 1.25) * 1.7, 2.75]}>{value}%</AxisLabel>
      ))}
      <AxisLabel position={[4.9, floor, 2.75]}>{dates[0].slice(5)}</AxisLabel>
      <AxisLabel position={[4.9, floor, -2.75]}>{dates[1].slice(5)}</AxisLabel>
    </group>
  )
}

function Fallback() {
  return <div role="status" style={{ padding: 32, color: "#b7bdc4" }}>この環境では3D表示を利用できません。下のカーブとCSVでデータを確認できます。</div>
}

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <Fallback /> : this.props.children }
}

export function RatesMeshScene({ data, mode, autoRotate, zoom, resetKey, dates }: {
  data: RatesMeshData
  mode: MeshMode
  autoRotate: boolean
  zoom: number
  resetKey: number
  dates: [string, string]
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(true)
  const [activeTab, setActiveTab] = useState(true)
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting))
    if (ref.current) observer.observe(ref.current)
    function updateVisibility() { setActiveTab(!document.hidden) }
    updateVisibility()
    document.addEventListener("visibilitychange", updateVisibility)
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", updateVisibility) }
  }, [])
  const animated = autoRotate && visible && activeTab
  return (
    <div ref={ref} data-testid="meshy-canvas" style={{ height: "100%", width: "100%", touchAction: "pan-y" }}>
      <SceneBoundary>
        <Canvas
          key={resetKey}
          camera={{ position: [8, 5.8, 10], fov: 48 }}
          dpr={[1, 1.5]}
          frameloop={animated ? "always" : "demand"}
          gl={{ antialias: true, alpha: true }}
          fallback={<Fallback />}
        >
          <ambientLight intensity={1.2} />
          <directionalLight position={[3, 8, 5]} intensity={3} />
          <directionalLight position={[-5, 3, -4]} intensity={2} color="#c2ff4a" />
          <DataMesh data={data} mode={mode} />
          <Axes dates={dates} />
          <OrbitControls
            makeDefault target={[0, -0.9, 0]} enablePan={false} enableZoom={false}
            enableDamping autoRotate={animated} autoRotateSpeed={0.65}
            minPolarAngle={0.3} maxPolarAngle={Math.PI * 0.49}
          />
          <Zoom value={zoom} />
        </Canvas>
      </SceneBoundary>
    </div>
  )
}
