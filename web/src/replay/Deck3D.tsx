import { OrbitControls } from "@react-three/drei";
import { DeckLoader } from "./DeckLoader";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { BASE_MM, labwareTitle } from "./model";
import {
  CAMERA_FOV,
  PIPETTE_LENGTH_MM,
  TIP_LENGTH_MM,
  binSpot,
  columnOf,
  homeView,
  labelHeight,
  liquidColumns,
  place,
  racksOfFrame,
  radiusAt,
  rowsOfFrame,
  tipsInRack,
  type Column,
  type LabwarePlacement,
  type Profile,
} from "./scene";
import { useTokens, type SceneTokens } from "./tokens";
import {
  CHANNELS,
  LEFT,
  MOUNT_GAP_MM,
  NOZZLE_PITCH_MM,
  RIGHT,
  rowMid,
  type Frame,
  type Timeline,
} from "./timeline";
import styles from "./Deck3D.module.css";
import type { Highlight, ReplayModel } from "./types";

/* The 3D view: the OT-2 deck with its eleven slots and the trash as a bin, every labware at
   its real footprint, its wells at the positions, diameters and depths of its definition and
   in the outline the ledger's own height table gives them (a cone, a bowl, a trough; a
   straight column when the export carries no table), the liquid in each well cut off at the
   height that table gives its volume (else the volume over the well's rated maximum), never
   under the drawing floor (state.ts MIN_FILL), coloured by what it holds (the liquids'
   colours blended by share; the 2D view shows the stack). The pipette is a gantry that travels along its path to the well of the
   current event, its tip filling and emptying as the ledger's volumes move; a rack loses its
   tips as they are used and the bin gains them. Orbit to look around, scroll to zoom, the
   button resets the view; Nothing here is physics: no
   droplets, no meniscus, only the ledger's numbers, interpolated between two known states.

   The shading is convention, like the choice of a lathe: the scene is lit by an environment
   map built in memory (RoomLight), the liquid is a glossy physical material with a darker
   floor, a brighter top and a rim (liquidShaderFor), each column has a lit surface disc and
   each well is a thin clear tube. A sheen says nothing about the liquid; a meniscus or a
   slosh would, so neither is drawn. Colours are not tone mapped (`flat`), so a token and a
   liquid's colour reach the screen as given, and the lights are tuned per theme by screenshot.

   `frame` is one object the component mutates on every tick; `version` is its counter, so
   React renders when it changes while the meshes are updated in place in useFrame. */
export function Deck3D({
  model,
  timeline,
  frame,
  version,
  playing,
  highlight,
  onSelect,
}: {
  model: ReplayModel;
  timeline: Timeline;
  frame: Frame;
  version: number;
  playing: boolean;
  highlight?: Highlight | null;
  onSelect?: (id: string) => void;
}) {
  const tokens = useTokens();
  const placements = useMemo(() => place(model), [model]);
  const home = useMemo(() => homeView(model), [model]);
  const controls = useRef<OrbitControlsImpl | null>(null);
  const [ready, setReady] = useState(false);
  const reset = () => {
    const c = controls.current;
    if (!c) return;
    c.object.position.set(...home.position);
    c.target.set(...home.target);
    c.update();
  };
  const live = playing;
  return (
    <div className={styles.wrap}>
      {!ready && <DeckLoader overlay />}
      <Canvas
        className={styles.canvas}
        frameloop={live ? "always" : "demand"}
        dpr={[1, 1.5]}
        camera={{
          position: home.position,
          fov: CAMERA_FOV,
          near: 1,
          far: 4000,
        }}
        flat
        gl={{ antialias: true, alpha: true }}
        onCreated={() => requestAnimationFrame(() => setReady(true))} // after the first frame
      >
        <Scene
          model={model}
          timeline={timeline}
          placements={placements}
          frame={frame}
          version={version}
          highlight={highlight ?? null}
          tokens={tokens}
          onSelect={onSelect}
        />
        <OrbitControls
          ref={controls}
          makeDefault
          target={home.target}
          minDistance={40}
          maxDistance={1200}
          maxPolarAngle={Math.PI / 2 - 0.02}
          enableDamping={false}
        />
      </Canvas>
      <div className={styles.bar}>
        <button
          type="button"
          onClick={reset}
          className={styles.reset}
          disabled={!ready}
        >
          Reset the view
        </button>
        <span className={styles.hint}>
          drag to orbit · scroll to zoom · right-drag to pan
        </span>
      </div>
    </div>
  );
}

function Scene({
  model,
  timeline,
  placements,
  frame,
  version,
  highlight,
  tokens,
  onSelect,
}: {
  model: ReplayModel;
  timeline: Timeline;
  placements: LabwarePlacement[];
  frame: Frame;
  version: number;
  highlight: Highlight | null;
  tokens: SceneTokens;
  onSelect?: (id: string) => void;
}) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => invalidate(), [version, highlight, tokens, invalidate]);
  const { width: W, height: H, slots } = model.data.deck;
  const occupied = useMemo(
    () => new Set(model.labware.map((l) => l.row.slot)),
    [model],
  );
  const labelY = useMemo(() => labelHeight(model), [model]);
  return (
    <>
      <RoomLight intensity={tokens.dark ? 0.5 : 0.38} />
      <directionalLight
        position={[W * 0.3, 400, 200]}
        intensity={tokens.dark ? 1.2 : 0.9}
      />
      {/* the deck */}
      <mesh position={[W / 2, -1.5, -H / 2]} receiveShadow>
        <boxGeometry args={[W + 12, 3, H + 12]} />
        <meshStandardMaterial color={tokens.surface2} roughness={0.9} />
      </mesh>
      {slots.map((s) => (
        <group
          key={s.id}
          position={[s.x + s.width / 2, 0, -(s.y + s.height / 2)]}
        >
          <mesh position={[0, 0.3, 0]}>
            <boxGeometry args={[s.width, 0.6, s.height]} />
            <meshStandardMaterial color={tokens.surface} roughness={0.8} />
          </mesh>
          {!occupied.has(s.id) && (
            <Label
              text={s.id}
              colour={tokens.faint}
              width={30}
              y={0.65}
              z={0}
              bold
            />
          )}
        </group>
      ))}
      {placements.map((p) =>
        p.lw.row.is_trash ? (
          <TrashBin
            key={p.lw.row.id}
            p={p}
            frame={frame}
            timeline={timeline}
            tokens={tokens}
          />
        ) : (
          <Labware3D
            key={p.lw.row.id}
            model={model}
            p={p}
            frame={frame}
            tokens={tokens}
            labelY={labelY}
            onSelect={onSelect}
          />
        ),
      )}
      <Rings
        model={model}
        placements={placements}
        frame={frame}
        highlight={highlight}
        tokens={tokens}
      />
      <Pipette
        frame={frame}
        timeline={timeline}
        width={W}
        depth={H}
        tokens={tokens}
        pipettes={model.data.pipettes}
      />
    </>
  );
}

