// Saves each [data-layer] element of an HTML page as its own transparent 1600x900 PNG (OUT_DIR/<layer>.png).
//
//   node docs/demo-video/render-layers.js PAGE.html OUT_DIR

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const [page_, outDir] = process.argv.slice(2);
if (!outDir) {
    console.error("usage: node render-layers.js PAGE.html OUT_DIR");
    process.exit(2);
}
fs.mkdirSync(outDir, { recursive: true });

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.goto(`file://${path.resolve(page_)}`);
    const layers = await page.$$eval("[data-layer]", (els) => els.map((el) => el.dataset.layer));
    for (const layer of layers) {
        await page.$$eval("[data-layer]", (els, keep) => els.forEach((el) => {
            el.style.visibility = el.dataset.layer === keep ? "visible" : "hidden";
        }), layer);
        await page.screenshot({ path: path.join(outDir, `${layer}.png`), omitBackground: true });
    }
    await browser.close();
})().catch((e) => {
    console.error(e);
    process.exit(1);
});
