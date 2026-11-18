import React from "react";
import { AbsoluteFill, Audio, Sequence, getStaticFiles, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C } from "./theme";
import { Background, clamp } from "./ui";

/** scenes.json is the single source of truth for scene order and duration (music.py reads it too). */
export type SceneSpec = { key: string; dur: number };
export const OVERLAP = 10; // frames of cross-fade between scenes

export const totalFrames = (scenes: SceneSpec[]) => scenes.reduce((a, s) => a + s.dur - OVERLAP, OVERLAP);
export const sceneStarts = (scenes: SceneSpec[]) => {
  const out: Record<string, number> = {};
  let at = 0;
  for (const s of scenes) {
    out[s.key] = at;
    at += s.dur - OVERLAP;
  }
  return out;
};
export const hasFile = (name: string) => getStaticFiles().some((f) => f.name === name);

const ProgressBar: React.FC = () => {
  const f = useCurrentFrame();
  const { durationInFrames, width } = useVideoConfig();
  return <div style={{ position: "absolute", left: 0, bottom: 0, height: 4, width: (f / durationInFrames) * width, background: C.gold }} />;
};

/**
 * Lays scenes out in order with cross-fades over the cream background, plus optional public/music.mp3 and
 * public/sfx.mp3. `registry` maps each scene key in scenes.json to a component taking { dur }.
 */
export const Timeline: React.FC<{ scenes: SceneSpec[]; registry: Record<string, React.FC<{ dur: number }>> }> = ({ scenes, registry }) => {
  const { durationInFrames } = useVideoConfig();
  let at = 0;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Background />
      {scenes.map((s) => {
        const from = at;
        at += s.dur - OVERLAP;
        const El = registry[s.key];
        if (!El) throw new Error(`scenes.json has "${s.key}" but no component is registered for it`);
        return (
          <Sequence key={s.key} from={from} durationInFrames={s.dur} name={s.key}>
            <El dur={s.dur} />
          </Sequence>
        );
      })}
      <ProgressBar />
      {hasFile("music.mp3") && (
        <Audio src={staticFile("music.mp3")} volume={(fr) => interpolate(fr, [0, 30, durationInFrames - 60, durationInFrames], [0, 0.5, 0.5, 0], clamp)} />
      )}
      {hasFile("sfx.mp3") && <Audio src={staticFile("sfx.mp3")} volume={0.85} />}
    </AbsoluteFill>
  );
};
