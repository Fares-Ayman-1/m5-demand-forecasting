import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { CITED, CUTOFFS, FOLD_WINS, HORIZON, IMPROVEMENT, KAGGLE, LATEST_CUTOFF, LEVELS, LEVEL_LOSSES, LEVEL_WINS, M5, MEAN, MODELS, MON, PER_FOLD, fmt, int, pct, type Series } from "../data";
import { C, FONT } from "../kit/theme";
import { BarList, Chip, FadeUp, Panel, Scene, enter, progress, useLayout } from "../kit/ui";
import { Head, Label, niceDate, niceTicks, pathOf, short } from "./common";

const winDays = (cut: number) => `${cut + 1}–${cut + HORIZON}`;

/** Mean WRMSSE of the three models, then the per-window values. */
export const Results: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const barsW = wide ? 820 * u : width - 120 * u;
  const tableW = wide ? 760 * u : width - 120 * u;
  const cols = [...CUTOFFS].reverse(); // most recent first, as in RESULTS.md
  const bars = (
    <FadeUp at={12}>
      <Panel style={{ width: barsW, padding: `${26 * u}px ${34 * u}px`, boxSizing: "border-box" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 * u }}>
          <Label size={14}>Mean WRMSSE · 3 backtests</Label>
          <div style={{ fontFamily: FONT.mono, fontSize: 14 * u, color: C.ink, background: C.goldSoft, borderRadius: 99, padding: `${5 * u}px ${12 * u}px`, letterSpacing: "0.08em" }}>LOWER IS BETTER</div>
        </div>
        <BarList
          at={26}
          width={barsW - 68 * u}
          size={(wide ? 25 : 23) * u}
          max={1.1}
          rows={MODELS.map((m) => ({ label: m.label, value: MEAN[m.key], display: fmt(MEAN[m.key]), hero: m.key === "lgbm" }))}
        />
      </Panel>
    </FadeUp>
  );
  const tA = 110;
  const table = (
    <FadeUp at={tA}>
      <Panel style={{ width: tableW, padding: `${20 * u}px ${28 * u}px`, boxSizing: "border-box" }}>
        <div style={{ display: "grid", gridTemplateColumns: `1.35fr repeat(${cols.length}, 1fr)`, rowGap: 6 * u, alignItems: "center" }}>
          <Label size={12}>Window (days)</Label>
          {cols.map((c) => (
            <Label key={c} size={12} style={{ textAlign: "right" }}>
              {winDays(c)}
            </Label>
          ))}
          {MODELS.map((m, mi) => (
            <React.Fragment key={m.key}>
              <div style={{ fontFamily: m.key === "lgbm" ? FONT.head : FONT.body, fontWeight: m.key === "lgbm" ? 600 : 500, fontSize: 21 * u, color: m.key === "lgbm" ? C.ink : C.muted, paddingTop: 8 * u, borderTop: `1px solid ${C.line}` }}>{m.short}</div>
              {cols.map((c, ci) => {
                const p = PER_FOLD(c);
                const best = Math.min(p.lgbm, p.seasonal_naive, p.moving_average_28) === p[m.key];
                return (
                  <div key={c} style={{ textAlign: "right", paddingTop: 8 * u, borderTop: `1px solid ${C.line}`, opacity: enter(f, tA + 8 + mi * 4 + ci * 2) }}>
                    <span style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 22 * u, color: C.ink, fontVariantNumeric: "tabular-nums", background: best ? C.gold : undefined, borderRadius: 8 * u, padding: `${2 * u}px ${8 * u}px` }}>{fmt(p[m.key])}</span>
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 20 * u, color: C.muted, marginTop: 14 * u }}>
          LightGBM is lowest in <b style={{ color: C.ink }}>{FOLD_WINS} of {CUTOFFS.length}</b> windows.
        </div>
      </Panel>
    </FadeUp>
  );
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: (wide ? 40 : 24) * u, padding: 50 * u }}>
        <Head eyebrow="Results · all 30,490 series" text={`${pct(IMPROVEMENT)} lower error than the best baseline.`} highlight={[pct(IMPROVEMENT)]} size={wide ? 64 : 46} maxWidth={(wide ? 1500 : 960) * u} />
        <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: (wide ? 30 : 18) * u, alignItems: wide ? "flex-start" : "center" }}>
          {bars}
          {table}
        </div>
      </AbsoluteFill>
    </Scene>
  );
};

