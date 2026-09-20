import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LowDataControl } from "@/components/pwa/low-data-control";
import en from "../../messages/en.json";

const copy = en.offline.lowData;

function saveData(value: boolean) {
  Object.defineProperty(navigator, "connection", {
    configurable: true,
    value: { saveData: value }
  });
}

beforeEach(() => {
  document.cookie = "sg_low_data=; Max-Age=0; Path=/";
  document.documentElement.dataset["lowData"] = "false";
  window.sessionStorage.clear();
  saveData(false);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("LowDataControl", () => {
  it("starts off, and turning it on sets one plain cookie and the page attribute", async () => {
    render(<LowDataControl copy={copy} />);
    expect(screen.getByText(copy.off)).toBeTruthy();
    await userEvent.setup().click(screen.getByRole("button", { name: copy.turnOn }));

    expect(screen.getByText(copy.on)).toBeTruthy();
    expect(document.documentElement.dataset["lowData"]).toBe("true");
    expect(document.cookie).toContain("sg_low_data=1");
    expect(screen.getByRole("button", { name: copy.turnOff }).getAttribute("aria-pressed")).toBe(
      "true"
    );
  });

  it("only suggests low-data when the browser asks to save data and no choice was made, and never turns it on itself", async () => {
    saveData(true);
    render(<LowDataControl copy={copy} />);

    expect(screen.getByText(copy.suggest)).toBeTruthy();
    expect(document.documentElement.dataset["lowData"]).toBe("false");
    await userEvent.setup().click(screen.getByRole("button", { name: copy.dismiss }));
    expect(screen.queryByText(copy.suggest)).toBeNull();
    expect(document.cookie).not.toContain("sg_low_data");
  });

  it("does not override an explicit choice: an explicit off is never suggested against", () => {
    saveData(true);
    document.cookie = "sg_low_data=0; Path=/";
    render(<LowDataControl copy={copy} />);
    expect(screen.queryByText(copy.suggest)).toBeNull();
    expect(screen.getByText(copy.off)).toBeTruthy();
  });

  it("stores nothing but the one preference cookie", async () => {
    render(<LowDataControl copy={copy} />);
    await userEvent.setup().click(screen.getByRole("button", { name: copy.turnOn }));
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });
});
