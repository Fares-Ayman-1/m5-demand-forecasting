import React from "react";
import scenesJson from "../scenes.json";
import { CITED } from "./data";
import { Timeline, type SceneSpec } from "./kit/Timeline";
import { SeriesOutro, SeriesTitle } from "./kit/series";
import { Demo, Engineering } from "./scenes/App";
import { HookLines, Hierarchy, Problem } from "./scenes/Intro";
import { Backtests, Leakage, Model } from "./scenes/Method";
import { Forecast, Kaggle, Levels, Monitoring, Results } from "./scenes/Results";

export const SCENES = scenesJson as SceneSpec[];

// Week number of this project in the series (1-4).
const WEEK = 4;

const registry: Record<string, React.FC<{ dur: number }>> = {
  title: ({ dur }) => (
    <SeriesTitle week={WEEK} dur={dur}>
      <HookLines />
    </SeriesTitle>
  ),
  problem: Problem,
  hierarchy: Hierarchy,
  leakage: Leakage,
  model: Model,
  backtests: Backtests,
  results: Results,
  levels: Levels,
  forecast: Forecast,
  kaggle: Kaggle,
  monitoring: Monitoring,
  demo: Demo,
  engineering: Engineering,
  outro: ({ dur }) => (
    <SeriesOutro
      week={WEEK}
      dur={dur}
      repo={CITED.repo}
      kaggle={CITED.kaggle}
      scope="A research project on public competition data, not a retail system."
      credit="Data: M5 Forecasting - Accuracy (Kaggle), non-commercial use"
      visual={<HookLines faint />}
    />
  ),
};

export const Main: React.FC = () => <Timeline scenes={SCENES} registry={registry} />;
