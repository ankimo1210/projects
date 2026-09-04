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
import { collections, type Collection } from './types';

import {
  cameraPosition,
  exposure,
  fieldOfView,
  initialYaw,
  modelExtent,
  nodes,
  rendererInfo,
  studioUrl,
  type SceneProps as Props,
} from './render-contract';

/** Drop a cached load so a collection that failed to download can be retried. */
export function clearAsset(collection: Collection) {
  useGLTF.clear(collections[collection].asset);
}

function Sculpture({
  collection,
  wireframe,
  onReady,
  onGeometry,
  comparison,
}: Pick<Props, 'collection' | 'wireframe' | 'onReady' | 'comparison'> & {
  onGeometry: (meshes: number, triangles: number) => void;
}) {
  const comparisonMode = !!comparison;
  const { scene } = useGLTF(collections[collection].asset);
  // Cloning the graph is expensive on the 655-mesh cafe, so it must not depend
  // on wireframe: that switch only flips a flag on the materials below.
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
        if (copy instanceof THREE.MeshStandardMaterial)
          copy.envMapIntensity = comparisonMode
            ? 1
            : collection === 'core'
              ? 1.6
              : 0.65;
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
        modelExtent(collection, comparisonMode) /
        Math.max(size.x, size.y, size.z),
    };
  }, [scene, collection, comparisonMode]);

  // Reached through the mounted group, not through the memo, so that flipping
  // the flag stays a plain scene-graph mutation.
  const root = useRef<THREE.Group>(null);
  useEffect(() => {
    root.current?.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      const applied = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      for (const material of applied)
        if ('wireframe' in material)
          (material as THREE.MeshStandardMaterial).wireframe = wireframe;
    });
  }, [prepared, wireframe]);

  useEffect(() => {
    onGeometry(prepared.meshes, prepared.triangles);
    onReady();
    return () => prepared.materials.forEach((material) => material.dispose());
  }, [prepared, onGeometry, onReady]);

  return (
    <group ref={root} scale={prepared.scale}>
      <primitive object={prepared.object} />
    </group>
  );
}

function World(props: Props) {
  const viewportWidth = useThree((state) => state.viewport.width);
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);
  const gl = useThree((state) => state.gl);
  const gpu = useMemo(() => rendererInfo(gl.domElement), [gl]);
  const distance = Math.hypot(...cameraPosition(props.collection));
  const width = props.comparison
    ? (2 * Math.tan((fieldOfView * Math.PI) / 360) * distance * size.width) /
      size.height
    : viewportWidth;
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
    camera.position.set(...cameraPosition(props.collection));
    camera.lookAt(0, 0, 0);
    controls.current?.target.set(0, 0, 0);
    controls.current?.update();
    if (sculpture.current)
      sculpture.current.rotation.set(0, initialYaw(props.collection), 0);
  }, [props.resetKey, props.collection, camera]);

  useFrame(({ gl, clock }, delta) => {
    if (gl.getContext().isContextLost()) return;
    if (sculpture.current && props.comparison) {
      sculpture.current.rotation.set(
        props.comparison.pitch,
        initialYaw(props.collection) + props.comparison.yaw,
        0,
        'YXZ',
      );
    }
    if (sculpture.current && props.playing && !props.comparison)
      sculpture.current.rotation.y +=
        Math.min(delta, 0.05) * props.speed * 0.12;
    if (telemetry.current.meshes)
      props.onFrame?.({
        timestamp: performance.now(),
        width: gl.domElement.width,
        height: gl.domElement.height,
        renderer: gpu,
      });
    const metric = telemetry.current;
    metric.frames++;
    const elapsed = clock.elapsedTime - metric.start;
    // useFrame runs before the render that resets gl.info, so `calls` is the
    // previous frame's count. The panel labels it as such.
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
      {props.comparison ? (
        <Environment files={studioUrl} />
      ) : (
        <>
          <ambientLight intensity={props.collection === 'cafe' ? 0.65 : 0.5} />
          <directionalLight
            position={[4, 6, 4]}
            intensity={props.collection === 'cafe' ? 2.1 : 2.4}
            color={props.collection === 'cafe' ? '#ffe4b9' : '#efffed'}
          />
          <directionalLight
            position={[-4, 2, -3]}
            intensity={2}
            color="#b9d5cc"
          />
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
        </>
      )}
      <group scale={Math.min(1, width / 7.5)}>
        <group ref={sculpture}>
          <Sculpture
            collection={props.collection}
            wireframe={props.wireframe}
            comparison={props.comparison}
            onReady={props.onReady}
            onGeometry={onGeometry}
          />
        </group>
        {props.collection === 'core' && !props.comparison && (
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
      {!props.comparison && (
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
      )}
    </>
  );
}

function ContextObserver({ onError }: Pick<Props, 'onError'>) {
  const gl = useThree((state) => state.gl);
  useEffect(() => {
    const lost = () => onError?.();
    gl.domElement.addEventListener('webglcontextlost', lost);
    return () => gl.domElement.removeEventListener('webglcontextlost', lost);
  }, [gl, onError]);
  return null;
}

export default function OrbitScene(props: Props) {
  return (
    <Canvas
      camera={{ position: cameraPosition(props.collection), fov: fieldOfView }}
      dpr={props.comparison ? 1 : [1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      fallback={
        <p className="webgl-note">
          3D表示を利用できません。プレビュー画像を表示しています。
        </p>
      }
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        gl.toneMappingExposure = exposure;
      }}
    >
      <ContextObserver onError={props.onError} />
      <Suspense fallback={null}>
        <World {...props} />
      </Suspense>
    </Canvas>
  );
}
