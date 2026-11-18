import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { CITED, CUTOFFS, HORIZON, KAGGLE, LAST_DAY, M5, MODELS_TRAINED, int } from "../data";
import { C, FONT } from "../kit/theme";
import { Callout, Chip, FadeUp, Panel, Scene, enter, progress, useLayout } from "../kit/ui";
import { Check, Head, Label, niceDate } from "./common";

/** No leakage: on day t every sales feature only sees sales up to t - 28. */
export const Leakage: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const W = wide ? 1500 * u : width - 100 * u;
  const sw = W - 64 * u; // svg width
  const K = 150; // linear part of the axis: t-150 .. t
  const x0 = (wide ? 300 : 210) * u; // start of the linear part (left of it: the break and t-364)
  const xEnd = sw - 70 * u;
  const xr = (k: number) => (k > K ? x0 - 70 * u : x0 + (1 - k / K) * (xEnd - x0));
  const lags = CITED.lags;
  const labelled = new Set([28, 35, 42, 56, 91, 364]);
  const H = 300 * u;
  const yLag = 58 * u;
  const yWin = 112 * u;
  const yAxis = 250 * u;
  const gap = enter(f, 74);
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 28 * u, padding: 50 * u }}>
        <Head eyebrow="No leakage" text="Every sales feature is at least 28 days old." highlight={["28"]} size={wide ? 64 : 46} />
        <FadeUp at={12}>
          <Panel style={{ width: W, padding: `${22 * u}px ${32 * u}px`, boxSizing: "border-box" }}>
            <svg width={sw} height={H} style={{ overflow: "visible" }}>
              {/* the 28 days before t: never used */}
              <rect x={xr(HORIZON - 0.5)} y={20 * u} width={xr(0) - xr(HORIZON - 0.5)} height={yAxis - 20 * u} fill={C.miss} opacity={0.55 * gap} rx={8 * u} />
              <text x={(xr(HORIZON) + xr(0)) / 2} y={yWin + 10 * u} textAnchor="middle" fontFamily={FONT.body} fontWeight={600} fontSize={(wide ? 20 : 17) * u} fill={C.ink} opacity={gap}>
                never used
              </text>
              <text x={(xr(HORIZON) + xr(0)) / 2} y={yWin + 36 * u} textAnchor="middle" fontFamily={FONT.body} fontSize={(wide ? 18 : 15) * u} fill={C.ink} opacity={gap}>
                {`last ${HORIZON} days`}
              </text>
              {/* row labels */}
              <text x={0} y={yLag + 6 * u} fontFamily={FONT.mono} fontSize={14 * u} fill={C.muted} letterSpacing="0.12em">
                LAGS
              </text>
              <text x={0} y={yWin + 26 * u} fontFamily={FONT.mono} fontSize={14 * u} fill={C.muted} letterSpacing="0.12em">
                ROLLING MEANS
              </text>
              {/* lag dots */}
              {lags.map((l, i) => {
                const s = enter(f, 20 + i * 3);
                return (
                  <g key={l} opacity={s}>
                    <circle cx={xr(l)} cy={yLag} r={8 * u * s} fill={C.gold} />
                    {labelled.has(l) && (
                      <text x={xr(l)} y={yLag - 18 * u} textAnchor="middle" fontFamily={FONT.mono} fontSize={14 * u} fill={C.ink}>
                        {l}
                      </text>
                    )}
                  </g>
                );
              })}
              {/* rolling windows end at t - 28 */}
              {CITED.windows.map((w, i) => {
                const g = progress(f, 40 + i * 4, 70 + i * 4);
                const xa = xr(HORIZON);
                const xb = xr(HORIZON + w);
                return <rect key={w} x={xa - (xa - xb) * g} y={yWin - 22 * u + i * 16 * u} width={(xa - xb) * g} height={10 * u} rx={5 * u} fill={C.blue} opacity={0.85} />;
              })}
              {CITED.windows.map((w, i) => (
                <text key={`l${w}`} x={xr(HORIZON + w) - 8 * u} y={yWin - 13 * u + i * 16 * u} textAnchor="end" fontFamily={FONT.mono} fontSize={11 * u} fill={C.muted} opacity={enter(f, 60 + i * 4)}>
                  {w}
                </text>
              ))}
              {/* axis */}
              <line x1={x0 - 90 * u} x2={xEnd} y1={yAxis} y2={yAxis} stroke={C.ink} strokeOpacity={0.35} strokeWidth={1.5 * u} />
              <text x={x0 - 35 * u} y={yAxis + 6 * u} textAnchor="middle" fontFamily={FONT.mono} fontSize={18 * u} fill={C.muted}>
                //
              </text>
              {[364, 112, 56, 28, 0].map((k) => (
                <g key={k}>
                  <line x1={xr(k)} x2={xr(k)} y1={yAxis - 6 * u} y2={yAxis + 6 * u} stroke={C.ink} strokeOpacity={0.5} />
                  <text x={xr(k)} y={yAxis + 30 * u} textAnchor="middle" fontFamily={FONT.mono} fontSize={14 * u} fill={k === 0 ? C.ink : C.muted} fontWeight={k === 0 ? 700 : 500}>
                    {k === 0 ? "day t" : `t − ${k}`}
                  </text>
                </g>
              ))}
              <line x1={xr(0)} x2={xr(0)} y1={10 * u} y2={yAxis} stroke={C.ink} strokeWidth={2.5 * u} />
            </svg>
          </Panel>
        </FadeUp>
        <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: 18 * u, alignItems: "stretch", width: W }}>
          <FadeUp at={96} style={{ flex: 1 }}>
            <Panel style={{ padding: `${18 * u}px ${24 * u}px`, display: "flex", gap: 18 * u, alignItems: "center", height: "100%", boxSizing: "border-box" }}>
              <Check size={40 * u} />
              <div>
                <div style={{ fontFamily: FONT.mono, fontSize: 15 * u, color: C.muted }}>tests/test_features.py · runs in CI</div>
                <div style={{ fontFamily: FONT.body, fontSize: 23 * u, color: C.ink, lineHeight: 1.35, marginTop: 4 * u }}>
                  Randomise every sale after day t − {HORIZON}: day t&apos;s features stay exactly the same.
                </div>
              </div>
            </Panel>
          </FadeUp>
          <FadeUp at={110} style={{ flex: wide ? 0.8 : undefined }}>
            <Panel style={{ padding: `${18 * u}px ${24 * u}px`, height: "100%", boxSizing: "border-box", borderLeft: `6px solid ${C.gold}`, display: "flex", alignItems: "center" }}>
              <div style={{ fontFamily: FONT.body, fontSize: 23 * u, color: C.ink, lineHeight: 1.35 }}>
                So <b>one model predicts all {HORIZON} days directly</b>, with no predictions fed back in.
              </div>
            </Panel>
          </FadeUp>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};

