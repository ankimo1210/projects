'use client';

import { useEffect, useRef, useState } from 'react';
import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Vector3, Quaternion } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { CreateSphere } from '@babylonjs/core/Meshes/Builders/sphereBuilder';
import { CreateTorus } from '@babylonjs/core/Meshes/Builders/torusBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import { HDRCubeTexture } from '@babylonjs/core/Materials/Textures/hdrCubeTexture';
import { ImageProcessingConfiguration } from '@babylonjs/core/Materials/imageProcessingConfiguration';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { SceneInstrumentation } from '@babylonjs/core/Instrumentation/sceneInstrumentation';
import '@babylonjs/loaders/glTF/2.0';
import '@babylonjs/loaders/glTF/glTFFileLoader';
import { collections } from './types';
import {
  cameraPosition,
  exposure,
  fieldOfView,
  initialYaw,
  modelExtent,
  nodes,
  rendererInfo,
  studioUrl,
  type SceneProps,
} from './render-contract';

export default function BabylonScene(props: SceneProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const labels = useRef<(HTMLButtonElement | null)[]>([]);
  const latest = useRef(props);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => {
    latest.current = props;
  });
  const comparisonMode = !!props.comparison;

  useEffect(() => {
    if (!canvas.current) return;
    let disposed = false;
    let engine: Engine | undefined;
    let observer: ResizeObserver | undefined;
    let scene: Scene | undefined;
    const fail = (cause: unknown) => {
      if (!disposed) {
        latest.current.onError?.();
        setError(cause instanceof Error ? cause : new Error('3D load failed'));
      }
    };
    try {
      const element = canvas.current;
      engine = new Engine(element, true, {
        alpha: true,
        powerPreference: 'high-performance',
        preserveDrawingBuffer: false,
      });
      const renderer = engine;
      renderer.onContextLostObservable.add(() =>
        fail(new Error('WebGL context lost')),
      );
      scene = new Scene(renderer);
      const world = scene;
      world.useRightHandedSystem = true;
      world.clearColor = new Color4(0, 0, 0, 0);
      world.imageProcessingConfiguration.exposure = exposure;
      world.imageProcessingConfiguration.toneMappingEnabled = true;
      world.imageProcessingConfiguration.toneMappingType =
        ImageProcessingConfiguration.TONEMAPPING_ACES;
      world.environmentIntensity = comparisonMode
        ? 1
        : props.collection === 'core'
          ? 1.6
          : 0.65;
      const camera = new ArcRotateCamera(
        'orbit-camera',
        Math.PI / 2,
        1.4,
        8,
        Vector3.Zero(),
        world,
      );
      camera.fov = (fieldOfView * Math.PI) / 180;
      camera.minZ = 0.1;
      camera.maxZ = 1000;
      camera.lowerBetaLimit = 0.35;
      camera.upperBetaLimit = Math.PI * 0.8;
      camera.panningSensibility = 0;
      camera.inertia = 0.93;
      camera.inputs.removeByType('ArcRotateCameraMouseWheelInput');
      if (!comparisonMode) camera.attachControl(element, false);
      const position = Vector3.FromArray(cameraPosition(props.collection));
      camera.setPosition(position);
      const layout = new TransformNode('viewport-scale', world);
      const sculpture = new TransformNode('sculpture-rotation', world);
      sculpture.parent = layout;
      const scaled = new TransformNode('asset-scale', world);
      scaled.parent = sculpture;
      const centered = new TransformNode('asset-center', world);
      centered.parent = scaled;
      const resize = () => {
        const rect = element.getBoundingClientRect();
        const dpr = comparisonMode
          ? 1
          : Math.min(1.5, Math.max(1, window.devicePixelRatio));
        renderer.setSize(
          Math.floor(rect.width * dpr),
          Math.floor(rect.height * dpr),
        );
        const width =
          (2 * Math.tan(camera.fov / 2) * position.length() * rect.width) /
          Math.max(1, rect.height);
        layout.scaling.setAll(Math.min(1, width / 7.5));
      };
      observer = new ResizeObserver(resize);
      observer.observe(element);
      resize();

      if (!comparisonMode) {
        const ambient = new HemisphericLight('ambient', Vector3.Up(), world);
        ambient.intensity = props.collection === 'cafe' ? 0.65 : 0.5;
        ambient.groundColor = Color3.White();
        ambient.specular = Color3.Black();
        const key = new DirectionalLight(
          'key',
          new Vector3(-4, -6, -4).normalize(),
          world,
        );
        key.intensity = props.collection === 'cafe' ? 2.1 : 2.4;
        key.diffuse = Color3.FromHexString(
          props.collection === 'cafe' ? '#ffe4b9' : '#efffed',
        ).toLinearSpace();
        const fill = new DirectionalLight(
          'fill',
          new Vector3(4, -2, 3).normalize(),
          world,
        );
        fill.intensity = 2;
        fill.diffuse = Color3.FromHexString('#b9d5cc').toLinearSpace();
      }
      const labelPositions: Vector3[] = [];
      if (!comparisonMode && props.collection === 'core') {
        const unlit = (name: string, hex: string, alpha = 1) => {
          const material = new StandardMaterial(name, world);
          material.disableLighting = true;
          material.emissiveColor = Color3.FromHexString(hex).toLinearSpace();
          material.alpha = alpha;
          return material;
        };
        const ring = CreateTorus(
          'orbit-line',
          { diameter: 5.3, thickness: 0.008, tessellation: 180 },
          world,
        );
        ring.parent = layout;
        ring.rotationQuaternion = Quaternion.FromEulerAngles(
          Math.PI / 2.6 - Math.PI / 2,
          0.15,
          0.05,
        );
        ring.material = unlit('orbit-line-material', '#6e806d', 0.48);
        const material = unlit('node-material', '#ceff75');
        nodes.forEach(({ position: point }, index) => {
          const dot = CreateSphere(
            `node-${index}`,
            { diameter: 0.14, segments: 16 },
            world,
          );
          dot.position.copyFromFloats(...point);
          dot.parent = layout;
          dot.material = material;
          labelPositions.push(new Vector3(point[0], point[1] - 0.23, point[2]));
        });
      }

      const environment = new Promise<void>((resolve, reject) => {
        world.environmentTexture = new HDRCubeTexture(
          studioUrl,
          world,
          128,
          false,
          true,
          false,
          true,
          resolve,
          (_message, cause) => reject(cause ?? new Error('HDR load failed')),
        );
      });
      const instrumentation = new SceneInstrumentation(world);
      const gpu = rendererInfo(element);
      let reset = -1;
      let last = 0;
      let metricStart = 0;
      let frames = 0;
      let wireframe: boolean | undefined;
      Promise.all([
        LoadAssetContainerAsync(collections[props.collection].asset, world),
        environment,
      ])
        .then(async ([container]) => {
          if (disposed) {
            container.dispose();
            return;
          }
          container.addAllToScene();
          for (const light of container.lights.slice()) light.dispose();
          for (const importedCamera of container.cameras.slice())
            importedCamera.dispose();
          world.activeCamera = camera;
          const meshes = container.meshes.filter(
            (mesh) => mesh.getTotalVertices() > 0,
          );
          let minimum = new Vector3(Infinity, Infinity, Infinity);
          let maximum = new Vector3(-Infinity, -Infinity, -Infinity);
          for (const mesh of meshes) {
            mesh.computeWorldMatrix(true);
            const bounds = mesh.getBoundingInfo().boundingBox;
            minimum = Vector3.Minimize(minimum, bounds.minimumWorld);
            maximum = Vector3.Maximize(maximum, bounds.maximumWorld);
          }
          const size = maximum.subtract(minimum);
          centered.position.copyFrom(minimum.add(maximum).scale(-0.5));
          scaled.scaling.setAll(
            modelExtent(props.collection, comparisonMode) /
              Math.max(size.x, size.y, size.z),
          );
          for (const node of [
            ...container.meshes,
            ...container.transformNodes,
          ]) {
            if (!node.parent) node.parent = centered;
          }
          const triangles = Math.round(
            meshes.reduce((sum, mesh) => sum + mesh.getTotalIndices() / 3, 0),
          );
          await world.whenReadyAsync();
          if (disposed) return;
          latest.current.onReady();
          renderer.runRenderLoop(() => {
            if (disposed) return;
            const current = latest.current;
            const now = performance.now();
            const delta = last ? Math.min((now - last) / 1000, 0.05) : 0;
            last = now;
            if (current.resetKey !== reset) {
              reset = current.resetKey;
              camera.setTarget(Vector3.Zero());
              camera.setPosition(position);
              camera.inertialAlphaOffset = 0;
              camera.inertialBetaOffset = 0;
              sculpture.rotation.set(0, initialYaw(props.collection), 0);
            }
            if (current.comparison) {
              sculpture.rotation.set(
                current.comparison.pitch,
                initialYaw(props.collection) + current.comparison.yaw,
                0,
              );
            } else if (current.playing) {
              sculpture.rotation.y += delta * current.speed * 0.12;
            }
            if (current.wireframe !== wireframe) {
              wireframe = current.wireframe;
              for (const material of container.materials) {
                if (
                  material instanceof PBRMaterial ||
                  material instanceof StandardMaterial
                )
                  material.wireframe = wireframe;
              }
            }
            current.onFrame?.({
              timestamp: now,
              width: renderer.getRenderWidth(),
              height: renderer.getRenderHeight(),
              renderer: gpu,
            });
            world.render();
            const viewport = camera.viewport.toGlobal(
              element.clientWidth,
              element.clientHeight,
            );
            labelPositions.forEach((point, index) => {
              const label = labels.current[index];
              if (!label) return;
              const projected = Vector3.Project(
                point,
                layout.getWorldMatrix(),
                world.getTransformMatrix(),
                viewport,
              );
              label.style.transform = `translate(-50%, -50%) translate(${projected.x}px, ${projected.y}px)`;
              label.style.visibility =
                projected.z > 0 && projected.z < 1 ? 'visible' : 'hidden';
            });
            if (!metricStart) metricStart = now;
            frames++;
            if (now - metricStart >= 1000) {
              current.onStats({
                meshes: meshes.length,
                triangles,
                fps: Math.round((frames * 1000) / (now - metricStart)),
                calls: instrumentation.drawCallsCounter.current,
              });
              frames = 0;
              metricStart = now;
            }
          });
        })
        .catch(fail);
    } catch (cause) {
      fail(cause);
    }
    return () => {
      disposed = true;
      observer?.disconnect();
      engine?.stopRenderLoop();
      scene?.dispose();
      engine?.dispose();
    };
  }, [props.collection, comparisonMode]);

  if (error) throw error;
  return (
    <div className="babylon-surface">
      <canvas ref={canvas} aria-label="Babylon.jsによる3D表示" />
      {!comparisonMode &&
        props.collection === 'core' &&
        nodes.map(({ panel, number }, index) => (
          <button
            key={panel}
            ref={(element) => {
              labels.current[index] = element;
            }}
            className="spatial-node babylon-node"
            onClick={() => props.onPanel(panel)}
            aria-label={`${panel.toUpperCase()}を開く`}
          >
            <span>{number}</span>
            {panel.toUpperCase()}
          </button>
        ))}
    </div>
  );
}
