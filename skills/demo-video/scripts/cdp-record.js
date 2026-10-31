// Records a take in an app that is already running with a Chrome DevTools port
// (an Electron desktop app such as Paratext 10 Studio, or Chrome itself), using a
// CDP screencast of the page: no screen recorder, and nothing outside the window.
//
//     node cdp-record.js TAKE.js OUT_DIR [--port 9229] [--page TEXT] [--prep]
//
// Start the app with --remote-debugging-port=9229 first. TAKE.js exports
//   module.exports = { prep?: async (ctx) => {}, take: async (ctx) => {} }
// with ctx = { page, frames, sleep, mark }. "prep" (run with --prep) puts the app
// in its starting state off camera; "take" is the filmed part. mark("what") logs
// a timestamp to OUT_DIR/timeline.json, which you cut on in edit.json.
//
// Writes OUT_DIR/cast/ (frames.json and fNNNNN.jpg). Turn it into a video with
//     python frames2mp4.py OUT_DIR/cast OUT_DIR/take.mp4 "crop=W:H:X:Y,scale=1600:-2,pad=1600:900:0:(oh-ih)/2:color=white"
// --page picks the window whose URL contains TEXT (default: the first page).

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const opt = (name, dflt) => (args.includes(name) ? args[args.indexOf(name) + 1] : dflt);
const [takeFile, outDir] = args.filter((a, i) => !a.startsWith("--") && !["--port", "--page"].includes(args[i - 1]));
if (!takeFile || !outDir) {
    console.error("usage: node cdp-record.js TAKE.js OUT_DIR [--port 9229] [--page TEXT] [--prep]");
    process.exit(2);
}
const port = opt("--port", "9229");
const pageMatch = opt("--page", "");
const { prep, take } = require(path.resolve(takeFile));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
    const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
    const page = browser.contexts().flatMap((c) => c.pages()).find((p) => p.url().includes(pageMatch));
    if (!page) throw new Error(`No page whose URL contains "${pageMatch}"`);
    const t0 = Date.now();
    const timeline = [];
    const mark = (what) => {
        const at = +((Date.now() - t0) / 1000).toFixed(2);
        timeline.push({ at, what });
        console.log(at, what);
    };
    // Extension UIs often live in iframes; pass them along so takes can find their panel.
    const ctx = { page, frames: () => page.frames(), sleep, mark };

    if (args.includes("--prep")) {
        await prep?.(ctx);
        await page.screenshot({ path: path.join(outDir, "prep.png") });
        await browser.close().catch(() => {});
        return;
    }

    const cast = path.join(outDir, "cast");
    fs.rmSync(cast, { recursive: true, force: true });
    fs.mkdirSync(cast, { recursive: true });
    const cdp = await page.context().newCDPSession(page);
    const frames = [];
    cdp.on("Page.screencastFrame", (f) => {
        const n = frames.length;
        fs.writeFileSync(path.join(cast, `f${String(n).padStart(5, "0")}.jpg`), Buffer.from(f.data, "base64"));
        frames.push({ n, t: f.metadata.timestamp });
        cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
    });
    await cdp.send("Page.startScreencast", { format: "jpeg", quality: 95, everyNthFrame: 1 });
    mark("start");
    await take(ctx);
    mark("end");
    await cdp.send("Page.stopScreencast");
    fs.writeFileSync(path.join(cast, "frames.json"), JSON.stringify({ wallStart: t0 / 1000, frames }));
    fs.writeFileSync(path.join(outDir, "timeline.json"), JSON.stringify(timeline, null, 2));
    await browser.close().catch(() => {});
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
