import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const PAGES: Record<string, string> = {
  "full record": "projects/synthetic-record-full",
  "minimal record": "projects/synthetic-record-minimal",
  "unreachable source":
    "projects/synthetic-record-full/sources/00000000-0000-4000-8000-000000000002",
  "missing source": "projects/synthetic-record-full/sources/00000000-0000-4000-8000-0000000000ff",
  trust: "trust"
};

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

for (const locale of LOCALES) {
  for (const [name, path] of Object.entries(PAGES)) {
    test(`${locale} ${name}: no axe violations, reflows at 320 px and 200% text`, async ({
      page
    }) => {
      await page.goto(`/${locale}/${path}`);

      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
      await page.setViewportSize({ width: 320, height: 800 });
      expect(await overflow(page)).toBeLessThanOrEqual(0);
      await page.setViewportSize({ width: 640, height: 800 });
      await page.evaluate(() => {
        document.documentElement.style.fontSize = "200%";
      });
      expect(await overflow(page)).toBeLessThanOrEqual(0);
    });
  }
}