/** Per-level WRMSSE in the latest window: LightGBM vs the better baseline at each level. */
export const Levels: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const W = wide ? 1060 * u : width - 100 * u;
  const labelW = (wide ? 250 : 210) * u;
  const valW = 150 * u;
  const barW = W - 56 * u - labelW - valW;
  const max = 1.0;
  const rowH = (wide ? 56 : 52) * u;
  const losers = LEVEL_LOSSES.map((l) => l.label.toLowerCase()).join(" and ");
  const sub = (
    <>
      Seasonal naive is better at the <b style={{ color: C.ink }}>{losers}</b> levels. The top-level totals are where a simple seasonal model holds up.
    </>
  );
  const chart = (
    <FadeUp at={10}>
      <Panel style={{ width: W, padding: `${18 * u}px ${28 * u}px ${14 * u}px`, boxSizing: "border-box" }}>
        <div style={{ display: "flex", gap: 22 * u, alignItems: "center", marginBottom: 6 * u, flexWrap: "wrap" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8 * u }}>
            <span style={{ width: 22 * u, height: 10 * u, borderRadius: 9, background: C.gold }} />
            <Label size={12} color={C.ink}>LightGBM</Label>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 8 * u }}>
            <span style={{ width: 22 * u, height: 10 * u, borderRadius: 9, background: "rgba(12,23,51,0.30)" }} />
            <Label size={12} color={C.ink}>Better baseline</Label>
          </span>
          <Label size={12} style={{ marginLeft: "auto" }}>{`WRMSSE · days ${winDays(LATEST_CUTOFF)} · lower is better`}</Label>
        </div>
        {LEVELS.map((l, i) => {
          const at = 18 + i * 4;
          const g = progress(f, at, at + 36);
          const e = enter(f, at);
          return (
            <div key={l.level} style={{ display: "flex", alignItems: "center", height: rowH, borderTop: `1px solid ${C.line}`, opacity: e, background: l.win ? undefined : "rgba(255,180,168,0.28)", borderRadius: l.win ? 0 : 8 * u }}>
              <div style={{ width: labelW, paddingLeft: 8 * u, fontFamily: FONT.body, fontWeight: l.win ? 500 : 700, fontSize: 20 * u, color: l.win ? C.muted : C.ink }}>{l.label}</div>
              <div style={{ width: barW, display: "flex", flexDirection: "column", gap: 4 * u }}>
                <div style={{ width: (l.lgbm / max) * barW * g, height: 13 * u, borderRadius: 99, background: C.gold }} />
                <div style={{ width: (l.base.v / max) * barW * g, height: 9 * u, borderRadius: 99, background: "rgba(12,23,51,0.30)" }} />
              </div>
              <div style={{ width: valW, textAlign: "right", fontVariantNumeric: "tabular-nums", lineHeight: 1.1, paddingRight: 6 * u, opacity: enter(f, at + 20) }}>
                <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 19 * u, color: C.ink }}>{fmt(l.lgbm)}</div>
                <div style={{ fontFamily: FONT.mono, fontSize: 13 * u, color: C.muted }}>
                  {l.base.key === "seasonal_naive" ? "SN" : "MA"} {fmt(l.base.v)}
                </div>
              </div>
            </div>
          );
        })}
        <div style={{ display: "flex", marginLeft: labelW, width: barW, justifyContent: "space-between", paddingTop: 6 * u, borderTop: `1px solid ${C.line}` }}>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <span key={t} style={{ fontFamily: FONT.mono, fontSize: 12 * u, color: C.muted, width: 0, display: "flex", justifyContent: "center" }}>
              {t.toFixed(2)}
            </span>
          ))}
        </div>
      </Panel>
    </FadeUp>
  );
  return (
    <Scene dur={dur}>
      {wide ? (
        <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 70 * u, padding: `0 ${90 * u}px` }}>
          <div style={{ width: 560 * u, display: "flex", flexDirection: "column", gap: 24 * u }}>
            <Head eyebrow="Per level, honestly" text={`Best at ${LEVEL_WINS} of ${LEVELS.length} levels.`} highlight={[String(LEVEL_WINS)]} align="left" size={66} maxWidth={560 * u} sub={sub} />
            <FadeUp at={80}>
              <div style={{ fontFamily: FONT.mono, fontSize: 14 * u, color: C.muted, lineHeight: 1.6 }}>SN = seasonal naive · MA = moving average 28</div>
            </FadeUp>
          </div>
          {chart}
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 20 * u, padding: `${36 * u}px ${50 * u}px` }}>
          <Head eyebrow="Per level, honestly" text={`Best at ${LEVEL_WINS} of ${LEVELS.length} levels.`} highlight={[String(LEVEL_WINS)]} size={50} sub={sub} />
          {chart}
        </AbsoluteFill>
      )}
    </Scene>
  );
};

