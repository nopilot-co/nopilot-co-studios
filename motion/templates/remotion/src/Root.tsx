import React from "react";
import { Composition } from "remotion";
import { Storyboard, sizeFor, totalSeconds } from "./Storyboard";

// Placeholder defaults; real values arrive via --props (inputProps) and are
// applied in calculateMetadata so duration/size match the storyboard.
const FALLBACK = {
  spec: { global: { aspect: "16:9", fps: 30 }, scenes: [] as any[] },
  tokens: { color: {} as Record<string, string> },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="storyboard"
      component={Storyboard as any}
      durationInFrames={300}
      fps={30}
      width={1280}
      height={720}
      defaultProps={FALLBACK as any}
      calculateMetadata={({ props }: any) => {
        const spec = props.spec ?? FALLBACK.spec;
        const fps = Number(spec.global?.fps ?? 30);
        const [width, height] = sizeFor(spec.global?.aspect ?? "16:9");
        const durationInFrames = Math.max(1, Math.round(totalSeconds(spec) * fps));
        return { durationInFrames, fps, width, height };
      }}
    />
  );
};