/* A labware: a glass body of its footprint, its wells as clear tubes turned from the ledger's
   own outline (scene.unitProfile: a cone, a bowl, a trough or a straight column; one lathe per
   labware, instanced) at their definition's places, the liquid in each as the same solid cut
   off at the ledger's height for the volume (a per-instance fill in the vertex shader), a tip
   in each rack position that still holds one, and its name on its front edge. The columns
   follow the frame: every well is rewritten when the event changes, and only the wells the
   event is changing on the frames between. */
function Labware3D({
  model,
  p,
  frame,
  tokens,
  labelY,
  onSelect,
}: {
  model: ReplayModel;
  p: LabwarePlacement;
  frame: Frame;
  tokens: SceneTokens;
  labelY: number;
  onSelect?: (id: string) => void;
}) {
  const wells = useRef<THREE.InstancedMesh>(null);
  const liquid = useRef<THREE.InstancedMesh>(null);
  const film = useRef<THREE.InstancedMesh>(null);
  const surface = useRef<THREE.InstancedMesh>(null);
  const tips = useRef<THREE.InstancedMesh>(null);
  const n = p.wells.length;
  const buffers = useMemo(
    () => ({
      fractions: new Float32Array(n),
      colours: new Float32Array(n * 3),
      films: new Float32Array(n),
      certain: new Float32Array(n),
      shown: new Float32Array(n),
      fills: new Float32Array(n), // the liquid's top per well, 0..1 of the depth: the shader's aFill
      o: new THREE.Object3D(),
      c: new THREE.Color(),
      body: new THREE.Color(),
      col: { fraction: 0, r: 0, g: 0, b: 0, film: 0, certain: 1 } as Column,
      slot: new Map<number, number>(p.wells.map((w, i) => [w.index, i])), // well index -> instance
    }),
    [n, p],
  );
  // one lathe per labware: the well (a clear tube) and the liquid (the same solid, cut off per
  // instance at its fill) share the outline; the film and the disc are flat
  const geometry = useMemo(
    () => latheOf(p.profile, p.round),
    [p.profile, p.round],
  );
  const column = useMemo(() => {
    const g = geometry.clone();
    g.setAttribute(
      "aFill",
      new THREE.InstancedBufferAttribute(buffers.fills, 1),
    );
    return g;
  }, [geometry, buffers]);
  const filmGeometry = useMemo(
    () =>
      p.round
        ? new THREE.CylinderGeometry(1, 1, 1, 20, 1, false)
        : new THREE.BoxGeometry(2, 1, 2),
    [p.round],
  );
  const disc = useMemo(
    () =>
      p.round ? new THREE.CircleGeometry(1, 20) : new THREE.PlaneGeometry(2, 2),
    [p.round],
  );
  const cone = useMemo(() => new THREE.ConeGeometry(1, 1, 14), []);
  const shader = useMemo(
    () => liquidShaderFor(lathePoints(p.profile, p.round)),
    [p.profile, p.round],
  );
  useEffect(
    () => () =>
      [geometry, column, filmGeometry, disc, cone].forEach((g) => g.dispose()),
    [geometry, column, filmGeometry, disc, cone],
  );
  const base = BASE_MM;
  const tiprack = p.lw.row.is_tiprack;
  const seen = useRef({
    version: -1,
    event: -2,
    racks: null as unknown,
    tokens: null as unknown,
  });

  // The wells never move, and the liquid solid sits in the well at 0.9 of its width: their
  // matrices are written once. The lathe's local y runs 0..1, floor to rim.
  useLayoutEffect(() => {
    const { o } = buffers;
    const write = (mesh: THREE.InstancedMesh | null, k: number) => {
      if (!mesh) return;
      p.wells.forEach((w, i) => {
        o.position.set(w.x, base, w.z);
        o.scale.set(w.rx * k, w.depth, w.rz * k);
        o.rotation.set(0, 0, 0);
        o.updateMatrix();
        mesh.setMatrixAt(i, o.matrix);
      });
      mesh.instanceMatrix.needsUpdate = true;
    };
    write(wells.current, 1);
    write(liquid.current, 0.9);
  }, [p, buffers, base]);

  const writeColumn = (
    i: number,
    w: LabwarePlacement["wells"][number],
    mesh: THREE.InstancedMesh,
    filmMesh: THREE.InstancedMesh,
    top: THREE.InstancedMesh,
  ) => {
    const { o, c, body, col, fills } = buffers;
    const f = col.fraction;
    fills[i] = f; // the solid is cut at this height in the vertex shader; 0 draws nothing
    c.setRGB(col.r, col.g, col.b);
    if (col.certain < 1) c.lerp(body, 0.5); // not certain: paler
    mesh.setColorAt(i, c);
    // the surface: a lit disc a hair above the liquid's top, as wide as the well is there
    const r = radiusAt(p.profile, f) * 0.9;
    o.position.set(w.x, base + f * w.depth + 0.02, w.z);
    o.scale.set(f > 0 ? w.rx * r : 1e-4, f > 0 ? w.rz * r : 1e-4, 1);
    o.rotation.set(-Math.PI / 2, 0, 0);
    o.updateMatrix();
    top.setMatrixAt(i, o.matrix);
    top.setColorAt(i, c);
    // a film: a thin disc on the well's floor in the liquid's colour
    const isFilm = col.film > 0;
    o.position.set(w.x, base + 0.3, w.z);
    o.scale.set(
      isFilm ? w.rx * 0.9 : 1e-4,
      isFilm ? 0.6 : 1e-4,
      isFilm ? w.rz * 0.9 : 1e-4,
    );
    o.rotation.set(0, 0, 0);
    o.updateMatrix();
    filmMesh.setMatrixAt(i, o.matrix);
    filmMesh.setColorAt(i, c);
  };

  useFrame(() => {
    const s = seen.current;
    if (s.version === frame.version && s.tokens === tokens) return;
    const { o, c, body, fractions, colours, films, certain, shown, col, slot } =
      buffers;
    body.set(tokens.surface2);
    if (tiprack) {
      const mesh = tips.current;
      if (!mesh) return;
      const racks = racksOfFrame(frame);
      if (racks === s.racks && s.tokens === tokens) {
        s.version = frame.version;
        return;
      }
      s.racks = racks;
      tipsInRack(racks, p, shown);
      p.wells.forEach((w, i) => {
        const on = shown[i];
        o.position.set(w.x, base + w.depth / 2, w.z);
        o.scale.set(
          on > 0 ? w.rx * 0.85 : 1e-4,
          on > 0 ? w.depth : 1e-4,
          on > 0 ? w.rz * 0.85 : 1e-4,
        );
        o.rotation.set(Math.PI, 0, 0);
        o.updateMatrix();
        mesh.setMatrixAt(i, o.matrix);
        mesh.setColorAt(i, c.set(on === 1 ? tokens.muted : tokens.warning));
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      s.version = frame.version;
      s.tokens = tokens;
      return;
    }
    const mesh = liquid.current;
    const filmMesh = film.current;
    const top = surface.current;
    if (!mesh || !filmMesh || !top) return;
    const rows = rowsOfFrame(frame);
    if (s.event !== frame.event || s.tokens !== tokens) {
      // every well, from the state the frame holds (live rows included)
      liquidColumns(model, rows, p, fractions, colours, films, certain);
      p.wells.forEach((w, i) => {
        col.fraction = fractions[i];
        col.r = colours[i * 3];
        col.g = colours[i * 3 + 1];
        col.b = colours[i * 3 + 2];
        col.film = films[i];
        col.certain = certain[i];
        writeColumn(i, w, mesh, filmMesh, top);
      });
      s.event = frame.event;
      s.tokens = tokens;
    } else if (frame.live.size) {
      // only the wells this event is changing
      for (const index of frame.live.keys()) {
        const i = slot.get(index);
        if (i === undefined) continue;
        columnOf(model, rows(index), p.wells[i].max, col, p.wells[i].shape);
        writeColumn(i, p.wells[i], mesh, filmMesh, top);
      }
    } else {
      s.version = frame.version;
      return;
    }
    column.getAttribute("aFill").needsUpdate = true;
    filmMesh.instanceMatrix.needsUpdate = true;
    top.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    if (filmMesh.instanceColor) filmMesh.instanceColor.needsUpdate = true;
    if (top.instanceColor) top.instanceColor.needsUpdate = true;
    s.version = frame.version;
  });

  const select = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect?.(p.lw.row.id);
  };
  return (
    <group>
      <mesh position={[p.x, p.height / 2, p.z]} onClick={select}>
        <boxGeometry args={[p.w, p.height, p.d]} />
        <meshPhysicalMaterial
          color={tokens.surface}
          transparent
          opacity={tokens.dark ? 0.3 : 0.4}
          roughness={0.25}
          clearcoat={1}
          clearcoatRoughness={0.2}
          depthWrite={false}
        />
      </mesh>
      {/* the base, opaque */}
      <mesh position={[p.x, base / 2, p.z]}>
        <boxGeometry args={[p.w, base, p.d]} />
        <meshStandardMaterial color={tokens.border} roughness={0.8} />
      </mesh>
      {n > 0 && (
        // the well: a thin clear tube, drawn after the columns so the liquid shows through it
        <instancedMesh
          ref={wells}
          args={[geometry, undefined, n]}
          frustumCulled={false}
          renderOrder={2}
        >
          <meshPhysicalMaterial
            color={tokens.dark ? "#9aa3b0" : "#ffffff"}
            side={THREE.DoubleSide}
            roughness={0.15}
            transparent
            opacity={0.22}
            clearcoat={1}
            clearcoatRoughness={0.1}
            depthWrite={false}
          />
        </instancedMesh>
      )}
      {n > 0 && !tiprack && (
        <>
          <instancedMesh
            ref={liquid}
            args={[column, undefined, n]}
            frustumCulled={false}
          >
            <meshPhysicalMaterial
              roughness={0.12}
              clearcoat={0.8}
              clearcoatRoughness={0.1}
              onBeforeCompile={shader}
            />
          </instancedMesh>
          <instancedMesh
            ref={surface}
            args={[disc, undefined, n]}
            frustumCulled={false}
            renderOrder={1}
          >
            <meshPhysicalMaterial
              roughness={0.22}
              clearcoat={0.5}
              clearcoatRoughness={0.25}
              transparent
              opacity={0.9}
              onBeforeCompile={surfaceShader}
            />
          </instancedMesh>
          <instancedMesh
            ref={film}
            args={[filmGeometry, undefined, n]}
            frustumCulled={false}
          >
            <meshStandardMaterial roughness={0.3} transparent opacity={0.6} />
          </instancedMesh>
        </>
      )}
      {n > 0 && tiprack && (
        <instancedMesh
          ref={tips}
          args={[cone, undefined, n]}
          frustumCulled={false}
        >
          <meshStandardMaterial roughness={0.5} />
        </instancedMesh>
      )}
      {/* the name, at the deck's one label height (above the tallest labware), on the front edge */}
      <group
        position={[p.x, Math.max(p.height + 0.05, labelY), p.z + p.d / 2 - 5]}
      >
        <Label
          text={`${p.lw.row.slot} · ${labwareTitle(p.lw)}`}
          colour={tokens.text}
          width={p.w - 6}
          y={0}
          z={0}
        />
      </group>
    </group>
  );
}

/* The light of a room, built in memory: three's RoomEnvironment (a box with a few emissive
   panels) rendered once through PMREMGenerator into the scene's environment map, so a glossy
   surface has something to reflect. No file is fetched. The intensity is per theme. */
function RoomLight({ intensity }: { intensity: number }) {
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    return () => {
      scene.environment = null;
      env.dispose();
      pmrem.dispose();
    };
  }, [gl, scene]);
  useEffect(() => {
    scene.environmentIntensity = intensity;
  }, [scene, intensity]);
  return null;
}

