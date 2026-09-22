"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

import type { Action, Archetype, Damage } from "@/lib/types";
import { modelUrl } from "@/lib/archetypes";
import { toWorld, zoneDef, type VehicleBounds } from "@/lib/zones";

export const ACTION_COLORS: Record<Action, string> = {
  replace: "#ef4444",
  repair: "#f59e0b",
  assess: "#38bdf8",
};

const SEVERITY_OPACITY: Record<string, number> = {
  leicht: 0.25,
  mittel: 0.4,
  schwer: 0.6,
};

const DEFAULT_BOUNDS: VehicleBounds = {
  minX: -2.35,
  maxX: 2.35,
  minY: -1.35,
  maxY: 1.35,
  maxZ: 1.6,
};

function VehicleModel({
  archetype,
  onBounds,
}: {
  archetype: Archetype;
  onBounds: (b: VehicleBounds) => void;
}) {
  const gltf = useGLTF(modelUrl(archetype));
  const scene = useMemo(() => gltf.scene.clone(), [gltf]);

  useEffect(() => {
    const box = new THREE.Box3().setFromObject(scene);
    onBounds({
      minX: box.min.x,
      maxX: box.max.x,
      minY: box.min.y,
      maxY: box.max.y,
      maxZ: box.max.z,
    });
  }, [scene, onBounds]);

  return <primitive object={scene} />;
}

interface MarkerProps {
  damage: Damage;
  archetype: Archetype;
  bounds: VehicleBounds;
  severity: string | null;
  selected: boolean;
  onSelect: () => void;
}

function ZoneMarker({
  damage,
  archetype,
  bounds,
  severity,
  selected,
  onSelect,
}: MarkerProps) {
  const def = zoneDef(archetype, damage.zone);
  const color = ACTION_COLORS[damage.action] ?? "#38bdf8";
  const opacity = SEVERITY_OPACITY[severity ?? ""] ?? 0.35;

  const world = useMemo(
    () => (def ? toWorld(def, bounds, archetype) : null),
    [def, bounds, archetype],
  );

  if (!world) return null;

  const markerColor = new THREE.Color(color);
  const glow = selected ? 1.2 : 0.7;

  return (
    <group>
      <mesh
        position={world.center}
        scale={[world.radius[0] * 2, world.radius[1] * 2, world.radius[2] * 2]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[1, 24, 24]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={selected ? Math.min(opacity + 0.25, 0.85) : opacity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh
        position={[
          world.center[0],
          world.center[1],
          world.center[2] + world.radius[2] + 0.08,
        ]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[selected ? 0.2 : 0.14, 16, 16]} />
        <meshBasicMaterial color={markerColor} />
        {selected && (
          <pointLight color={color} intensity={glow * 2} distance={2.5} />
        )}
      </mesh>
    </group>
  );
}

function CameraFocus({ focus }: { focus: [number, number, number] | null }) {
  const controls = useRef<React.ElementRef<typeof OrbitControls>>(null);
  const { camera } = useThree();
  const anim = useRef<{
    fromPos: THREE.Vector3;
    fromTarget: THREE.Vector3;
    toPos: THREE.Vector3;
    toTarget: THREE.Vector3;
    t: number;
  } | null>(null);

  useFrame((_, delta) => {
    const controlsRef = controls.current;
    if (!controlsRef) return;
    if (focus) {
      if (!anim.current || anim.current.t >= 1) {
        const toTarget = new THREE.Vector3(...focus);
        const dir = new THREE.Vector3(0.55, -0.6, 0.45).normalize();
        const dist = 5.5;
        const toPos = toTarget.clone().addScaledVector(dir, dist);
        anim.current = {
          fromPos: camera.position.clone(),
          fromTarget: controlsRef.target.clone(),
          toPos,
          toTarget,
          t: 0,
        };
      }
      const a = anim.current;
      a.t = Math.min(a.t + delta * 1.6, 1);
      const k = THREE.MathUtils.smoothstep(a.t, 0, 1);
      camera.position.lerpVectors(a.fromPos, a.toPos, k);
      controlsRef.target.lerpVectors(a.fromTarget, a.toTarget, k);
      controlsRef.update();
    }
  });

  return (
    <OrbitControls
      ref={controls}
      target={[0, 0, 0.85]}
      enableDamping
      dampingFactor={0.08}
      minDistance={2.5}
      maxDistance={14}
      minPolarAngle={0.15}
      maxPolarAngle={Math.PI * 0.55}
    />
  );
}

export default function CarViewer({
  archetype,
  damages,
  severity,
  selectedZone,
  onSelectZone,
}: {
  archetype: Archetype;
  damages: Damage[];
  severity: string | null;
  selectedZone: string | null;
  onSelectZone: (zone: string | null) => void;
}) {
  const [bounds, setBounds] = useState<VehicleBounds>(DEFAULT_BOUNDS);
  const onBounds = useMemo(
    () => (b: VehicleBounds) => setBounds((prev) => (prev === b ? prev : b)),
    [],
  );

  const focusDef = useMemo(() => {
    if (!selectedZone) return null;
    const def = zoneDef(archetype, selectedZone);
    return def ? toWorld(def, bounds, archetype).center : null;
  }, [selectedZone, archetype, bounds]);

  return (
    <div className="relative h-full w-full rounded-xl bg-gradient-to-b from-zinc-900 to-zinc-950">
      <Canvas
        camera={{ position: [3.4, -3.8, 2.3], up: [0, 0, 1], fov: 42 }}
        className="cursor-grab active:cursor-grabbing"
      >
        <color attach="background" args={["#0c0d10"]} />
        <ambientLight intensity={1.1} />
        <directionalLight
          position={[6, -4, 9]}
          intensity={2.2}
          castShadow
          shadow-mapSize={[1024, 1024]}
          shadow-camera-left={-6}
          shadow-camera-right={6}
          shadow-camera-top={6}
          shadow-camera-bottom={-6}
        />
        <directionalLight position={[-4, 3, 4]} intensity={0.6} />
        <Suspense fallback={null}>
          <VehicleModel archetype={archetype} onBounds={onBounds} />
          {damages.map((d) => (
            <ZoneMarker
              key={`${archetype}-${d.zone}`}
              damage={d}
              archetype={archetype}
              bounds={bounds}
              severity={severity}
              selected={selectedZone === d.zone}
              onSelect={() =>
                onSelectZone(selectedZone === d.zone ? null : d.zone)
              }
            />
          ))}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -0.01]} receiveShadow>
            <planeGeometry args={[40, 40]} />
            <shadowMaterial opacity={0.35} />
          </mesh>
          <CameraFocus focus={focusDef} />
        </Suspense>
      </Canvas>
      <div className="pointer-events-none absolute left-3 top-3 rounded-md bg-black/50 px-2.5 py-1.5 text-xs text-zinc-300">
        Ziehen: drehen · Scrollen: zoomen · Zone anklicken: Details
      </div>
    </div>
  );
}
