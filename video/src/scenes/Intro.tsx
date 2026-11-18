import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { M5, int } from "../data";
import { C, FONT } from "../kit/theme";
import { FadeUp, Panel, Scene, enter, progress, useLayout } from "../kit/ui";
import { Head, Label, Stat, niceDate, niceTicks, pathOf, short } from "./common";

/** Hook visual: 70 store x department weekly sales lines (real data), drawn left to right. */
export const HookLines: React.FC<{ faint?: boolean }> = ({ faint }) => {
  const f = useCurrentFrame();
  const { width, height, u } = useLayout();
  const { lines, weeks } = M5.hook;
  const top = height * 0.14;
  const h = height * 0.72;
  const paths = useMemo(
    () => lines.map((row) => pathOf(row.map((v, i) => [(i / (weeks - 1)) * width, top + (1 - v) * h] as [number, number]))),
    [lines, weeks, width, top, h],
  );
  const years = [M5.first_date.slice(0, 4), M5.dates["1913"].slice(0, 4)];
  return (
    <AbsoluteFill>
      <svg width={width} height={height} style={{ position: "absolute" }}>
        {paths.map((d, i) => {
          const p = progress(f, i * 0.7, i * 0.7 + 80);
          const accent = i % 7 === 2; // FOODS_3 of each store (sorted store, dept): the busiest department
          return (
            <path
              key={i}
              d={d}
              fill="none"
              stroke={accent ? C.blue : C.ink}
              strokeOpacity={(faint ? 0.5 : 1) * (accent ? 0.55 : 0.12)}
              strokeWidth={(accent ? 1.6 : 1.1) * u}
              pathLength={1}
              strokeDasharray="1 1"
              strokeDashoffset={1 - p}
            />
          );
        })}
      </svg>
      {/* soft cream wash so the title stays readable over the lines */}
      <AbsoluteFill style={{ background: `radial-gradient(48% 40% at 50% 50%, rgba(245,241,234,0.94), rgba(245,241,234,0.55) 70%, transparent)` }} />
      {!faint && (
        <div style={{ position: "absolute", left: 48 * u, bottom: 40 * u, opacity: enter(f, 30) }}>
          <Label size={14}>{`${M5.hook.n} lines = every store × department · weekly units · ${years[0]}–${M5.last_date.slice(0, 4)} · each scaled to its own peak`}</Label>
        </div>
      )}
    </AbsoluteFill>
  );
};

/** The problem: series, stores, states, days; the real total daily sales line and the 28 days to forecast. */
export const Problem: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const W = wide ? 1560 * u : width - 120 * u;
  const tileW = wide ? 300 * u : (W - 3 * 14 * u) / 4;
  const cw = W - 64 * u; // chart inner width
  const ch = (wide ? 250 : 270) * u;
  const padL = 70 * u;
  const data = M5.total_daily;
  const nTotal = data.length + 28;
  const max = Math.max(...data);
  const ticks = niceTicks(max, 3);
  const yMax = ticks[ticks.length - 1];
  const x = (i: number) => padL + (i / (nTotal - 1)) * (cw - padL);
  const y = (v: number) => ch - (v / yMax) * ch;
  const d = pathOf(data.map((v, i) => [x(i), y(v)] as [number, number]));
  const reveal = progress(f, 40, 110);
  const fz = enter(f, 105);
  const zx = x(data.length - 0.5);
  const zw = x(nTotal - 1) - zx;
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 30 * u, padding: 50 * u }}>
        <Head eyebrow="The problem" text="Forecast every item, 28 days ahead." highlight={["28"]} />
        <div style={{ display: "flex", gap: 14 * u }}>
          <Stat at={14} w={tileW} big={int(M5.n_series)} label="item × store series" />
          <Stat at={18} w={tileW} big={String(M5.n_stores)} label="Walmart stores" />
          <Stat at={22} w={tileW} big={String(M5.n_states)} label={`states · ${M5.states.join(" ")}`} />
          <Stat at={26} w={tileW} big={int(M5.n_days)} label="days of history" />
        </div>
        <FadeUp at={30}>
          <Panel style={{ width: W, padding: `${24 * u}px ${32 * u}px ${18 * u}px`, boxSizing: "border-box" }}>
            <Label size={13} style={{ marginBottom: 12 * u }}>{`Units sold per day · all ${int(M5.n_series)} series combined`}</Label>
            <svg width={cw} height={ch + 40 * u} style={{ overflow: "visible" }}>
              {ticks.map((t) => (
                <g key={t}>
                  <line x1={padL} x2={cw} y1={y(t)} y2={y(t)} stroke={C.line} strokeWidth={1} />
                  <text x={padL - 12 * u} y={y(t) + 5 * u} textAnchor="end" fontFamily={FONT.mono} fontSize={14 * u} fill={C.muted}>
                    {short(t)}
                  </text>
                </g>
              ))}
              <defs>
                <clipPath id="rev">
                  <rect x={0} y={-10} width={padL + (cw - padL) * reveal} height={ch + 20} />
                </clipPath>
              </defs>
              <path d={d} fill="none" stroke={C.ink} strokeOpacity={0.75} strokeWidth={1.2 * u} clipPath="url(#rev)" />
              {/* the 28 days to forecast (days 1942-1969) */}
              <rect x={zx} y={0} width={Math.max(zw, 6 * u)} height={ch} fill={C.gold} opacity={0.85 * fz} rx={2 * u} />
              <text x={zx + Math.max(zw, 6 * u)} y={-12 * u} textAnchor="end" fontFamily={FONT.body} fontWeight={600} fontSize={20 * u} fill={C.ink} opacity={fz}>
                +28 days to forecast
              </text>
              <text x={padL} y={ch + 30 * u} fontFamily={FONT.mono} fontSize={14 * u} fill={C.muted}>
                {`DAY ${M5.first_day} · ${niceDate(M5.first_date)}`}
              </text>
              <text x={zx} y={ch + 30 * u} textAnchor="end" fontFamily={FONT.mono} fontSize={14 * u} fill={C.muted}>
                {`DAY ${int(M5.last_day)} · ${niceDate(M5.last_date)}`}
              </text>
            </svg>
          </Panel>
        </FadeUp>
      </AbsoluteFill>
    </Scene>
  );
};