/** The model: one LightGBM per store, the setup, and the training time. */
export const Model: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const byState = M5.states.map((s) => ({ state: s, stores: M5.stores.filter((x) => x.startsWith(s)) }));
  const tile = (wide ? 118 : 104) * u;
  const specs = [
    { k: "Loss", v: `Tweedie, power ${CITED.tweediePower}` },
    { k: "Features", v: `${CITED.features} per row` },
    { k: "Lags", v: `${CITED.lags[0]} to ${CITED.lags[CITED.lags.length - 1]} days` },
    { k: "Rolling", v: `${CITED.windows[0]} to ${CITED.windows[CITED.windows.length - 1]}-day windows` },
    { k: "Rounds", v: int(CITED.rounds) },
  ];
  const stores = (
    <FadeUp at={10}>
      <Panel style={{ padding: `${22 * u}px ${26 * u}px`, display: "flex", flexDirection: "column", gap: 14 * u }}>
        {byState.map((g, gi) => (
          <div key={g.state} style={{ display: "flex", alignItems: "center", gap: 12 * u }}>
            <div style={{ width: 46 * u, fontFamily: FONT.mono, fontSize: 16 * u, color: C.muted }}>{g.state}</div>
            {g.stores.map((s, i) => {
              const at = 16 + (gi * 4 + i) * 3;
              const e = enter(f, at);
              return (
                <div key={s} style={{ width: tile, height: tile * 0.78, borderRadius: 14 * u, border: `1px solid ${C.line}`, background: C.card2, opacity: e, transform: `translateY(${(1 - e) * 14}px)`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 * u }}>
                  {/* a tiny tree glyph: three gold leaves on navy branches */}
                  <svg width={40 * u} height={28 * u} viewBox="0 0 40 28">
                    <path d="M20 4 L9 22 M20 4 L31 22 M20 4 L20 22" stroke={C.ink} strokeOpacity={0.45} strokeWidth={1.6} fill="none" />
                    <circle cx="20" cy="4" r="3.6" fill={C.ink} />
                    {[9, 20, 31].map((cx) => (
                      <circle key={cx} cx={cx} cy="23" r="3.6" fill={C.gold} />
                    ))}
                  </svg>
                  <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 20 * u, color: C.ink }}>{s}</div>
                </div>
              );
            })}
          </div>
        ))}
      </Panel>
    </FadeUp>
  );
  const specList = (
    <FadeUp at={40}>
      <Panel style={{ padding: `${14 * u}px ${26 * u}px`, width: wide ? 560 * u : width - 120 * u, boxSizing: "border-box" }}>
        {specs.map((s, i) => (
          <div key={s.k} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: `${(wide ? 11 : 8) * u}px 0`, borderTop: i ? `1px solid ${C.line}` : undefined, opacity: enter(f, 44 + i * 4) }}>
            <Label size={14}>{s.k}</Label>
            <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: (wide ? 26 : 23) * u, color: C.ink, letterSpacing: "-0.02em" }}>{s.v}</div>
          </div>
        ))}
      </Panel>
    </FadeUp>
  );
  const callout = (
    <Callout at={86} big={`${CITED.trainMinutes} min`} width={wide ? 1300 * u : width - 120 * u}>
      to train all {MODELS_TRAINED} models: {M5.n_stores} stores × ({CITED.backtestsPerStore} backtests + 1 final), on a 12-thread laptop CPU.
    </Callout>
  );
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: (wide ? 34 : 24) * u, padding: 50 * u }}>
        <Head eyebrow="The model" text="One LightGBM model per store." highlight={["LightGBM"]} size={wide ? 68 : 52} />
        <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: (wide ? 30 : 18) * u, alignItems: "center" }}>
          {stores}
          {specList}
        </div>
        {callout}
      </AbsoluteFill>
    </Scene>
  );
};

