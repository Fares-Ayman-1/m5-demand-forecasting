import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { HORIZON, LAST_DAY } from "../data";
import { hasFile } from "../kit/Timeline";
import { C, FONT } from "../kit/theme";
import { BrowserFrame, Chip, FadeUp, Panel, Scene, enter, useLayout } from "../kit/ui";
import { Head } from "./common";

// public/demo.mp4: the real Streamlit dashboard (app/dashboard.py), recorded by scripts/capture.mjs from
// capture/plan.json at 1280 x 800 CSS px, scale 2 (2560 x 1600), ~22 s. Played from 1 s at 1.75x.
const CAP_W = 2560;
const CAP_H = 1600;
export const DEMO_START = 30;
export const DEMO_RATE = 1.75;

export const Demo: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const fw = wide ? 1180 * u : width - 80 * u;
  const vw = fw - 32 * u - 2;
  const vh = (vw * CAP_H) / CAP_W;
  const e = enter(f, 0, 30);
  const video = hasFile("demo.mp4") ? (
    <OffthreadVideo src={staticFile("demo.mp4")} muted startFrom={DEMO_START} playbackRate={DEMO_RATE} style={{ width: vw, height: vh, display: "block" }} />
  ) : (
    <div style={{ width: vw, height: vh, display: "flex", alignItems: "center", justifyContent: "center", background: C.card2, fontFamily: FONT.mono, fontSize: 18 * u, color: C.muted }}>public/demo.mp4 missing: see video/README.md</div>
  );
  const frame = (
    <div style={{ opacity: e, transform: `translateY(${(1 - e) * 40}px)` }}>
      <BrowserFrame url="localhost:8501 · app/dashboard.py" width={fw}>
        {video}
      </BrowserFrame>
    </div>
  );
  const points = [
    "Pick any store, department or item",
    `Its forecast for days ${LAST_DAY + 1}–${LAST_DAY + HORIZON}`,
    "The most recent backtest: forecast vs actual",
    "Error by aggregation level",
  ];
  if (!wide)
    return (
      <Scene dur={dur}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 26 * u, padding: 40 * u }}>
          <Head eyebrow="The real app · Streamlit" text="The dashboard, running live." highlight={["live."]} size={52} />
          {frame}
          <div style={{ display: "flex", gap: 12 * u, flexWrap: "wrap", justifyContent: "center", maxWidth: 1000 * u }}>
            <Chip at={40} size={18 * u}>Series explorer</Chip>
            <Chip at={44} size={18 * u}>Recent backtest</Chip>
            <Chip at={48} size={18 * u} tone="gold">Error by level</Chip>
          </div>
        </AbsoluteFill>
      </Scene>
    );
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 60 * u, padding: `0 ${70 * u}px` }}>
        {frame}
        <div style={{ width: 520 * u, display: "flex", flexDirection: "column", gap: 26 * u }}>
          <Head eyebrow="The real app · Streamlit" text="The dashboard, running live." highlight={["live."]} align="left" size={60} maxWidth={520 * u} />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 * u }}>
            {points.map((p, i) => (
              <FadeUp key={p} at={40 + i * 10}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 * u }}>
                  <span style={{ width: 12 * u, height: 12 * u, borderRadius: 12, background: C.gold, flex: "none" }} />
                  <span style={{ fontFamily: FONT.body, fontSize: 25 * u, color: C.ink, lineHeight: 1.35 }}>{p}</span>
                </div>
              </FadeUp>
            ))}
          </div>
          <FadeUp at={90}>
            <div style={{ fontFamily: FONT.mono, fontSize: 14 * u, color: C.muted, lineHeight: 1.6 }}>{`Screen recording of the real app, sped up ${DEMO_RATE}×`}</div>
          </FadeUp>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};

/** Engineering: the parts around the model. */
export const Engineering: React.FC<{ dur: number }> = ({ dur }) => {
  const { u, wide, width } = useLayout();
  const cols = wide ? 3 : 2;
  const gap = 18 * u;
  const W = wide ? 1500 * u : width - 100 * u;
  const cw = (W - gap * (cols - 1)) / cols;
  const cards = [
    { k: "FastAPI", t: "Read-only /v1 forecast API, OpenAPI docs, one error shape" },
    { k: "Docker", t: "API and dashboard with docker compose" },
    { k: "CI", t: "GitHub Actions: ruff, mypy, pytest, Docker build" },
    { k: "MLflow", t: "Every backtest logged; RESULTS.md generated from the runs" },
    { k: "Tests", t: "WRMSSE vs hand-calculated values, leakage, pipeline, API contract" },
    { k: "Monitoring", t: "PSI drift and accuracy decay set a retrain flag" },
  ];
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 36 * u, padding: 50 * u }}>
        <Head eyebrow="Engineering" text="Built like a service, not a notebook." highlight={["service,"]} size={wide ? 66 : 50} />
        <div style={{ display: "flex", flexWrap: "wrap", gap, width: W }}>
          {cards.map((c, i) => (
            <FadeUp key={c.k} at={16 + i * 5}>
              <Panel style={{ width: cw, height: (wide ? 170 : 168) * u, padding: `${20 * u}px ${24 * u}px`, boxSizing: "border-box", borderTop: `5px solid ${C.gold}` }}>
                <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 30 * u, color: C.ink, letterSpacing: "-0.02em" }}>{c.k}</div>
                <div style={{ fontFamily: FONT.body, fontSize: (wide ? 22 : 21) * u, color: C.muted, lineHeight: 1.4, marginTop: 8 * u }}>{c.t}</div>
              </Panel>
            </FadeUp>
          ))}
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