/** One line chart: history before the cutoff, then actual vs forecast in the backtest window. */
const ForecastChart: React.FC<{ s: Series; w: number; h: number; at: number; title: string; note: string }> = ({ s, w, h, at, title, note }) => {
  const f = useCurrentFrame();
  const { u } = useLayout();
  const nH = s.history.length;
  const n = nH + s.actual.length;
  const padL = 58 * u;
  const padB = 34 * u;
  const ch = h - padB;
  const ticks = niceTicks(Math.max(...s.history, ...s.actual, ...s.pred), 3);
  const yMax = ticks[ticks.length - 1];
  const x = (i: number) => padL + (i / (n - 1)) * (w - padL);
  const y = (v: number) => ch - (v / yMax) * ch;
  const hist = pathOf(s.history.map((v, i) => [x(i), y(v)] as [number, number]));
  const act = pathOf([[x(nH - 1), y(s.history[nH - 1])], ...s.actual.map((v, i) => [x(nH + i), y(v)] as [number, number])]);
  const pred = pathOf(s.pred.map((v, i) => [x(nH + i), y(v)] as [number, number]));
  const r1 = progress(f, at, at + 40);
  const r2 = progress(f, at + 40, at + 95);
  const xc = x(nH - 0.5);
  const cutoff = M5.fold.cutoff;
  const id = title.replace(/\W/g, "");
  return (
    <div>
      <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 24 * u, color: C.ink, letterSpacing: "-0.02em" }}>{title}</div>
      <div style={{ fontFamily: FONT.body, fontSize: 18 * u, color: C.muted, marginBottom: 12 * u }}>{note}</div>
      <svg width={w} height={h} style={{ overflow: "visible" }}>
        <defs>
          <clipPath id={`h${id}`}>
            <rect x={0} y={-20} width={padL + (xc - padL) * r1} height={h + 40} />
          </clipPath>
          <clipPath id={`w${id}`}>
            <rect x={xc} y={-20} width={(w - xc) * r2} height={h + 40} />
          </clipPath>
        </defs>
        <rect x={xc} y={0} width={w - xc} height={ch} fill={C.goldSoft} opacity={enter(f, at + 30)} />
        {ticks.map((t) => (
          <g key={t}>
            <line x1={padL} x2={w} y1={y(t)} y2={y(t)} stroke={C.line} />
            <text x={padL - 10 * u} y={y(t) + 5 * u} textAnchor="end" fontFamily={FONT.mono} fontSize={13 * u} fill={C.muted}>
              {short(t)}
            </text>
          </g>
        ))}
        <line x1={xc} x2={xc} y1={0} y2={ch} stroke={C.gold} strokeWidth={3 * u} opacity={enter(f, at + 30)} />
        <path d={hist} fill="none" stroke={C.ink} strokeOpacity={0.45} strokeWidth={2 * u} clipPath={`url(#h${id})`} />
        <path d={act} fill="none" stroke={C.ink} strokeWidth={2.4 * u} clipPath={`url(#w${id})`} />
        <path d={pred} fill="none" stroke={C.blue} strokeWidth={3.6 * u} strokeLinejoin="round" clipPath={`url(#w${id})`} />
        {[
          { i: 0, d: cutoff - nH + 1, anchor: "start" as const },
          { i: nH - 0.5, d: cutoff, anchor: "middle" as const },
          { i: n - 1, d: cutoff + s.actual.length, anchor: "end" as const },
        ].map((t) => (
          <text key={t.d} x={x(t.i)} y={ch + 24 * u} textAnchor={t.anchor} fontFamily={FONT.mono} fontSize={13 * u} fill={t.d === cutoff ? C.ink : C.muted}>
            {`${t.d === cutoff ? "CUTOFF · " : ""}${niceDate(M5.dates[String(t.d)] ?? "", false)}`}
          </text>
        ))}
      </svg>
    </div>
  );
};

