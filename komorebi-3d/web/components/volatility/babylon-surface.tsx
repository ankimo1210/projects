'use client';

import { useEffect, useMemo, useRef } from 'react';
import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Matrix, Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { VertexData } from '@babylonjs/core/Meshes/mesh.vertexData';
import { CreateLineSystem } from '@babylonjs/core/Meshes/Builders/linesBuilder';
import { CreateSphere } from '@babylonjs/core/Meshes/Builders/sphereBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { PointerEventTypes } from '@babylonjs/core/Events/pointerEvents';
import '@babylonjs/core/Culling/ray';
import {
  axes,
  cameraPosition,
  frame,
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

export default function BabylonSurface(props: SurfaceProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const labels = useRef<(HTMLSpanElement | null)[]>([]);
  const latest = useRef(props);
  const update = useRef<((value: SurfaceProps) => void) | null>(null);
  const axis = useMemo(() => axes(props.grid), [props.grid]);
  useEffect(() => {
    latest.current = props;
    update.current?.(props);
  });

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    let engine: Engine | undefined;
    let resize: ResizeObserver | undefined;
    try {
      engine = new Engine(element, true, {
        alpha: true,
        preserveDrawingBuffer: false,
      });
      const renderer = engine;
      renderer.onContextLostObservable.add(() => latest.current.onError());
      const scene = new Scene(renderer);
      scene.useRightHandedSystem = true;
      scene.clearColor = new Color4(0, 0, 0, 0);
      scene.imageProcessingConfiguration.toneMappingEnabled = false;
      scene.imageProcessingConfiguration.isEnabled = false;
      const camera = new ArcRotateCamera(
        'surface-camera',
        0,
        1,
        12,
        Vector3.FromArray(frame.center),
        scene,
      );
      camera.fov = (frame.fov * Math.PI) / 180;
      camera.minZ = 0.1;
      camera.maxZ = 100;
      camera.inertia = 0;
      camera.panningSensibility = 0;
      camera.lowerRadiusLimit = 7;
      camera.upperRadiusLimit = 22;
      camera.lowerBetaLimit = Math.PI / 2 - 1.4;
      camera.upperBetaLimit = Math.PI / 2 - 0.12;
      camera.wheelDeltaPercentage = 0.025;
      camera.attachControl(element, true);
      const material = new StandardMaterial('surface-color', scene);
      material.disableLighting = true;
      material.emissiveColor = Color3.White();
      material.backFaceCulling = false;
      const surface = new Mesh('surface', scene);
      surface.material = material;
      surface.useVertexColors = true;
      surface.enablePointerMoveEvents = true;
      const dot = CreateSphere(
        'selected-point',
        { diameter: 0.13, segments: 16 },
        scene,
      );
      const dotMaterial = new StandardMaterial('selected-color', scene);
      dotMaterial.disableLighting = true;
      dotMaterial.emissiveColor = Color3.FromHexString(ink.selected);
      dot.material = dotMaterial;
      dot.isPickable = false;
      let baseLines: Mesh[] = [];
      let selection: Mesh | undefined;
      let previousGrid = '';
      let previousSelection = '';
      let previousWire: boolean | undefined;
      let labelPositions: Vec3[] = [];
      const lines = (
        name: string,
        paths: Vec3[][],
        color: string,
        alpha = 1,
      ) => {
        const mesh = CreateLineSystem(
          name,
          {
            useVertexAlpha: true,
            lines: paths.map((path) => path.map((v) => Vector3.FromArray(v))),
          },
          scene,
        );
        mesh.color = Color3.FromHexString(color);
        mesh.alpha = alpha;
        mesh.isPickable = false;
        return mesh;
      };
      update.current = (value) => {
        camera.setPosition(Vector3.FromArray(cameraPosition(value.view)));
        camera.getViewMatrix(true);
        if (previousGrid !== value.grid.id) {
          const data = meshData(value.grid);
          const vertices = new VertexData();
          vertices.positions = data.positions;
          vertices.indices = data.indices;
          vertices.colors = data.colors.flatMap((channel, index) =>
            index % 3 === 2 ? [channel, 1] : [channel],
          );
          vertices.normals = [];
          VertexData.ComputeNormals(
            data.positions,
            data.indices,
            vertices.normals,
          );
          vertices.applyToMesh(surface, true);
        }
        if (
          previousGrid !== value.grid.id ||
          previousWire !== value.wireframe
        ) {
          baseLines.forEach((mesh) => mesh.dispose(false, true));
          const axis = axes(value.grid);
          labelPositions = axis.labels.map((label) => label.position);
          baseLines = [
            lines('axes', axis.lines, ink.grid, 0.55),
            ...(value.wireframe
              ? [lines('grid', meshLines(value.grid), '#91c5b4', 0.8)]
              : []),
          ];
          // Keep the transparent surface pickable in wireframe mode.
          material.alpha = value.wireframe ? 0 : 1;
        }
        const selectionKey = `${value.grid.id}:${value.selected.row}:${value.selected.column}`;
        if (selectionKey !== previousSelection) {
          selection?.dispose(false, true);
          selection = lines(
            'slices',
            selectedLines(value.grid, value.selected),
            ink.selected,
          );
          const position = positionOf(
            value.grid,
            value.selected.row,
            value.selected.column,
          );
          dot.position.set(position[0], position[1] + 0.045, position[2]);
          previousSelection = selectionKey;
        }
        if (previousGrid !== value.grid.id) value.onReady(value.grid.id);
        previousGrid = value.grid.id;
        previousWire = value.wireframe;
      };
      update.current(latest.current);
      let pointerStart = [0, 0];
      scene.onPointerObservable.add((info) => {
        if (info.type === PointerEventTypes.POINTERDOWN)
          pointerStart = [info.event.clientX, info.event.clientY];
        const point =
          info.pickInfo?.pickedMesh === surface
            ? info.pickInfo.pickedPoint
            : null;
        if (info.type === PointerEventTypes.POINTERMOVE && !info.event.buttons)
          latest.current.onHover(
            point ? pointAtWorld(latest.current.grid, point.x, point.z) : null,
          );
        if (
          info.type === PointerEventTypes.POINTERUP &&
          point &&
          Math.hypot(
            info.event.clientX - pointerStart[0],
            info.event.clientY - pointerStart[1],
          ) < 4
        )
          latest.current.onSelect(
            pointAtWorld(latest.current.grid, point.x, point.z),
          );
      });
      resize = new ResizeObserver(() => renderer.resize());
      resize.observe(element);
      renderer.resize();
      renderer.runRenderLoop(() => {
        // Matrix notifications also fire on resize and external camera writes.
        // Publish only motion originating in this camera's input controller.
        const userMotion =
          camera.inertialAlphaOffset !== 0 ||
          camera.inertialBetaOffset !== 0 ||
          camera.inertialRadiusOffset !== 0;
        scene.render();
        if (userMotion)
          latest.current.onView(
            viewFromPosition([
              camera.position.x,
              camera.position.y,
              camera.position.z,
            ]),
          );
        const viewport = camera.viewport.toGlobal(
          renderer.getRenderWidth(),
          renderer.getRenderHeight(),
        );
        labelPositions.forEach((position, index) => {
          const label = labels.current[index];
          if (!label) return;
          const screen = Vector3.Project(
            Vector3.FromArray(position),
            Matrix.IdentityReadOnly,
            scene.getTransformMatrix(),
            viewport,
          );
          label.style.left = `${screen.x}px`;
          label.style.top = `${screen.y}px`;
          label.style.visibility =
            screen.z > 0 && screen.z < 1 ? 'visible' : 'hidden';
        });
      });
    } catch {
      latest.current.onError();
    }
    return () => {
      update.current = null;
      resize?.disconnect();
      engine?.dispose();
    };
  }, []);

  return (
    <div className="vol-native-scene">
      <canvas
        ref={canvas}
        aria-label="Babylon.js ボラティリティーサーフェス"
        onPointerLeave={() => props.onHover(null)}
      />
      <div className="vol-axis-overlay">
        {axis.labels.map((label, index) => (
          <span
            key={index}
            ref={(element) => {
              labels.current[index] = element;
            }}
            className={`vol-axis-label ${label.title ? 'is-title' : ''}`}
          >
            {label.text}
          </span>
        ))}
      </div>
    </div>
  );
}
