import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const QUESTIONS: Record<string, string> = {
  idle: "",
  answer: "What is planned?",
  "several sources": "__conflict",
  insufficient: "__insufficient",
  rejected: "__unknown_citation",
  outage: "__unavailable",
  "rate limited": "__ratelimit",
  "long text": "__long"
};

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

for (const locale of LOCALES) {
  for (const [name, question] of Object.entries(QUESTIONS)) {
    test(`${locale} question (${name}): no axe violations, reflows at 320 px and 200% text`, async ({
      page
    }) => {
      await page.goto(`/${locale}/projects/synthetic-record-full`);

      if (question !== "") {
        const form = page.locator("[data-slot=project-question]");
        await form.locator("textarea").fill(question);
        const submit = form.locator("button[type=submit]");
        await expect(submit).toBeEnabled();
        await submit.click();
        await expect(form.locator("[data-slot=question-result] > *").first()).toBeVisible();
      }

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

test("the question field has a programmatic label, description, and 44 px controls; reduced motion adds no animation", async ({
  page
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/en/projects/synthetic-record-full");

  const field = page.getByLabel("Your question");
  await expect(field).toHaveAttribute("aria-describedby", /.+/);
  const box = await page.getByRole("button", { name: "Ask the sources" }).boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  const animated = await page.evaluate(
    () =>
      [...document.querySelectorAll("[data-slot=project-question] *")].filter((element) => {
        const style = getComputedStyle(element);
        return style.animationName !== "none" || parseFloat(style.transitionDuration) > 0;
      }).length
  );
  expect(animated).toBe(0);
});