export const Forecast: React.FC<{ dur: number }> = ({ dur }) => {
  const { u, wide, width } = useLayout();
  const fo = M5.fold;
  const parts = fo.item.id.split("_"); // FOODS_3_090_CA_3 -> item FOODS_3_090, store CA_3
  const item = parts.slice(0, 3).join("_");
  const store = parts.slice(3).join("_");
  const pw = wide ? 800 * u : width - 100 * u;
  const cw = pw - 56 * u;
  const ch = (wide ? 360 : 230) * u;
  const legend = (
    <FadeUp at={60}>
      <div style={{ display: "flex", gap: 28 * u, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
        {[
          { c: C.ink, o: 0.45, t: `History (${fo.context_days} days)` },
          { c: C.ink, o: 1, t: "What sold" },
          { c: C.blue, o: 1, t: "Forecast made at the cutoff" },
        ].map((l) => (
          <span key={l.t} style={{ display: "flex", alignItems: "center", gap: 10 * u }}>
            <span style={{ width: 30 * u, height: 4 * u, borderRadius: 4, background: l.c, opacity: l.o }} />
            <span style={{ fontFamily: FONT.body, fontSize: 20 * u, color: C.ink }}>{l.t}</span>
          </span>
        ))}
        <span style={{ display: "flex", alignItems: "center", gap: 10 * u }}>
          <span style={{ width: 22 * u, height: 16 * u, borderRadius: 4, background: C.goldSoft, borderLeft: `3px solid ${C.gold}` }} />
          <span style={{ fontFamily: FONT.body, fontSize: 20 * u, color: C.ink }}>{`Backtest, days ${winDays(fo.cutoff)}`}</span>
        </span>
      </div>
    </FadeUp>
  );
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: (wide ? 30 : 18) * u, padding: `${36 * u}px ${50 * u}px` }}>
        <Head eyebrow="Forecast vs actual · most recent backtest" text="Forecast against what really sold." highlight={["really"]} size={wide ? 64 : 48} />
        <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: (wide ? 28 : 14) * u }}>
          <FadeUp at={10}>
            <Panel style={{ width: pw, padding: `${18 * u}px ${28 * u}px`, boxSizing: "border-box" }}>
              <ForecastChart s={fo.total} w={cw} h={ch} at={20} title={`All ${int(M5.n_series)} series, summed`} note="Units per day" />
            </Panel>
          </FadeUp>
          <FadeUp at={22}>
            <Panel style={{ width: pw, padding: `${18 * u}px ${28 * u}px`, boxSizing: "border-box" }}>
              <ForecastChart s={fo.item} w={cw} h={ch} at={34} title={`${item} at store ${store}`} note={`Units per day · the series with the ${fo.item.why}`} />
            </Panel>
          </FadeUp>
        </div>
        {legend}
      </AbsoluteFill>
    </Scene>
  );
};

/** Kaggle private leaderboard on the hidden 28 days. */
export const Kaggle: React.FC<{ dur: number }> = ({ dur }) => {
  const { u, wide } = useLayout();
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 30 * u, padding: 60 * u }}>
        <Head eyebrow="Kaggle · late submission" text={`Kaggle scored the hidden ${HORIZON} days.`} highlight={["hidden"]} size={wide ? 66 : 52} />
        <FadeUp at={24}>
          <Panel float style={{ padding: `${30 * u}px ${60 * u}px`, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 * u, borderTop: `6px solid ${C.gold}` }}>
            <Label size={15}>Private leaderboard · WRMSSE</Label>
            <div style={{ fontFamily: FONT.head, fontWeight: 700, fontSize: (wide ? 190 : 160) * u, color: C.ink, letterSpacing: "-0.05em", lineHeight: 1 }}>{KAGGLE.private}</div>
            <Label size={14}>Lower is better</Label>
          </Panel>
        </FadeUp>
        <div style={{ display: "flex", gap: 14 * u, flexWrap: "wrap", justifyContent: "center", maxWidth: 960 * u }}>
          <Chip at={44} size={19 * u} tone="gold">{`Days ${KAGGLE.firstDay}–${KAGGLE.lastDay}`}</Chip>
          <Chip at={48} size={19 * u}>{`${niceDate(M5.dates[String(KAGGLE.firstDay)])} – ${niceDate(M5.dates[String(KAGGLE.lastDay)])}`}</Chip>
          <Chip at={52} size={19 * u}>{`Submitted ${niceDate(KAGGLE.date)}`}</Chip>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};