/* A well's outline as geometry: the profile turned about its axis, 20 sides for a round
   well, 4 for a box (turned so a side is a wall: the box's half-side is the profile's radius
   times root two), with a floor from the axis out when the outline does not start at a point.
   The lathe's y runs 0..1, the depth; the instance matrix scales it to the well. */
const PROFILE_MAX = 32; // the shader's uniform holds this many points
function lathePoints(profile: Profile, round: boolean): THREE.Vector2[] {
  const k = round ? 1 : Math.SQRT2;
  const points = profile.map(([r, y]) => new THREE.Vector2(r * k, y));
  if (points[0].x > 0) points.unshift(new THREE.Vector2(0, 0));
  return points.slice(-PROFILE_MAX);
}
function latheOf(profile: Profile, round: boolean): THREE.BufferGeometry {
  const lathe = new THREE.LatheGeometry(
    lathePoints(profile, round),
    round ? 20 : 4,
    round ? 0 : Math.PI / 4,
  );
  if (round) return lathe;
  const flat = lathe.toNonIndexed(); // a box has flat faces: no smoothing over the corners
  flat.computeVertexNormals();
  lathe.dispose();
  return flat;
}

/* The liquid's shading, added to the physical material's shaders. In the vertex stage the
   solid is cut at the instance's fill (`aFill`, 0..1 of the depth): every vertex above it is
   brought down to that height and out to the outline's radius there, read from the same
   points the lathe was turned from (`uProfile`); a fill of 0 draws nothing. In the fragment
   stage a vertical gradient (darker at the floor, brighter at the surface) and a brighter rim
   where the surface turns away from the eye. Drawing conventions, like the choice of a
   lathe: they say nothing about the liquid. */
