// Render the cut sheets in this folder to PNG previews in previews/.
// Needs Playwright with Chromium:  node projects/nested-hingeboxes/render_previews.js
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const here = __dirname;
const files = [];
for (const n of [6, 8, 9, 10, 12]) files.push(`sheets/sheets${n}.svg`);

(async () => {
  fs.mkdirSync(path.join(here, "previews"), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
  for (const f of files) {
    const svg = fs.readFileSync(path.join(here, f), "utf8");
    await page.setContent(
      `<html><body style="margin:0;background:#fff">` +
      `<div style="width:1400px">${svg.replace(/<\?xml[^>]*>/, "")}</div></body></html>`);
    // scale the SVG to 1400 px wide, keeping its aspect ratio
    await page.evaluate(() => {
      const s = document.querySelector("svg");
      s.setAttribute("width", "1400");
      s.removeAttribute("height");
      s.style.display = "block";
    });
    const out = path.join(here, "previews", path.basename(f).replace(/\.svg$/, ".png"));
    await page.locator("svg").screenshot({ path: out });
    console.log(out);
  }
  await browser.close();
})();
