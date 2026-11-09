import { spawn } from "node:child_process";
import { writeFileSync, readFileSync } from "node:fs";

const [, , pageUrl, jobsFile, outDir] = process.argv;
const jobs = JSON.parse(readFileSync(jobsFile, "utf8"));
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9241;
const prof = outDir + "/.prof";
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${port}`, "--no-sandbox", "--hide-scrollbars",
  "--use-angle=metal", "--enable-webgl", "--ignore-gpu-blocklist", `--user-data-dir=${prof}`,
  "--window-size=1600,1000", pageUrl,
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map();
function send(method, params = {}) {
  return new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
}
async function evaluate(expr, awaitPromise = false) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise, returnByValue: true });
  if (r.result?.exceptionDetails) return "EXC " + JSON.stringify(r.result.exceptionDetails).slice(0, 400);
  return r.result?.result?.value;
}

try {
  let target;
  for (let t = 0; t < 40 && !target; t++) {
    await sleep(500);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((x) => x.type === "page"); } catch {}
  }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  await send("Runtime.enable");
  let state;
  for (let t = 0; t < 180; t++) {
    state = await evaluate("window.__state");
    if (state === "ready" || state === "error") break;
    await sleep(1000);
  }
  console.log("state", state);
  console.log("cam", JSON.stringify(await evaluate("window.__cam")));
  console.log("mats", JSON.stringify(await evaluate("window.__mats")));
  await sleep(6000);
  if (process.env.PROBE) console.log("probe", await evaluate(process.env.PROBE, true));
  for (const j of jobs) {
    if (j.setup) console.log("setup", await evaluate(`setup(${JSON.stringify(j.setup)})`, true));
    const data = await evaluate(`shot(${JSON.stringify(j.pos)}, ${JSON.stringify(j.target)}, ${j.w}, ${j.h})`, true);
    if (typeof data === "string" && data.startsWith("data:image")) {
      writeFileSync(`${outDir}/${j.name}.png`, Buffer.from(data.split(",")[1], "base64"));
      console.log("saved", j.name);
    } else console.log("fail", j.name, String(data).slice(0, 100));
  }
} finally {
  chrome.kill("SIGKILL");
}
