/**
 * The low-data preference: one functional cookie, `sg_low_data`, holding `1` or `0`. It contains no
 * identifier and no personal data, is readable by the page so the mode applies before first paint,
 * is never sent to any API, and lasts a year. The browser's data-saving signal is only ever a
 * suggestion: an explicit choice (either value) always wins, and the signal never turns the mode on
 * by itself.
 */
export const LOW_DATA_COOKIE = "sg_low_data";
export const LOW_DATA_EVENT = "sg-low-data-change";
const ONE_YEAR_SECONDS = 365 * 24 * 60 * 60;

export type LowDataChoice = "on" | "off" | "unset";

export function readLowDataChoice(cookieHeader: string): LowDataChoice {
  for (const part of cookieHeader.split(";")) {
    const [name, value] = part.trim().split("=");

    if (name === LOW_DATA_COOKIE) {
      return value === "1" ? "on" : value === "0" ? "off" : "unset";
    }
  }

  return "unset";
}

export function lowDataCookie(on: boolean, secure: boolean): string {
  return `${LOW_DATA_COOKIE}=${on ? "1" : "0"}; Path=/; Max-Age=${ONE_YEAR_SECONDS}; SameSite=Lax${secure ? "; Secure" : ""}`;
}

/** Whether the page is currently in low-data mode (set on `<html>` before paint by the head script). */
export function isLowData(): boolean {
  return typeof document !== "undefined" && document.documentElement.dataset["lowData"] === "true";
}

export function applyLowData(on: boolean): void {
  document.documentElement.dataset["lowData"] = on ? "true" : "false";
  document.cookie = lowDataCookie(on, window.location.protocol === "https:");
  window.dispatchEvent(new Event(LOW_DATA_EVENT));
  void navigator.serviceWorker?.ready
    .then((registration) => registration.active?.postMessage({ type: "LOW_DATA", value: on }))
    .catch(() => undefined);
}

/** A saved-data hint from the browser, when it offers one. Only ever a suggestion. */
export function browserAsksToSaveData(): boolean {
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;

  return connection?.saveData === true;
}

/** Polling and other optional refreshes wait twice as long in low-data mode. */
export function scaleDelay(milliseconds: number): number {
  return isLowData() ? milliseconds * 2 : milliseconds;
}

/**
 * The tiny script that applies the stored choice before first paint, so there is no flash. It only
 * reads the cookie above and sets one attribute; it contains no data and makes no request.
 */
export const LOW_DATA_HEAD_SCRIPT = `try{var m=document.cookie.match(/(?:^|; )${LOW_DATA_COOKIE}=([01])/);document.documentElement.dataset.lowData=m&&m[1]==="1"?"true":"false"}catch(e){}`;
