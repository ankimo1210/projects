'use client';

import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import {
  Environment,
  Html,
  Lightformer,
  OrbitControls,
  useGLTF,
} from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsType } from 'three-stdlib';
import {
  collections,
  type Collection,
  type Panel,
  type SceneStats,
} from './types';

type Props = {
  collection: Collection;
  playing: boolean;
  speed: number;
  wireframe: boolean;
  resetKey: number;
  onReady: () => void;
  onStats: (stats: SceneStats) => void;
  onPanel: (panel: Panel) => void;
};

function Sculpture({
  collection,
  wireframe,
  onReady,
  onGeometry,
}: Pick<Props, 'collection' | 'wireframe' | 'onReady'> & {
  onGeometry: (meshes: number, triangles: number) => void;
}) {
  const { scene } = useGLTF(collections[collection].asset);
  const prepared = useMemo(() => {
    const object = scene.clone(true);
    const materials: THREE.Material[] = [];
    let meshes = 0;
    let triangles = 0;
    object.traverse((child) => {
      if ((child as THREE.Light).isLight) child.visible = false;
      if (!(child as THREE.Mesh).isMesh) return;
      const mesh = child as THREE.Mesh;
      meshes++;
      triangles +=
        (mesh.geometry.index?.count ??
          mesh.geometry.attributes.position.count) / 3;
      const originals = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      const copies = originals.map((material) => {
        const copy = material.clone();
        if ('wireframe' in copy)
          (copy as THREE.MeshStandardMaterial).wireframe = wireframe;
        if (copy instanceof THREE.MeshStandardMaterial)
          copy.envMapIntensity = collection === 'core' ? 1.6 : 0.65;
        materials.push(copy);
        return copy;
      });
      mesh.material = Array.isArray(mesh.material) ? copies : copies[0];
    });
    const bounds = new THREE.Box3().setFromObject(object);
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    object.position.sub(center);
    return {
      object,
      materials,
      meshes,
      triangles,
      scale:
        (collection === 'core' ? 5.2 : 5) / Math.max(size.x, size.y, size.z),
    };
  }, [scene, collection, wireframe]);

  useEffect(() => {
    onGeometry(prepared.meshes, prepared.triangles);
    onReady();
    return () => prepared.materials.forEach((material) => material.dispose());
  }, [prepared, onGeometry, onReady]);

  return (
    <group scale={prepared.scale}>
      <primitive object={prepared.object} />
    </group>
  );
}

const nodes: {
  panel: Panel;
  position: [number, number, number];
  number: string;
}[] = [
  { panel: 'code', position: [-2.4, 0.85, 0.1], number: '01' },
  { panel: 'data', position: [2.5, 0.4, 0.1], number: '02' },
  { panel: 'research', position: [0.8, -1.85, 0.9], number: '03' },
];

