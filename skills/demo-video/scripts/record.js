// Records a scripted walkthrough of a web app for a demo video.
//
//     node record.js SCENE.json OUT_DIR [--no-video]
//
// Logs in off camera (if the scene has "login"), then plays the scene's steps at
// 1600x900 and writes video.webm, timeline.json (when each step started) and
// screenshots. --no-video plays the steps without recording, to probe inputs.
//
// Scene: {"baseUrl": "https://app.example.org", "login": {...}, "steps": [...]}.
// baseUrl can be overridden with DEMO_URL. "login" is
//   {"url": "/login/", "fields": {"#username": "$DEMO_USERNAME", "#password": "$DEMO_PASSWORD"},
//    "submit": "#loginSubmit", "settle": 3000}
// where "$NAME" values come from the environment, or a .env in the current directory or next to the scene file.
//
// Steps: {goto}, {hold}, {move: [x, y]}, {click: [x, y]}, {clickText}, {type: [css, text], enter}, {select: [css, value]},
// {scroll: px, steps}, {scrollTo: text, block}, {scrollTop}, {screenshot: name}, {note}. Any step can add "hold" (ms).

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const VIEWPORT = { width: 1600, height: 900 };

const [sceneFile, outDir] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const recordVideo = !process.argv.includes("--no-video");
if (!sceneFile || !outDir) {
    console.error("usage: node record.js SCENE.json OUT_DIR [--no-video]");
    process.exit(2);
}

function env(name) {
    if (process.env[name]) return process.env[name];
    for (const dotenv of [path.resolve(".env"), path.join(path.dirname(path.resolve(sceneFile)), ".env")]) {
        if (!fs.existsSync(dotenv)) continue;
        const line = fs.readFileSync(dotenv, "utf8").split("\n").map((l) => l.replace(/^export /, ""))
            .find((l) => l.startsWith(`${name}=`));
        if (line) return line.slice(name.length + 1).trim().replace(/^["']|["']$/g, "");
    }
    return undefined;
}

const scene = JSON.parse(fs.readFileSync(sceneFile, "utf8"));
const BASE_URL = process.env.DEMO_URL || scene.baseUrl || "";
fs.mkdirSync(outDir, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function login(browser, cfg) {
    const context = await browser.newContext({ viewport: VIEWPORT });
    const page = await context.newPage();
    await page.goto(`${BASE_URL}${cfg.url}`);
    for (const [css, value] of Object.entries(cfg.fields)) {
        const v = value.startsWith("$") ? env(value.slice(1)) : value;
        if (!v) throw new Error(`Set ${value.slice(1)} in the environment or .env.`);
        await page.fill(css, v);
    }
    await page.click(cfg.submit);
    const loginPath = new URL(`${BASE_URL}${cfg.url}`).pathname;
    await page.waitForURL((u) => u.pathname !== loginPath, { timeout: 30000 });
    // Let anything the app does after login (syncs, redirects) settle before filming.
    await sleep(cfg.settle ?? 3000);
    const state = await context.storageState();
    await context.close();
    return state;
}

// Glide the mouse to (x, y) so hovers and clicks look like a person did them.
async function glide(page, x, y, steps = 25) {
    await page.mouse.move(x, y, { steps });
}

async function smoothScroll(page, px, steps = 40) {
    for (let i = 0; i < steps; i++) {
        await page.mouse.wheel(0, px / steps);
        await sleep(16);
    }
    await sleep(300);
}

(async () => {
    const browser = await chromium.launch();
    const storageState = scene.login ? await login(browser, scene.login) : undefined;
    const context = await browser.newContext({
        viewport: VIEWPORT,
        storageState,
        ...(recordVideo ? { recordVideo: { dir: outDir, size: VIEWPORT } } : {}),
    });
    const t0 = Date.now(); // the video starts with the page, so time from just before it
    const page = await context.newPage();
    const timeline = [];
    let shot = 0;

    for (const step of scene.steps) {
        const at = (Date.now() - t0) / 1000;
        timeline.push({ at: Number(at.toFixed(2)), step });
        console.log(`[${at.toFixed(1)}s]`, JSON.stringify(step));

        if (step.goto) {
            await page.goto(`${BASE_URL}${step.goto}`);
            await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
        } else if (step.move) {
            await glide(page, ...step.move);
        } else if (step.click) {
            await glide(page, ...step.click);
            await sleep(250);
            await page.mouse.click(...step.click);
            await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
        } else if (step.clickText) {
            const el = page.getByText(step.clickText, { exact: !!step.exact }).first();
            const box = await el.boundingBox();
            if (box) await glide(page, box.x + box.width / 2, box.y + box.height / 2);
            await sleep(250);
            await el.click();
        } else if (step.type) {
            const el = page.locator(step.type[0]).first();
            const box = await el.boundingBox();
            if (box) await glide(page, box.x + box.width / 2, box.y + box.height / 2);
            await el.click();
            await page.keyboard.type(step.type[1], { delay: 110 });
            if (step.enter) await page.keyboard.press("Enter");
        } else if (step.select) {
            await page.selectOption(step.select[0], step.select[1]);
        } else if (step.scroll) {
            await smoothScroll(page, step.scroll, step.steps);
        } else if (step.scrollTo) {
            await page
                .getByText(step.scrollTo, { exact: !!step.exact })
                .first()
                .evaluate((el, block) => el.scrollIntoView({ behavior: "smooth", block }), step.block || "start");
            await sleep(1200);
        } else if (step.scrollTop) {
            await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
            await sleep(1200);
        } else if (step.screenshot) {
            await page.screenshot({ path: path.join(outDir, `${String(++shot).padStart(2, "0")}-${step.screenshot}.png`) });
        }
        if (step.hold) await sleep(step.hold);
    }

    const video = page.video();
    await context.close();
    if (video) fs.renameSync(await video.path(), path.join(outDir, "video.webm"));
    await browser.close();
    fs.writeFileSync(path.join(outDir, "timeline.json"), JSON.stringify(timeline, null, 2));
    console.log(`Done. Output in ${outDir}`);
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