const HEIGHT_VARYING = "varying float vHeight;\n";
function liquidShaderFor(
  points: THREE.Vector2[],
): (shader: THREE.WebGLProgramParametersWithUniforms) => void {
  const profile = Array.from({ length: PROFILE_MAX }, (_, i) =>
    points[Math.min(i, points.length - 1)].clone(),
  );
  return (shader) => {
    shader.uniforms.uProfile = { value: profile };
    shader.uniforms.uProfileCount = { value: points.length };
    shader.vertexShader =
      `attribute float aFill;\nuniform vec2 uProfile[${PROFILE_MAX}];\nuniform int uProfileCount;\n` +
      HEIGHT_VARYING +
      shader.vertexShader.replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        float fill = aFill;
        if (fill <= 0.0) {
          transformed = vec3(0.0);
        } else if (position.y > fill) {
          float r = uProfile[uProfileCount - 1].x;
          for (int i = 1; i < ${PROFILE_MAX}; i++) {
            if (i >= uProfileCount) break;
            if (uProfile[i].y >= fill) {
              vec2 a = uProfile[i - 1];
              vec2 b = uProfile[i];
              r = mix(a.x, b.x, clamp((fill - a.y) / max(b.y - a.y, 1e-6), 0.0, 1.0));
              break;
            }
          }
          float r0 = length(position.xz);
          transformed.xz = r0 > 1e-6 ? position.xz * (r / r0) : position.xz;
          transformed.y = fill;
        }
        vHeight = transformed.y / max(fill, 1e-4);`,
      );
    shader.fragmentShader =
      HEIGHT_VARYING +
      shader.fragmentShader
        .replace(
          "#include <color_fragment>",
          "#include <color_fragment>\n diffuseColor.rgb *= mix(0.62, 1.05, clamp(vHeight, 0.0, 1.0));",
        )
        .replace(
          "#include <opaque_fragment>",
          "float rim = pow(1.0 - abs(dot(normalize(vViewPosition), normalize(vNormal))), 3.0);\n outgoingLight += vec3(0.18) * rim;\n#include <opaque_fragment>",
        );
  };
}

/* The surface disc: the column's colour tinted a little towards white, brighter at a
   glancing angle. */
function surfaceShader(shader: THREE.WebGLProgramParametersWithUniforms): void {
  shader.fragmentShader = shader.fragmentShader
    .replace(
      "#include <color_fragment>",
      "#include <color_fragment>\n diffuseColor.rgb = mix(diffuseColor.rgb, vec3(1.0), 0.04);",
    )
    .replace(
      "#include <opaque_fragment>",
      "float rim = pow(1.0 - abs(dot(normalize(vViewPosition), normalize(vNormal))), 2.0);\n outgoingLight += vec3(0.12) * rim;\n#include <opaque_fragment>",
    );
}

/* The fixed trash: an open bin the height of a tall labware, in slot 12, with the tips the
   run has dropped lying in it, each in the colour of its residue. */
function TrashBin({
  p,
  frame,
  timeline,
  tokens,
}: {
  p: LabwarePlacement;
  frame: Frame;
  timeline: Timeline;
  tokens: SceneTokens;
}) {
  const t = 2;
  const h = p.height;
  const capacity = Math.max(1, timeline.drops[timeline.count]);
  // the liquid level: the run's total waste fills the bin to a third; nothing is drawn inside
  // the bin but the level and the tips, because the ledger knows microlitres and tips only
  const level = useRef<THREE.Mesh>(null);
  const wasteMax = Math.max(1, timeline.waste[timeline.count]);
  const [words, setWords] = useState<string>("12 · Trash");
  const lastWords = useRef("");
  const pile = useRef<THREE.InstancedMesh>(null);
  const cone = useMemo(
    () => new THREE.ConeGeometry(2.2, TIP_LENGTH_MM, 10),
    [],
  );
  const o = useMemo(() => new THREE.Object3D(), []);
  const c = useMemo(() => new THREE.Color(), []);
  const written = useRef(-1);
  useFrame(() => {
    const lv = level.current;
    if (lv) {
      const frac = frame.waste / wasteMax;
      const height = Math.max(0.01, frac * h * 0.35);
      lv.scale.y = height;
      lv.position.y = t + height / 2;
      lv.visible = frame.waste > 0;
    }
    // the label's text changes only per tip and per 10 µl, so the texture cache stays small
    const coarse = Math.round(frame.waste / 10) * 10;
    const next = `12 · Trash · ${frame.drops} tip${frame.drops === 1 ? "" : "s"}${coarse > 0 ? ` · ${coarse} µl` : ""}`;
    if (next !== lastWords.current) {
      lastWords.current = next;
      setWords(next);
    }
    const mesh = pile.current;
    if (!mesh || written.current === frame.drops) return;
    const count = Math.min(capacity, frame.drops);
    for (
      let n = written.current < 0 ? 0 : Math.min(written.current, count);
      n < count;
      n++
    ) {
      const spot = binSpot(n, p);
      o.position.set(spot.x, spot.y, spot.z);
      // the cone's axis is its local y: laid flat by the pitch, then turned by the yaw about
      // the vertical (scene.binTipEnds is this same rotation in numbers)
      o.rotation.set(
        Math.PI / 2 + spot.pitch,
        Math.PI / 2 - spot.yaw,
        0,
        "YXZ",
      );
      o.scale.set(1, 1, 1);
      o.updateMatrix();
      mesh.setMatrixAt(n, o.matrix);
      mesh.setColorAt(
        n,
        c.setRGB(
          timeline.dropColour[n * 3] ?? 0.6,
          timeline.dropColour[n * 3 + 1] ?? 0.6,
          timeline.dropColour[n * 3 + 2] ?? 0.6,
        ),
      );
    }
    mesh.count = count;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    written.current = frame.drops;
  });
  return (
    <group>
      <group position={[p.x, 0, p.z]}>
        <mesh position={[0, t / 2, 0]}>
          <boxGeometry args={[p.w, t, p.d]} />
          <meshStandardMaterial color={tokens.border} roughness={0.9} />
        </mesh>
        {[
          [0, -p.d / 2 + t / 2, p.w, t],
          [0, p.d / 2 - t / 2, p.w, t],
          [-p.w / 2 + t / 2, 0, t, p.d],
          [p.w / 2 - t / 2, 0, t, p.d],
        ].map(([x, z, w, d], i) => (
          <mesh key={i} position={[x, h / 2, z]}>
            <boxGeometry args={[w, h, d]} />
            <meshStandardMaterial
              color={tokens.surface2}
              roughness={0.9}
              transparent
              opacity={0.85}
            />
          </mesh>
        ))}
        <mesh ref={level} position={[0, t, 0]} visible={false}>
          <boxGeometry args={[p.w - 2 * t, 1, p.d - 2 * t]} />
          <meshStandardMaterial
            color={tokens.muted}
            transparent
            opacity={0.35}
            roughness={0.2}
            depthWrite={false}
          />
        </mesh>
        <group position={[0, h + 0.05, p.d / 2 - 6]}>
          <Label
            text={words}
            colour={tokens.muted}
            width={p.w - 6}
            y={0}
            z={0}
          />
        </group>
      </group>
      <instancedMesh
        ref={pile}
        args={[cone, undefined, capacity]}
        frustumCulled={false}
      >
        <meshStandardMaterial roughness={0.5} />
      </instancedMesh>
    </group>
  );
}

/* Rings on the rim of wells: the wells the pipette is working in, a finding's wells (red)
   and the wells the damage reached later (orange). Three instanced meshes; the first follows
   the frame, the others the highlight. */
function Rings({
  model,
  placements,
  frame,
  highlight,
  tokens,
}: {
  model: ReplayModel;
  placements: LabwarePlacement[];
  frame: Frame;
  highlight: Highlight | null;
  tokens: SceneTokens;
}) {
  const capacity = Math.max(1, model.wells.length);
  const acted = useRef<THREE.InstancedMesh>(null);
  const marked = useRef<THREE.InstancedMesh>(null);
  const reached = useRef<THREE.InstancedMesh>(null);
  const torus = useMemo(() => new THREE.TorusGeometry(1, 0.06, 6, 32), []);
  const o = useMemo(() => new THREE.Object3D(), []);
  const byIndex = useMemo(() => {
    const map = new Map<
      number,
      { x: number; y: number; z: number; r: number }
    >();
    for (const p of placements)
      for (const w of p.wells)
        if (w.index >= 0)
          map.set(w.index, {
            x: w.x,
            y: p.height + 0.4,
            z: w.z,
            r: Math.max(w.rx, w.rz) + 0.5,
          });
    return map;
  }, [placements]);
  const write = (
    mesh: THREE.InstancedMesh | null,
    indices: ArrayLike<number>,
  ) => {
    if (!mesh) return;
    let n = 0;
    for (let k = 0; k < indices.length; k++) {
      const w = byIndex.get(indices[k]);
      if (!w || n >= capacity) continue;
      o.position.set(w.x, w.y, w.z);
      o.scale.set(w.r, w.r, 1);
      o.rotation.set(-Math.PI / 2, 0, 0);
      o.updateMatrix();
      mesh.setMatrixAt(n++, o.matrix);
    }
    mesh.count = n;
    mesh.instanceMatrix.needsUpdate = true;
  };
  useLayoutEffect(() => {
    write(marked.current, highlight?.wells ?? []);
    write(reached.current, highlight?.downstream ?? []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight, byIndex, capacity, o]);
  const actedKey = useRef("");
  const targets = useMemo(() => new Int32Array(CHANNELS), []);
  useFrame(() => {
    const e = frame.event < model.count ? model.data.events[frame.event] : null;
    const on = e && frame.phase === "action";
    const key = on ? `${frame.event}` : "";
    if (key === actedKey.current) return;
    actedKey.current = key;
    let n = 0;
    if (on) for (const t of e.targets) if (n < CHANNELS) targets[n++] = t[1];
    write(acted.current, targets.subarray(0, n));
  });
  return (
    <>
      <instancedMesh
        ref={acted}
        args={[torus, undefined, capacity]}
        frustumCulled={false}
      >
        <meshBasicMaterial color={tokens.text} />
      </instancedMesh>
      <instancedMesh
        ref={marked}
        args={[torus, undefined, capacity]}
        frustumCulled={false}
      >
        <meshBasicMaterial color={tokens.error} />
      </instancedMesh>
      <instancedMesh
        ref={reached}
        args={[torus, undefined, capacity]}
        frustumCulled={false}
      >
        <meshBasicMaterial color={tokens.warning} />
      </instancedMesh>
    </>
  );
}

/* The pipette: a cross-beam over the deck, one carriage block riding under it, a rod from the
   block down to each mount (the OT-2 has one carriage with two mounts 34 mm apart along x),
   the working pipette (the one the event names) hanging from its rod and the other held up
   under the block, each on its own side, and one tip
   per channel when a tip is on, filled to what it holds in the colour of what it drew. The rig
   sits where the frame says the tip's point is; the frame moves it along the path between
   two ledger states, and the rods are scaled every frame so nothing floats. The beam rides on
   two side rails, one along each side of the deck on a post at each end, a shoe at each of
   the beam's ends sitting on its rail, so the beam travels front to back on something. */
function Pipette({
  frame,
  timeline,
  width,
  depth,
  tokens,
  pipettes,
}: {
  frame: Frame;
  timeline: Timeline;
  width: number;
  depth: number;
  tokens: SceneTokens;
  pipettes: ReplayModel["data"]["pipettes"];
}) {
  const rig = useRef<THREE.Group>(null);
  const body = useRef<THREE.Group>(null); // the head, the body and the mounts: over the first channel's tip
  const beam = useRef<THREE.Group>(null); // the beam and its two shoes
  const block = useRef<THREE.Mesh>(null); // the one carriage block, under the beam, over both mounts
  // One group per mount the protocol loads, each with its own rod and its own pipette's body.
  // The one the event names works (at the rig's point, lowered to the well); the other stays
  // up under the block, the OT-2's mount gap to its side. An export without mounts (schema < 3)
  // draws the pipette with the most channels as the working one, as before.
  const mounts = useMemo(
    () =>
      (["left", "right"] as const)
        .map((m) => ({ m, p: pipettes.find((q) => q.mount === m) }))
        .filter(
          (x): x is { m: "left" | "right"; p: (typeof pipettes)[number] } =>
            Boolean(x.p),
        ),
    [pipettes],
  );
  const fallback: "left" | "right" =
    [...mounts].sort((a, b) => b.p.channels - a.p.channels)[0]?.m ?? "left";
  const groups = useRef<Record<string, THREE.Group | null>>({});
  const rods = useRef<Record<string, THREE.Mesh | null>>({});
  const shells = useRef<(THREE.Mesh | null)[]>([]);
  const contents = useRef<(THREE.Mesh | null)[]>([]);
  const colour = useMemo(() => new THREE.Color(), []);
  const gantry = timeline.travelHeight + TIP_LENGTH_MM + PIPETTE_LENGTH_MM + 30; // where the beam rides
  const bodyBottom = TIP_LENGTH_MM; // local y, above the tip's point (rig y = the point)
  const bodyTop = bodyBottom + PIPETTE_LENGTH_MM;
  useFrame(() => {
    const r = rig.current;
    if (!r) return;
    r.position.set(frame.x, frame.h, -frame.y);
    // the nozzle row starts over the first channel's tip and runs to the front at the pitch of
    // the tips, so a row of tips is under a row of nozzles and a lone tip under the first; the
    // body itself sits over the middle of the row (PipetteBody)
    if (body.current) body.current.position.set(frame.ox[0], 0, -frame.oy[0]);
    // the rods from each head up to the beam, and the block under the beam: their length
    // changes with the rig's height every frame; thin, so a rod never reads as the pipette
    const top = gantry - frame.h;
    // which mount works now, and where the other hangs: the mount gap to its side, its body
    // over the same point of the carriage (each body stands over the middle of its own row)
    const acting =
      frame.mount === LEFT
        ? "left"
        : frame.mount === RIGHT
          ? "right"
          : fallback;
    const actingMid = rowMid(
      mounts.find((x) => x.m === acting)?.p.channels ?? 1,
    );
    // the idle mount stays up under the block while the working one goes down to a well, so it
    // never passes through the labware; each rod spans from its head to the block
    const lift = Math.max(
      0,
      top - BEAM_MM / 2 - BLOCK_MM - bodyTop - HEAD_MM - IDLE_GAP_MM,
    );
    let idleX = 0;
    for (const { m, p } of mounts) {
      const g = groups.current[m];
      const r = rods.current[m];
      const works = m === acting;
      const x = works ? 0 : m === "right" ? MOUNT_GAP_MM : -MOUNT_GAP_MM;
      if (!works) idleX = x;
      const up = works ? 0 : lift;
      if (g) g.position.set(x, up, actingMid - rowMid(p.channels));
      if (r) {
        r.position.y = (bodyTop + HEAD_MM + top - up) / 2;
        r.scale.y = Math.max(1, top - up - bodyTop - HEAD_MM);
      }
    }
    // the beam over the working mount, which is where the block hangs: over the middle of the
    // working pipette's row (an 8-channel's is 31.5 mm in front of its first tip), not over
    // the first tip, so beam and block never part
    if (beam.current)
      beam.current.position.z = -frame.y - frame.oy[0] + actingMid;
    if (block.current) {
      block.current.position.set(
        idleX / 2,
        top - BEAM_MM / 2 - BLOCK_MM / 2,
        actingMid,
      );
    }
    const nk = Math.max(1, frame.channels);
    colour.setRGB(frame.tipColour[0], frame.tipColour[1], frame.tipColour[2]);
    for (let k = 0; k < CHANNELS; k++) {
      const shell = shells.current[k];
      const inner = contents.current[k];
      if (!shell || !inner) continue;
      // a channel on the same point as an earlier one (several channels sent to one short
      // well) is not drawn again: one tip there, and the readout says how many
      let own = true;
      for (let j = 0; j < k && own; j++)
        own =
          Math.abs(frame.ox[j] - frame.ox[k]) > 0.01 ||
          Math.abs(frame.oy[j] - frame.oy[k]) > 0.01;
      const on = k < nk && own && frame.tipOn[k] === 1;
      shell.visible = on;
      inner.visible = on && frame.held[k] > 0;
      if (!on) continue;
      const x = frame.ox[k];
      const z = -frame.oy[k];
      shell.position.set(x, TIP_LENGTH_MM / 2, z);
      const frac = Math.max(
        0,
        Math.min(1, frame.held[k] / timeline.pipetteMax),
      );
      const len = Math.max(TIP_LENGTH_MM * frac, 1e-3);
      inner.position.set(x, len / 2, z);
      inner.scale.setScalar(Math.max(frac, 1e-3));
      (inner.material as THREE.MeshStandardMaterial).color.copy(colour);
    }
  });
  return (
    <>
      {/* the frame: a rail along each side of the deck, under the beam's ends, on two posts */}
      {[-RAIL_X_MM, width + RAIL_X_MM].map((x) => (
        <group key={x}>
          <mesh position={[x, gantry - BEAM_MM / 2 - RAIL_MM / 2, -depth / 2]}>
            <boxGeometry args={[RAIL_MM, RAIL_MM, depth + 24]} />
            <meshStandardMaterial color={tokens.border} roughness={0.7} />
          </mesh>
          {[10, -depth - 10].map((z) => (
            <mesh
              key={z}
              position={[x, (gantry - BEAM_MM / 2 - RAIL_MM) / 2, z]}
            >
              <boxGeometry
                args={[RAIL_MM, gantry - BEAM_MM / 2 - RAIL_MM, RAIL_MM]}
              />
              {/* the front posts stand between the camera and the front slots: see-through, so they
                  never hide the pipette at work there; the back ones solid */}
              <meshStandardMaterial
                color={tokens.border}
                roughness={0.7}
                transparent={z > 0}
                opacity={z > 0 ? 0.28 : 1}
                depthWrite={z <= 0}
              />
            </mesh>
          ))}
        </group>
      ))}
      <group ref={beam} position={[0, 0, 0]}>
        <mesh position={[width / 2, gantry, 0]}>
          <boxGeometry args={[width + 2 * RAIL_X_MM, BEAM_MM, 14]} />
          <meshStandardMaterial color={tokens.border} roughness={0.6} />
        </mesh>
        {/* a shoe at each end, riding on its rail */}
        {[-RAIL_X_MM, width + RAIL_X_MM].map((x) => (
          <mesh key={x} position={[x, gantry, 0]}>
            <boxGeometry args={[RAIL_MM + 6, BEAM_MM + 6, 24]} />
            <meshStandardMaterial color={tokens.muted} roughness={0.5} />
          </mesh>
        ))}
      </group>
      <group
        ref={rig}
        position={[timeline.park[0], timeline.travelHeight, -timeline.park[1]]}
      >
        <group ref={body}>
          {/* the one carriage block, under the beam, spanning both mounts; placed per frame */}
          {/* no pipette loaded (a protocol that runs only a module): no carriage to draw */}
          <mesh ref={block} visible={mounts.length > 0}>
            <boxGeometry
              args={[(mounts.length > 1 ? MOUNT_GAP_MM : 0) + 22, BLOCK_MM, 18]}
            />
            <meshStandardMaterial color={tokens.border} roughness={0.6} />
          </mesh>
          {mounts.map(({ m, p }) => (
            <group key={m} ref={(g) => void (groups.current[m] = g)}>
              {/* the mount's rod from its head up to the block, scaled per frame */}
              <mesh
                ref={(r) => void (rods.current[m] = r)}
                position={[0, bodyTop + HEAD_MM + 10, rowMid(p.channels)]}
              >
                <cylinderGeometry args={[1.6, 1.6, 1, 10]} />
                <meshStandardMaterial color={tokens.faint} roughness={0.6} />
              </mesh>
              <PipetteBody
                y={bodyBottom}
                channels={Math.max(1, p.channels)}
                colour={tokens.muted}
                head={tokens.faint}
              />
            </group>
          ))}
        </group>
        {Array.from({ length: CHANNELS }, (_, k) => (
          <group key={k}>
            <mesh
              ref={(m) => void (shells.current[k] = m)}
              rotation={[Math.PI, 0, 0]}
              visible={false}
            >
              <coneGeometry args={[2.2, TIP_LENGTH_MM, 12, 1, true]} />
              <meshStandardMaterial
                color={tokens.text}
                roughness={0.4}
                transparent
                opacity={0.55}
                side={THREE.DoubleSide}
              />
            </mesh>
            <mesh
              ref={(m) => void (contents.current[k] = m)}
              rotation={[Math.PI, 0, 0]}
              visible={false}
            >
              <coneGeometry args={[2.0, TIP_LENGTH_MM, 12]} />
              <meshStandardMaterial roughness={0.3} />
            </mesh>
          </group>
        ))}
      </group>
    </>
  );
}

const HEAD_MM = 12; // the mount's head block: shorter and narrower than the pipette under it
const BEAM_MM = 8; // the cross-beam's height
const IDLE_GAP_MM = 4; // the idle mount's head under the carriage block
const RAIL_MM = 8; // a side rail's (and its posts') section
const RAIL_X_MM = 20; // how far outside the deck's sides the rails run
const BLOCK_MM = 10; // the carriage block's height, riding under the beam

/* A pipette: a head block on top, a shoulder, the body, and a nozzle per channel, so it
   reads as a pipette at every moment, tip on or off. The first nozzle is at the group's
   origin and a multichannel's other seven trail towards the front of the deck (scene +z) at
   the tips' pitch: the A tip is the pipette's first channel and the A row is at the back of a
   plate, so the tips of a plate column, or the row centred in a trough, are under the
   nozzles; the body stands over the middle of the row, where the mount is. The idle mount is
   the same shape in the border colour. */
function PipetteBody({
  y,
  channels,
  colour,
  head,
}: {
  y: number;
  channels: number;
  colour: string;
  head: string;
}) {
  const bodyTop = y + PIPETTE_LENGTH_MM;
  const shoulder = 10;
  const nozzle = 9;
  const n = Math.max(1, Math.min(8, channels));
  // The mount, and so the body, sits over the middle of the nozzle row: the OT-2 8-channel's
  // definition (opentrons_shared_data, geometry/eight_channel, `nozzleMap`) puts A1 at
  // y = +31.5 and H1 at y = -31.5 from the mount, inside a housing 32 mm × 86 mm.
  const mid = ((n - 1) * NOZZLE_PITCH_MM) / 2;
  return (
    <group>
      <mesh position={[0, bodyTop + HEAD_MM / 2, mid]}>
        <boxGeometry args={[9, HEAD_MM, 7]} />
        <meshStandardMaterial color={head} roughness={0.6} />
      </mesh>
      <mesh position={[0, bodyTop - shoulder / 2, mid]}>
        <cylinderGeometry args={[7, 5.5, shoulder, 18]} />
        <meshStandardMaterial color={colour} roughness={0.45} />
      </mesh>
      <mesh
        position={[
          0,
          y + nozzle + (PIPETTE_LENGTH_MM - shoulder - nozzle) / 2,
          mid,
        ]}
      >
        <cylinderGeometry
          args={[5.5, 4.5, PIPETTE_LENGTH_MM - shoulder - nozzle, 18]}
        />
        <meshStandardMaterial color={colour} roughness={0.5} />
      </mesh>
      {n > 1 && (
        // the housing the nozzles hang from, the width of the row: the multichannel's block
        <mesh position={[0, y + nozzle + 5, mid]}>
          <boxGeometry args={[14, 10, (n - 1) * NOZZLE_PITCH_MM + 14]} />
          <meshStandardMaterial color={colour} roughness={0.5} />
        </mesh>
      )}
      {Array.from({ length: n }, (_, k) => (
        <mesh key={k} position={[0, y + nozzle / 2, k * NOZZLE_PITCH_MM]}>
          <cylinderGeometry args={[1.4, 2.4, nozzle, 12]} />
          <meshStandardMaterial color={colour} roughness={0.5} />
        </mesh>
      ))}
    </group>
  );
}

/* A word on a surface: text drawn to a canvas, on a plane lying flat. No font is fetched. */
function Label({
  text,
  colour,
  width,
  y,
  z,
  bold,
}: {
  text: string;
  colour: string;
  width: number;
  y: number;
  z: number;
  bold?: boolean;
}) {
  const texture = useMemo(
    () => makeLabel(text, colour, bold),
    [text, colour, bold],
  );
  useEffect(() => () => dropLabel(texture), [texture]);
  if (!texture) return null;
  const aspect = texture.image.width / texture.image.height;
  const w = Math.max(4, width);
  return (
    <mesh position={[0, y, z]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[w, w / aspect]} />
      <meshBasicMaterial map={texture} transparent depthWrite={false} />
    </mesh>
  );
}

const labels = new Map<string, THREE.CanvasTexture>();
const labelUsers = new Map<THREE.CanvasTexture, number>();

/* A label no mesh shows any more leaves the cache and frees its canvas. */
function dropLabel(texture: THREE.CanvasTexture | null): void {
  if (!texture) return;
  const n = (labelUsers.get(texture) ?? 1) - 1;
  if (n > 0) {
    labelUsers.set(texture, n);
    return;
  }
  labelUsers.delete(texture);
  for (const [key, t] of labels) if (t === texture) labels.delete(key);
  texture.dispose();
}

function makeLabel(
  text: string,
  colour: string,
  bold?: boolean,
): THREE.CanvasTexture | null {
  if (typeof document === "undefined") return null;
  const key = `${text}|${colour}|${bold ? 1 : 0}`;
  const cached = labels.get(key);
  if (cached) {
    labelUsers.set(cached, (labelUsers.get(cached) ?? 0) + 1);
    return cached;
  }
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const size = 48;
  ctx.font = `${bold ? 700 : 600} ${size}px ui-sans-serif, system-ui, sans-serif`;
  const measured = Math.ceil(ctx.measureText(text).width) + 24;
  canvas.width = Math.max(64, Math.min(2048, measured));
  canvas.height = size + 20;
  ctx.font = `${bold ? 700 : 600} ${size}px ui-sans-serif, system-ui, sans-serif`;
  ctx.fillStyle = colour;
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillText(text, 12, canvas.height / 2, canvas.width - 24);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  labels.set(key, texture);
  labelUsers.set(texture, 1);
  return texture;
}
