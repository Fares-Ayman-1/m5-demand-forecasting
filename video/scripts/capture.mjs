// Screen-record a real local app page in headless Chrome (light colour scheme) for the video's demo scene.
// Usage: node scripts/capture.mjs capture/plan.json
// plan.json: {
//   "url": "http://localhost:8501/", "out": "capture/demo.webm",
//   "viewport": {"width": 1280, "height": 800}, "scale": 2,
//   "ready": "<JS expression that is truthy when the page is ready>",
//   "warmup": "<optional async JS run before recording>",
//   "steps": [{"wait": 800}, {"click": "css selector"}, {"type": ["selector", "text"]},
//             {"js": "<async JS>"}, {"scroll": 600}, {"key": "Enter"}]
// }
// Then: ffmpeg -i capture/demo.webm -vf "fps=30,format=yuv420p" -c:v libx264 -crf 14 public/demo.mp4
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";

const plan = JSON.parse(fs.readFileSync(process.argv[2] ?? "capture/plan.json", "utf8"));
const exe = path.resolve("node_modules/.remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe");
const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ["--hide-scrollbars"] });
const page = await browser.newPage();
const vp = plan.viewport ?? { width: 1280, height: 800 };
await page.setViewport({ ...vp, deviceScaleFactor: plan.scale ?? 2 });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
await page.goto(plan.url, { waitUntil: "networkidle2", timeout: 120000 });
if (plan.ready) await page.waitForFunction(plan.ready, { timeout: 120000, polling: 250 });
if (plan.warmup) await page.evaluate(`(async () => { ${plan.warmup} })()`);

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const recorder = await page.screencast({ path: plan.out ?? "capture/demo.webm", scale: plan.scale ?? 2 });
for (const s of plan.steps ?? []) {
  if (s.wait) await wait(s.wait);
  if (s.click) await page.click(s.click);
  if (s.type) await page.type(s.type[0], s.type[1], { delay: 60 });
  if (s.key) await page.keyboard.press(s.key);
  if (s.scroll) await page.evaluate((y) => window.scrollBy({ top: y, behavior: "smooth" }), s.scroll);
  if (s.js) console.log(JSON.stringify(await page.evaluate(`(async () => { ${s.js} })()`)));
}
await recorder.stop();
await browser.close();
console.log("wrote", plan.out ?? "capture/demo.webm");