/** Three rolling-origin backtests and the hidden Kaggle window, on one day axis. */
export const Backtests: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const { u, wide, width } = useLayout();
  const W = wide ? 1500 * u : width - 100 * u;
  const sw = W - 64 * u;
  const labelW = (wide ? 270 : 200) * u;
  const d0 = 1760; // left edge of the axis (training continues to the left, from day 1000)
  const d1 = KAGGLE.lastDay;
  const x = (d: number) => labelW + ((d - d0) / (d1 - d0)) * (sw - labelW);
  const rowH = (wide ? 64 : 62) * u;
  const rows = [
    ...CUTOFFS.map((c, i) => ({ name: `Backtest ${i + 1}`, cut: c, hidden: false })),
    { name: "Kaggle", cut: LAST_DAY, hidden: true },
  ];
  const H = rows.length * rowH + 70 * u;
  return (
    <Scene dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 34 * u, padding: 50 * u }}>
        <Head
          eyebrow="Evaluation · rolling origin"
          text="Three backtests, rolling forward."
          highlight={["rolling"]}
          size={wide ? 68 : 54}
          sub={`Train up to a cutoff, forecast the next ${HORIZON} days, score them. Then move the cutoff.`}
        />
        <FadeUp at={14}>
          <Panel style={{ width: W, padding: `${26 * u}px ${32 * u}px`, boxSizing: "border-box" }}>
            <svg width={sw} height={H} style={{ overflow: "visible" }}>
              {rows.map((r, i) => {
                const y = i * rowH + 10 * u;
                const g = progress(f, 24 + i * 12, 60 + i * 12);
                const s = enter(f, 50 + i * 12);
                const xs = x(r.cut + 0.5);
                const xe = x(r.cut + HORIZON + 0.5);
                return (
                  <g key={r.name}>
                    <text x={0} y={y + 24 * u} fontFamily={FONT.head} fontWeight={600} fontSize={(wide ? 24 : 20) * u} fill={C.ink}>
                      {r.name}
                    </text>
                    <text x={0} y={y + 46 * u} fontFamily={FONT.mono} fontSize={13 * u} fill={C.muted}>
                      {r.hidden ? `DAYS ${KAGGLE.firstDay}–${KAGGLE.lastDay}` : `CUTOFF DAY ${r.cut}`}
                    </text>
                    {/* training span (fades in from the left edge: it starts at day 1000) */}
                    <rect x={labelW} y={y + 12 * u} width={(xs - labelW) * g} height={26 * u} rx={6 * u} fill="rgba(12,23,51,0.16)" />
                    {/* scored window */}
                    {r.hidden ? (
                      <rect x={xs + 3 * u} y={y + 12 * u} width={xe - xs - 3 * u} height={26 * u} rx={6 * u} fill={C.goldSoft} stroke={C.gold} strokeWidth={2 * u} strokeDasharray={`${6 * u} ${4 * u}`} opacity={s} />
                    ) : (
                      <rect x={xs + 3 * u} y={y + 12 * u} width={(xe - xs - 3 * u) * s} height={26 * u} rx={6 * u} fill={C.gold} />
                    )}
                  </g>
                );
              })}
              {/* axis */}
              {(() => {
                const y = rows.length * rowH + 14 * u;
                const ticks = [...CUTOFFS, LAST_DAY, KAGGLE.lastDay];
                return (
                  <g opacity={enter(f, 20)}>
                    <line x1={labelW} x2={sw} y1={y} y2={y} stroke={C.ink} strokeOpacity={0.3} />
                    {ticks.map((t) => (
                      <g key={t}>
                        <line x1={x(t + 0.5)} x2={x(t + 0.5)} y1={y - 5 * u} y2={y + 5 * u} stroke={C.ink} strokeOpacity={0.5} />
                        <text x={x(t + 0.5)} y={y + 24 * u} textAnchor="middle" fontFamily={FONT.mono} fontSize={14 * u} fill={C.ink}>
                          {t}
                        </text>
                        {wide && M5.dates[String(t)] && (
                          <text x={x(t + 0.5)} y={y + 44 * u} textAnchor="middle" fontFamily={FONT.mono} fontSize={12 * u} fill={C.muted}>
                            {niceDate(M5.dates[String(t)])}
                          </text>
                        )}
                      </g>
                    ))}
                    <text x={labelW} y={y + 24 * u} fontFamily={FONT.mono} fontSize={13 * u} fill={C.muted}>
                      {`← training from day ${int(CITED.trainStartDay)}`}
                    </text>
                  </g>
                );
              })()}
            </svg>
          </Panel>
        </FadeUp>
        <div style={{ display: "flex", gap: 14 * u, flexWrap: "wrap", justifyContent: "center" }}>
          <Chip at={96} size={18 * u} tone="gold">{`Scored: ${HORIZON} unseen days each`}</Chip>
          <Chip at={100} size={18 * u}>Hidden window: scored by Kaggle</Chip>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
