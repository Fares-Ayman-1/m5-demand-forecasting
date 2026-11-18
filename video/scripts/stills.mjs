// Render review stills: node scripts/stills.mjs <Composition> <frame> [<frame> ...]
// Writes out/stills/<Composition>-<frame>.png at half scale (Wide) or 0.6 (Square). One bundle, one tab.
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";

const [, , id = "Wide", ...frames] = process.argv;
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id });
for (const fr of frames) {
  const output = path.resolve(`out/stills/${id}-${String(fr).padStart(4, "0")}.png`);
  await renderStill({ composition, serveUrl, frame: Number(fr), output, scale: id.startsWith("Wide") ? 0.5 : 0.6 });
  console.log("wrote", output);
}