/** A gauge from 0 to 2x the alert threshold, with the threshold marked. */
const Gauge: React.FC<{ value: number; alert: number; at: number; w: number; over: boolean; mark: string }> = ({ value, alert, at, w, over, mark }) => {
  const f = useCurrentFrame();
  const { u } = useLayout();
  const max = alert * 2;
  const g = progress(f, at, at + 36);
  const fill = Math.min(value / max, 1) * w * g;
  return (
    <div style={{ position: "relative", width: w, height: 30 * u, marginTop: 10 * u, marginBottom: 22 * u }}>
      <div style={{ position: "absolute", top: 8 * u, width: w, height: 14 * u, borderRadius: 99, background: "rgba(12,23,51,0.07)" }} />
      <div style={{ position: "absolute", top: 8 * u, width: Math.max(fill, value > 0 ? 3 * u * g : 0), height: 14 * u, borderRadius: 99, background: over ? C.miss : C.green }} />
      <div style={{ position: "absolute", left: w / 2 - 1.5 * u, top: 0, width: 3 * u, height: 30 * u, background: C.ink, borderRadius: 2 }} />
      <div style={{ position: "absolute", left: w / 2, top: 32 * u, transform: "translateX(-50%)", fontFamily: FONT.mono, fontSize: 13 * u, color: C.ink, whiteSpace: "nowrap" }}>{`alert ${mark}`}</div>
      <div style={{ position: "absolute", left: 0, top: 32 * u, fontFamily: FONT.mono, fontSize: 13 * u, color: C.muted }}>0</div>
    </div>
  );
};

export const Monitoring: React.FC<{ dur: number }> = ({ dur }) => {
  const { u, wide, width } = useLayout();
  const cardW = wide ? 480 * u : width - 100 * u;
  const gw = cardW - 56 * u;
  const cards = [
    { k: "Sales drift · PSI", big: MON.salesPsi.toFixed(5), v: MON.salesPsi, alert: CITED.psiAlert, over: MON.salesPsi > CITED.psiAlert, mark: `> ${CITED.psiAlert}`, note: "Daily unit sales, latest 28 days vs the 28 before" },
    { k: "Price drift · PSI", big: MON.pricePsi.toFixed(5), v: MON.pricePsi, alert: CITED.psiAlert, over: MON.pricePsi > CITED.psiAlert, mark: `> ${CITED.psiAlert}`, note: "Sell prices, same two windows" },
    { k: "Error · latest window", big: `+${pct(MON.change)}`, v: MON.change, alert: CITED.decayAlert, over: MON.accuracyAlert, mark: `> +${pct(CITED.decayAlert, 0)}`, note: "WRMSSE vs the mean of the two earlier backtests" },
  ];
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: (wide ? 36 : 20) * u, padding: `${36 * u}px ${50 * u}px` }}>
        <Head
          eyebrow={`Monitoring · days ${MON.current[0]}–${MON.current[1]} vs ${MON.reference[0]}–${MON.reference[1]}`}
          text="Low drift is not low error."
          highlight={["not"]}
          size={wide ? 68 : 52}
          sub={`The inputs barely moved, yet the latest window is ${pct(MON.change, 0)} harder to forecast.`}
        />
        <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: (wide ? 24 : 12) * u }}>
          {cards.map((c, i) => (
            <FadeUp key={c.k} at={22 + i * 10}>
              <Panel style={{ width: cardW, padding: `${(wide ? 22 : 14) * u}px ${28 * u}px`, boxSizing: "border-box", borderTop: wide ? `5px solid ${c.over ? C.miss : C.green}` : undefined, borderLeft: wide ? undefined : `6px solid ${c.over ? C.miss : C.green}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <Label size={13} color={C.ink}>{c.k}</Label>
                  <Label size={12}>{c.over ? "Alert" : "No alert"}</Label>
                </div>
                <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: (wide ? 58 : 44) * u, color: C.ink, letterSpacing: "-0.04em", lineHeight: 1.1, marginTop: 4 * u }}>{c.big}</div>
                <Gauge value={c.v} alert={c.alert} at={34 + i * 10} w={gw} over={c.over} mark={c.mark} />
                <div style={{ fontFamily: FONT.body, fontSize: 17 * u, color: C.muted, marginTop: 6 * u }}>{c.note}</div>
              </Panel>
            </FadeUp>
          ))}
        </div>
        <div style={{ display: "flex", gap: 14 * u, alignItems: "center" }}>
          <Chip at={80} size={21 * u} tone="gold">{`retrain_recommended: ${MON.retrain}`}</Chip>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
