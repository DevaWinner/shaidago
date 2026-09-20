"use client";

import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";

type Copy = Messages["offline"];

const SAVED_AT = "x-sg-saved-at";

function subscribeOnline(callback: () => void): () => void {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);

  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

/** Online/offline events and `navigator.onLine` are hints, never proof: they only choose wording. */
export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true
  );
}

/**
 * Registers the service worker (production only), says when the page is a saved copy and how old
 * it is, and announces a waiting update without applying it: an update never reloads the page on
 * its own, and on a report page it waits, so nothing typed is ever lost to it.
 */
export function PwaSupport({
  copy,
  language
}: Readonly<{ copy: Copy; language: ApiLocale }>): ReactNode {
  const online = useOnline();
  const [savedAt, setSavedAt] = useState<number | undefined>(undefined);
  const [waiting, setWaiting] = useState<ServiceWorker | undefined>(undefined);
  const [backOnline, setBackOnline] = useState(false);
  const format = createFormatters(language);

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) {
      return undefined;
    }

    let cancelled = false;

    void navigator.serviceWorker
      .register("/sw.js", { scope: "/", updateViaCache: "none" })
      .then((registration) => {
        if (cancelled) return;
        const announce = (worker: ServiceWorker | null): void => {
          if (worker !== null && navigator.serviceWorker.controller !== null) {
            setWaiting(worker);
          }
        };

        announce(registration.waiting);
        registration.addEventListener("updatefound", () => {
          const installing = registration.installing;

          installing?.addEventListener("statechange", () => {
            if (installing.state === "installed") announce(installing);
          });
        });
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let live = true;
    const lookup = async (): Promise<void> => {
      if (!("caches" in window)) return;
      try {
        const saved = await caches.match(window.location.href);
        const value = Number(saved?.headers.get(SAVED_AT));

        if (live) setSavedAt(Number.isFinite(value) && value > 0 ? value : undefined);
      } catch {
        if (live) setSavedAt(undefined);
      }
    };
    const goOffline = (): void => {
      setBackOnline(false);
      void lookup();
    };
    const goOnline = (): void => {
      setSavedAt(undefined);
      setBackOnline(true);
    };

    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    if (!navigator.onLine) void lookup();

    return () => {
      live = false;
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  const onReport = typeof window !== "undefined" && /\/report(\/|$)/.test(window.location.pathname);

  return (
    <div className="grid gap-2 empty:hidden" data-slot="pwa-support">
      <div aria-live="polite" role="status">
        {online ? (
          backOnline ? (
            <p className="m-0 text-sm">{copy.backOnline}</p>
          ) : null
        ) : (
          <p
            className="m-0 border-2 border-border bg-card p-2 text-sm font-semibold"
            data-slot="offline-banner"
          >
            {savedAt === undefined
              ? copy.bannerNoDate
              : formatMessageLite(copy.banner, {
                  date: format.dateTime(new Date(savedAt).toISOString())
                })}
          </p>
        )}
      </div>
      {waiting === undefined ? null : (
        <div
          aria-live="polite"
          className="flex flex-wrap items-center gap-3 border border-border bg-card p-2 text-sm"
          data-slot="update-notice"
          role="status"
        >
          <span>{copy.update}</span>
          {onReport ? (
            <span>{copy.updateLater}</span>
          ) : (
            <Button
              onClick={() => {
                navigator.serviceWorker.addEventListener("controllerchange", () => {
                  window.location.reload();
                });
                waiting.postMessage({ type: "SKIP_WAITING" });
              }}
              variant="secondary"
            >
              {copy.updateApply}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
