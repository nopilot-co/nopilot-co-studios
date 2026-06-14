import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Layer/region/role semantics kept in sync with motion/scripts/motion/animate.py.

type Layer = {
  type: string;
  content?: string;
  region?: string;
  role?: string;
  enter?: string;
};
type Scene = { id: string; duration: number; narration?: string; layers: Layer[] };
type Spec = { global: any; scenes: Scene[] };
type Tokens = { color: Record<string, string> };

const REGIONS: Record<string, [number, number, number, number]> = {
  full: [6, 6, 6, 6],
  center: [38, 18, 38, 18],
  top: [8, 12, 72, 12],
  bottom: [72, 12, 8, 12],
  "upper-third": [6, 8, 66, 8],
  "lower-third": [66, 8, 6, 8],
  left: [20, 52, 20, 8],
  right: [20, 8, 20, 52],
};
const ROLE_COLOR: Record<string, string> = {
  primary: "primary",
  secondary: "secondary",
  accent: "tertiary",
  surface: "surface",
};
const ASPECT_WH: Record<string, [number, number]> = {
  "16:9": [1280, 720],
  "9:16": [720, 1280],
  "1:1": [1080, 1080],
  "4:5": [1024, 1280],
};

export const sizeFor = (aspect: string): [number, number] => ASPECT_WH[aspect] ?? [1280, 720];
export const totalSeconds = (spec: Spec): number =>
  (spec.scenes ?? []).reduce((a, s) => a + Number(s.duration || 0), 0) || 1;

const FONT =
  "ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif";

const LayerView: React.FC<{ layer: Layer; color: Record<string, string> }> = ({ layer, color }) => {
  const frame = useCurrentFrame();
  const [t, r, b, l] = REGIONS[layer.region ?? "center"] ?? REGIONS.center;
  const paint = color[ROLE_COLOR[layer.role ?? ""] ?? ""] ?? color.foreground ?? "#1A2433";

  // Enter motion over the first ~15 frames of the scene.
  const enter = (layer.enter ?? "").toLowerCase();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  let transform = "none";
  if (enter.includes("up")) {
    const dy = interpolate(frame, [0, 15], [28, 0], { extrapolateRight: "clamp" });
    transform = `translateY(${dy}px)`;
  } else if (enter.includes("wipe")) {
    const dx = interpolate(frame, [0, 15], [-40, 0], { extrapolateRight: "clamp" });
    transform = `translateX(${dx}px)`;
  }

  const base: React.CSSProperties = {
    position: "absolute",
    top: `${t}%`,
    right: `${r}%`,
    bottom: `${b}%`,
    left: `${l}%`,
    opacity,
    transform,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    fontFamily: FONT,
    fontWeight: 700,
    lineHeight: 1.15,
  };
  const big = ["center", "top", "full"].includes(layer.region ?? "center");

  if (layer.type === "text") {
    return <div style={{ ...base, color: paint, fontSize: big ? 64 : 38, padding: "0 4%" }}>{layer.content}</div>;
  }
  if (layer.type === "shape") {
    const isRule = (layer.content ?? "").toLowerCase().includes("rule");
    return (
      <div
        style={{
          ...base,
          background: paint,
          borderRadius: 6,
          ...(isRule ? { top: "auto", height: 8 } : {}),
        }}
      />
    );
  }
  // image / icon / chart placeholder (real rendering lands S4/embed).
  const sec = color.secondary ?? "#6B7280";
  return (
    <div style={{ ...base, flexDirection: "column", gap: 8, border: `2px dashed ${sec}`, color: sec, fontSize: 22 }}>
      <span style={{ fontSize: 14, letterSpacing: "0.16em" }}>{String(layer.type).toUpperCase()}</span>
      {layer.content}
    </div>
  );
};

const SceneView: React.FC<{ scene: Scene; color: Record<string, string>; fps: number }> = ({ scene, color, fps }) => {
  const frame = useCurrentFrame();
  const dur = scene.duration * fps;
  const fade = interpolate(frame, [0, 6, dur - 6, dur], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      {scene.layers.map((layer, i) => (
        <LayerView key={i} layer={layer} color={color} />
      ))}
    </AbsoluteFill>
  );
};

export const Storyboard: React.FC<{ spec: Spec; tokens: Tokens }> = ({ spec, tokens }) => {
  const { fps } = useVideoConfig();
  const color = tokens?.color ?? {};
  let acc = 0;
  return (
    <AbsoluteFill style={{ background: color.background ?? "#FFFFFF" }}>
      {(spec.scenes ?? []).map((scene, i) => {
        const from = Math.round(acc * fps);
        acc += Number(scene.duration || 0);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.round(scene.duration * fps)}>
            <SceneView scene={scene} color={color} fps={fps} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