function World(props: Props) {
  const viewportWidth = useThree((state) => state.viewport.width);
  const camera = useThree((state) => state.camera);
  const sculpture = useRef<THREE.Group>(null);
  const controls = useRef<OrbitControlsType>(null);
  const telemetry = useRef({ start: 0, frames: 0, meshes: 0, triangles: 0 });
  const onGeometry = useMemo(
    () => (meshes: number, triangles: number) => {
      telemetry.current.meshes = meshes;
      telemetry.current.triangles = triangles;
    },
    [],
  );

  useEffect(() => {
    camera.position.set(0, props.collection === 'cafe' ? 2.8 : 1.25, 7.8);
    controls.current?.target.set(0, 0, 0);
    controls.current?.update();
    if (sculpture.current)
      sculpture.current.rotation.set(
        0,
        props.collection === 'cafe' ? -0.5 : 0,
        0,
      );
  }, [props.resetKey, props.collection, camera]);

  useFrame(({ gl, clock }, delta) => {
    if (sculpture.current && props.playing)
      sculpture.current.rotation.y +=
        Math.min(delta, 0.05) * props.speed * 0.12;
    const metric = telemetry.current;
    metric.frames++;
    const elapsed = clock.elapsedTime - metric.start;
    if (elapsed >= 1 && metric.meshes) {
      props.onStats({
        meshes: metric.meshes,
        triangles: Math.round(metric.triangles),
        fps: Math.round(metric.frames / elapsed),
        calls: gl.info.render.calls,
      });
      metric.start = clock.elapsedTime;
      metric.frames = 0;
    }
  });

  return (
    <>
      <ambientLight intensity={props.collection === 'cafe' ? 0.65 : 0.5} />
      <directionalLight
        position={[4, 6, 4]}
        intensity={props.collection === 'cafe' ? 2.1 : 2.4}
        color={props.collection === 'cafe' ? '#ffe4b9' : '#efffed'}
      />
      <directionalLight position={[-4, 2, -3]} intensity={2} color="#b9d5cc" />
      <Environment resolution={128} frames={1}>
        <Lightformer
          intensity={5}
          position={[0, 5, -3]}
          rotation={[Math.PI / 2, 0, 0]}
          scale={[10, 2, 1]}
        />
        <Lightformer
          intensity={4}
          position={[-4, 1, 3]}
          rotation={[0, Math.PI / 2, 0]}
          scale={[2, 7, 1]}
        />
        <Lightformer
          intensity={3}
          position={[4, 3, 2]}
          rotation={[0, -Math.PI / 2, 0]}
          scale={[3, 6, 1]}
        />
        <Lightformer
          intensity={1.5}
          color="#caff65"
          position={[0, -4, 1]}
          rotation={[-Math.PI / 2, 0, 0]}
          scale={[8, 3, 1]}
        />
      </Environment>
      <group scale={Math.min(1, viewportWidth / 7.5)}>
        <group ref={sculpture}>
          <Sculpture
            collection={props.collection}
            wireframe={props.wireframe}
            onReady={props.onReady}
            onGeometry={onGeometry}
          />
        </group>
        {props.collection === 'core' && (
          <>
            <mesh rotation={[Math.PI / 2.6, 0.15, 0.05]}>
              <torusGeometry args={[2.65, 0.004, 5, 180]} />
              <meshBasicMaterial color="#6e806d" transparent opacity={0.48} />
            </mesh>
            {nodes.map(({ panel, position, number }) => (
              <group key={panel} position={position}>
                <mesh
                  onClick={(event) => {
                    event.stopPropagation();
                    props.onPanel(panel);
                  }}
                >
                  <sphereGeometry args={[0.07, 16, 16]} />
                  <meshBasicMaterial color="#ceff75" />
                </mesh>
                <Html
                  center
                  distanceFactor={8}
                  position={[0, -0.23, 0]}
                  zIndexRange={[5, 0]}
                >
                  <button
                    className="spatial-node"
                    onClick={() => props.onPanel(panel)}
                    aria-label={`${panel.toUpperCase()}を開く`}
                  >
                    <span>{number}</span>
                    {panel.toUpperCase()}
                  </button>
                </Html>
              </group>
            ))}
          </>
        )}
      </group>
      <OrbitControls
        ref={controls}
        makeDefault
        enablePan={false}
        enableZoom={false}
        enableDamping
        dampingFactor={0.07}
        rotateSpeed={0.55}
        minPolarAngle={0.35}
        maxPolarAngle={Math.PI * 0.8}
      />
    </>
  );
}

export default function OrbitScene(props: Props) {
  return (
    <Canvas
      camera={{ position: [0, 1.25, 7.8], fov: 43 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      fallback={
        <p className="webgl-note">
          3D表示を利用できません。プレビュー画像を表示しています。
        </p>
      }
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        gl.toneMappingExposure = 1.2;
      }}
    >
      <Suspense fallback={null}>
        <World {...props} />
      </Suspense>
    </Canvas>
  );
}
