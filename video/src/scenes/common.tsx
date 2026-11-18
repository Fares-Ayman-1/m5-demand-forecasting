import React from "react";
import { useCurrentFrame } from "remotion";
import { C, FONT } from "../kit/theme";
import { Eyebrow, FadeUp, Words, enter, progress, useLayout } from "../kit/ui";

/** Eyebrow + headline (one gold-highlighted word) + optional muted sub line. */
export const Head: React.FC<{
  eyebrow: string;
  text: string;
  highlight: string[];
  sub?: React.ReactNode;
  at?: number;
  align?: "left" | "center";
  size?: number;
  maxWidth?: number;
}> = ({ eyebrow, text, highlight, sub, at = 0, align, size, maxWidth }) => {
  const { u, wide, width } = useLayout();
  const al = align ?? "center";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: al === "center" ? "center" : "flex-start", gap: 18 * u }}>
      <Eyebrow at={at} size={17 * u}>
        {eyebrow}
      </Eyebrow>
      <Words text={text} at={at + 4} size={(size ?? (wide ? 68 : 56)) * u} highlight={highlight} align={al} maxWidth={maxWidth ?? width - 120 * u} />
      {sub && (
        <FadeUp at={at + 16}>
          <div style={{ fontFamily: FONT.body, fontSize: (wide ? 27 : 25) * u, color: C.muted, lineHeight: 1.45, textAlign: al, maxWidth: maxWidth ?? width - 140 * u }}>{sub}</div>
        </FadeUp>
      )}
    </div>
  );
};

/** Small stat tile: big navy number + mono label. */
export const Stat: React.FC<{ big: string; label: string; at: number; w: number }> = ({ big, label, at, w }) => {
  const { u } = useLayout();
  return (
    <FadeUp at={at}>
      <div style={{ width: w, background: C.card, border: `1px solid ${C.line}`, borderRadius: 18 * u, padding: `${16 * u}px ${18 * u}px`, boxSizing: "border-box", borderTop: `5px solid ${C.gold}` }}>
        <div style={{ fontFamily: FONT.head, fontWeight: 600, fontSize: 46 * u, color: C.ink, letterSpacing: "-0.04em", lineHeight: 1.05 }}>{big}</div>
        <div style={{ fontFamily: FONT.mono, fontSize: 14 * u, color: C.muted, letterSpacing: "0.12em", textTransform: "uppercase", marginTop: 6 * u }}>{label}</div>
      </div>
    </FadeUp>
  );
};

/** Mono uppercase label. */
export const Label: React.FC<{ children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties }> = ({ children, size = 14, color = C.muted, style }) => {
  const { u } = useLayout();
  return <div style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: size * u, letterSpacing: "0.14em", textTransform: "uppercase", color, ...style }}>{children}</div>;
};

/** "Nice" axis ticks from 0 to >= max. */
export const niceTicks = (max: number, n = 4): number[] => {
  const raw = max / n;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = 0; v <= max + step * 0.999; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return out;
};

export const short = (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}k` : String(v));

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2016-04-24" -> "24 Apr 2016" (or without the year). */
export const niceDate = (iso: string, year = true) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}${year ? ` ${y}` : ""}`;
};

/** SVG path through points. */
export const pathOf = (pts: [number, number][]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");

/** Animated reveal width (0..1) helper. */
export const useReveal = (a: number, b: number) => progress(useCurrentFrame(), a, b);
export const useEnter = (at: number) => enter(useCurrentFrame(), at);

/** A green tick in a filled circle (data-illustration green), navy check mark. */
export const Check: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="12" fill={C.green} />
    <path d="M6.5 12.5l3.5 3.5 7.5-8" stroke={C.ink} strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