/** WRMSSE hierarchy: 12 aggregation levels, series per level (log-scaled bars). */
export const Hierarchy: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const W = wide ? 900 * u : width - 120 * u;
  const labelW = 250 * u;
  const numW = 110 * u;
  const barW = W - 64 * u - labelW - numW;
  const maxLog = Math.log10(M5.n_series);
  const rowH = (wide ? 50 : 44) * u;
  const levelLabel: Record<string, string> = {
    total: "Total",
    state: "State",
    store: "Store",
    category: "Category",
    department: "Department",
    state_category: "State × category",
    state_department: "State × dept",
    store_category: "Store × category",
    store_department: "Store × dept",
    item: "Item",
    item_state: "Item × state",
    item_store: "Item × store",
  };
  const panel = (
    <FadeUp at={10}>
      <Panel style={{ width: W, padding: `${22 * u}px ${32 * u}px`, boxSizing: "border-box" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 * u }}>
          <Label size={13}>Aggregation level</Label>
          <Label size={13}>Series · bar on log scale</Label>
        </div>
        {M5.levels.map((lv, i) => {
          const at = 18 + i * 4;
          const s = enter(f, at);
          const g = progress(f, at + 4, at + 34);
          const bottom = i === M5.levels.length - 1;
          const w = (Math.max(Math.log10(lv.n), 0.04) / maxLog) * barW;
          return (
            <div key={lv.level} style={{ display: "flex", alignItems: "center", height: rowH, opacity: s, transform: `translateY(${(1 - s) * 12}px)`, borderTop: i ? `1px solid ${C.line}` : undefined }}>
              <div style={{ width: labelW, fontFamily: bottom ? FONT.head : FONT.body, fontWeight: bottom ? 600 : 500, fontSize: 22 * u, color: bottom ? C.ink : C.muted }}>
                <span style={{ fontFamily: FONT.mono, fontSize: 13 * u, color: C.muted, marginRight: 10 * u }}>{String(i + 1).padStart(2, "0")}</span>
                {levelLabel[lv.level] ?? lv.level}
              </div>
              <div style={{ width: barW, height: (bottom ? 16 : 11) * u, background: "rgba(12,23,51,0.05)", borderRadius: 99 }}>
                <div style={{ width: w * g, height: "100%", borderRadius: 99, background: bottom ? C.gold : "rgba(12,23,51,0.30)" }} />
              </div>
              <div style={{ width: numW, textAlign: "right", fontFamily: FONT.head, fontWeight: 600, fontSize: (bottom ? 24 : 21) * u, color: C.ink, fontVariantNumeric: "tabular-nums" }}>{int(lv.n)}</div>
            </div>
          );
        })}
      </Panel>
    </FadeUp>
  );
  const sub = (
    <>
      WRMSSE scores every level, weights each series by its dollar sales, then averages the 12. That is{" "}
      <b style={{ color: C.ink }}>{int(M5.n_level_series)} series</b> scored at once.
    </>
  );
  return (
    <Scene dur={dur}>
      {wide ? (
        <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 80 * u, padding: `0 ${100 * u}px` }}>
          <div style={{ width: 640 * u, display: "flex", flexDirection: "column", gap: 26 * u }}>
            <Head eyebrow="The metric · WRMSSE" text="One forecast, scored at 12 levels." highlight={["12"]} align="left" maxWidth={640 * u} sub={sub} />
            <FadeUp at={70}>
              <div style={{ fontFamily: FONT.body, fontSize: 24 * u, color: C.muted, lineHeight: 1.45 }}>
                Forecasts are made at <b style={{ color: C.ink }}>item × store</b> and summed up the tree.
              </div>
            </FadeUp>
          </div>
          {panel}
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 26 * u, padding: 50 * u }}>
          <Head eyebrow="The metric · WRMSSE" text="One forecast, scored at 12 levels." highlight={["12"]} size={52} sub={sub} />
          {panel}
        </AbsoluteFill>
      )}
    </Scene>
  );
};
