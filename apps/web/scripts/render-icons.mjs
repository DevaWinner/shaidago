/**
 * Renders the committed SVG marks in public/icons to the PNG sizes the manifest and iOS need.
 * Run with `node scripts/render-icons.mjs` after changing an SVG; the PNGs are committed so the
 * build needs no image tooling. Uses the Playwright already pinned for the browser tests.
 */
import { readFile, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const dir = new URL("../public/icons/", import.meta.url);
const jobs = [
  ["icon.svg", "icon-192.png", 192],
  ["icon.svg", "icon-512.png", 512],
  ["icon.svg", "apple-touch-icon.png", 180],
  ["icon-maskable.svg", "icon-maskable-512.png", 512]
];
const browser = await chromium.launch();

for (const [source, target, size] of jobs) {
  const svg = await readFile(new URL(source, dir), "utf8");
  const page = await browser.newPage({ viewport: { width: size, height: size } });

  await page.setContent(
    `<style>html,body{margin:0}svg{display:block;width:${size}px;height:${size}px}</style>${svg}`
  );
  await writeFile(new URL(target, dir), await page.screenshot({ omitBackground: true }));
  await page.close();
}
await browser.close();
