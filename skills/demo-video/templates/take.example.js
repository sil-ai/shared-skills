// A desktop-app take for cdp-record.js (here, a panel inside an Electron app).
//   node cdp-record.js take.example.js OUT_DIR --page isMainWindow --prep   # set the starting state, check prep.png
//   node cdp-record.js take.example.js OUT_DIR --page isMainWindow          # film it

// Extension panels usually live in an iframe: find the one that shows the text you need.
async function panel(ctx) {
    for (const f of ctx.frames()) {
        const t = await f.evaluate(() => document.body?.innerText || "").catch(() => "");
        if (t.includes("Findings")) return f;
    }
    throw new Error("panel not found");
}

const smooth = (loc, block = "start") => loc.evaluate((el, block) => el.scrollIntoView({ behavior: "smooth", block }), block);
const offCamera = (page) => page.mouse.move(5, 500); // park the pointer so it doesn't trigger tooltips

module.exports = {
    // Off camera: close anything a previous take left open, scroll to the top, drop focus
    // (a focused button shows a tooltip in the first seconds of the take).
    async prep(ctx) {
        const p = await panel(ctx);
        await p.evaluate(() => document.querySelectorAll("*").forEach((el) => { if (el.scrollHeight > el.clientHeight + 5) el.scrollTop = 0; }));
        await p.evaluate(() => document.activeElement?.blur());
        await offCamera(ctx.page);
    },

    async take(ctx) {
        const { page, sleep, mark } = ctx;
        const p = await panel(ctx);
        await p.evaluate(() => document.activeElement?.blur());
        await offCamera(page);
        await sleep(4000);

        mark("open first finding");
        const first = p.getByText("first finding text", { exact: false }).first();
        await first.click();
        await offCamera(page);
        await sleep(7000);

        // Toggles keep their state between takes: check before clicking.
        mark("why");
        if (!(await p.getByText("text only shown when expanded", { exact: false }).count())) {
            await p.getByText("Why", { exact: false }).first().click();
        }
        await smooth(first);
        await sleep(6000);

        mark("answers");
        await p.getByText("Yes", { exact: false }).first().hover(); // hover, never click: don't change real data
        await sleep(1500);
    },
};
