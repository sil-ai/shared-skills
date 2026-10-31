// Renders an HTML page at 1600x900 for the video.
//
//   node render-layers.js PAGE.html OUT_DIR          each [data-layer] element as its own transparent PNG (OUT_DIR/<layer>.png)
//   node render-layers.js PAGE.html OUT.png --card   the whole page as one still (an end card or title card)

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const [page_, out] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const card = process.argv.includes("--card");
if (!out) {
    console.error("usage: node render-layers.js PAGE.html OUT_DIR | OUT.png --card");
    process.exit(2);
}

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.goto(pathToFileURL(path.resolve(page_)).href);
    await page.waitForLoadState("networkidle");
    if (card) {
        fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
        await page.screenshot({ path: out });
    } else {
        fs.mkdirSync(out, { recursive: true });
        const layers = await page.$$eval("[data-layer]", (els) => els.map((el) => el.dataset.layer));
        for (const layer of layers) {
            await page.$$eval("[data-layer]", (els, keep) => els.forEach((el) => {
                el.style.visibility = el.dataset.layer === keep ? "visible" : "hidden";
            }), layer);
            await page.screenshot({ path: path.join(out, `${layer}.png`), omitBackground: true });
        }
    }
    await browser.close();
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
