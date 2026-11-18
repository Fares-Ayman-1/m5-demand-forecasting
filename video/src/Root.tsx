import React from "react";
import { Composition } from "remotion";
import { Main, SCENES } from "./Main";
import { totalFrames } from "./kit/Timeline";
import { FPS } from "./kit/theme";

export const Root: React.FC = () => (
  <>
    <Composition id="Wide" component={Main} durationInFrames={totalFrames(SCENES)} fps={FPS} width={1920} height={1080} />
    <Composition id="Square" component={Main} durationInFrames={totalFrames(SCENES)} fps={FPS} width={1080} height={1080} />
  </>
);
