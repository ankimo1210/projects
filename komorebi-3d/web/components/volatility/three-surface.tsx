'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsType } from 'three-stdlib';
import * as THREE from 'three';
import {
  axes,
  cameraPosition,
  frame,
  initialView,
  ink,
  meshData,
  meshLines,
  pointAtWorld,
  positionOf,
  selectedLines,
  viewFromPosition,
  type SurfaceProps,
  type Vec3,
} from './contract';

function Segments({
  lines,
  color,
  opacity = 1,
}: {
  lines: Vec3[][];
  color: string;
  opacity?: number;
}) {
  const geometry = useMemo(() => {
    const positions = lines.flatMap((line) =>
      line.slice(1).flatMap((end, index) => [...line[index], ...end]),
    );
    const result = new THREE.BufferGeometry();
    result.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(positions, 3),
    );
    return result;
  }, [lines]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        toneMapped={false}
      />
    </lineSegments>
  );
}

function World(props: SurfaceProps) {
  const {
    onError,
    onReady,
    grid: { id: gridId },
  } = props;
  const camera = useThree((state) => state.camera);
  const gl = useThree((state) => state.gl);
  const controls = useRef<OrbitControlsType>(null);
  const applying = useRef(false);
  const geometry = useMemo(() => {
    const data = meshData(props.grid);
    const colors: number[] = [];
    for (let index = 0; index < data.colors.length; index += 3) {
      const color = new THREE.Color().setRGB(
        data.colors[index],
        data.colors[index + 1],
        data.colors[index + 2],
        THREE.SRGBColorSpace,
      );
      colors.push(color.r, color.g, color.b);
    }
    const result = new THREE.BufferGeometry();
    result.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(data.positions, 3),
    );
    result.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    result.setIndex(data.indices);
    result.computeVertexNormals();
    return result;
  }, [props.grid]);
  const axis = useMemo(() => axes(props.grid), [props.grid]);
  const gridLines = useMemo(() => meshLines(props.grid), [props.grid]);
  const slices = useMemo(
    () => selectedLines(props.grid, props.selected),
    [props.grid, props.selected],
  );
  const marker = positionOf(
    props.grid,
    props.selected.row,
    props.selected.column,
  );
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => {
    applying.current = true;
    camera.position.set(...cameraPosition(props.view));
    camera.lookAt(...frame.center);
    controls.current?.target.set(...frame.center);
    controls.current?.update();
    applying.current = false;
  }, [props.view, camera]);
  useEffect(() => {
    const lost = () => onError();
    gl.domElement.addEventListener('webglcontextlost', lost);
    return () => gl.domElement.removeEventListener('webglcontextlost', lost);
  }, [gl, onError]);
  useEffect(() => {
    onReady(gridId);
  }, [gridId, onReady]);

  return (
    <>
      <Segments lines={axis.lines} color={ink.grid} opacity={0.55} />
      <mesh
        geometry={geometry}
        onPointerMove={(event) => {
          if (!event.buttons)
            props.onHover(
              pointAtWorld(props.grid, event.point.x, event.point.z),
            );
        }}
        onPointerOut={() => props.onHover(null)}
        onClick={(event) => {
          if (event.delta < 4)
            props.onSelect(
              pointAtWorld(props.grid, event.point.x, event.point.z),
            );
        }}
      >
        <meshBasicMaterial
          vertexColors
          side={THREE.DoubleSide}
          toneMapped={false}
          colorWrite={!props.wireframe}
          depthWrite={!props.wireframe}
          polygonOffset
          polygonOffsetFactor={1}
          polygonOffsetUnits={1}
        />
      </mesh>
      {props.wireframe && (
        <Segments lines={gridLines} color="#91c5b4" opacity={0.8} />
      )}
      <Segments lines={slices} color={ink.selected} />
      <mesh position={[marker[0], marker[1] + 0.045, marker[2]]}>
        <sphereGeometry args={[0.065, 16, 12]} />
        <meshBasicMaterial color={ink.selected} toneMapped={false} />
      </mesh>
      {axis.labels.map((label, index) => (
        <Html key={index} position={label.position} center zIndexRange={[4, 0]}>
          <span className={`vol-axis-label ${label.title ? 'is-title' : ''}`}>
            {label.text}
          </span>
        </Html>
      ))}
      <OrbitControls
        ref={controls}
        enablePan={false}
        enableDamping={false}
        target={frame.center}
        minDistance={7}
        maxDistance={22}
        minPolarAngle={Math.PI / 2 - 1.4}
        maxPolarAngle={Math.PI / 2 - 0.12}
        rotateSpeed={0.6}
        zoomSpeed={0.7}
        onChange={() => {
          if (!applying.current)
            props.onView(
              viewFromPosition([
                camera.position.x,
                camera.position.y,
                camera.position.z,
              ]),
            );
        }}
      />
    </>
  );
}

export default function ThreeSurface(props: SurfaceProps) {
  const { onError } = props;
  const [available] = useState(() => {
    try {
      const probe = document.createElement('canvas').getContext('webgl2');
      probe?.getExtension('WEBGL_lose_context')?.loseContext();
      return !!probe;
    } catch {
      return false;
    }
  });
  useEffect(() => {
    if (!available) onError();
  }, [available, onError]);
  if (!available) return null;
  return (
    <Canvas
      dpr={1}
      camera={{
        position: cameraPosition(initialView),
        fov: frame.fov,
        near: 0.1,
        far: 100,
      }}
      gl={{ alpha: true, antialias: true }}
      onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
      fallback={
        <p className="vol-unavailable">
          WebGLを利用できません。下の断面で数値を確認できます。
        </p>
      }
    >
      <World {...props} />
    </Canvas>
  );
}
