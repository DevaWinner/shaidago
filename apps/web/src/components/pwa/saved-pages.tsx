"use client";

import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";

type Copy = Messages["offline"];
type Saved = Readonly<{ href: string; title: string; savedAt: number | undefined }>;

const PAGES_CACHE = "sg-pages-v1";
const MAX_LISTED = 40;

/** Lists the public pages this browser saved, read from Cache Storage on this device only. */
export function SavedPages({
  copy,
  language
}: Readonly<{ copy: Copy; language: ApiLocale }>): ReactNode {
  const [pages, setPages] = useState<readonly Saved[] | undefined>(undefined);
  const [cleared, setCleared] = useState(false);
  const format = createFormatters(language);

  useEffect(() => {
    let live = true;
    const read = async (): Promise<void> => {
      let found: Saved[] = [];

      if ("caches" in window) {
        try {
          const cache = await caches.open(PAGES_CACHE);
          const keys = (await cache.keys()).slice(-MAX_LISTED).reverse();

          for (const key of keys) {
            // The offline page is a stand-in, not something the reader saved.
            if (new URL(key.url).pathname.endsWith("/offline")) continue;
            const response = await cache.match(key);
            const url = new URL(key.url);
            const text = response === undefined ? "" : (await response.text()).slice(0, 4000);
            const title =
              /<title[^>]*>([^<]{1,200})<\/title>/i.exec(text)?.[1]?.trim() ?? url.pathname;
            const stamp = Number(response?.headers.get("x-sg-saved-at"));

            found.push({
              href: `${url.pathname}${url.search}`,
              title,
              savedAt: Number.isFinite(stamp) && stamp > 0 ? stamp : undefined
            });
          }
        } catch {
          found = [];
        }
      }
      if (live) setPages(found);
    };

    void read();

    return () => {
      live = false;
    };
  }, []);

  async function clear(): Promise<void> {
    const registration = await navigator.serviceWorker?.getRegistration();

    registration?.active?.postMessage({ type: "CLEAR_SAVED_PAGES" });
    if ("caches" in window) await caches.delete(PAGES_CACHE);
    setCleared(true);
    setPages([]);
  }

  return (
    <section aria-labelledby="saved-pages-heading" className="grid gap-3" data-slot="saved-pages">
      <h2 className="m-0 text-ledger-lg" id="saved-pages-heading">
        {copy.savedHeading}
      </h2>
      {pages === undefined ? null : pages.length === 0 ? (
        <p className="m-0">{copy.savedNone}</p>
      ) : (
        <>
          <p className="m-0 text-sm text-muted-foreground">{copy.savedNote}</p>
          <ul className="m-0 grid list-none gap-2 p-0">
            {pages.map((page) => (
              <li className="grid gap-1 border border-border bg-card p-3" key={page.href}>
                <a className="font-semibold underline [overflow-wrap:anywhere]" href={page.href}>
                  {page.title}
                </a>
                {page.savedAt === undefined ? null : (
                  <small>
                    {formatMessageLite(copy.savedOn, {
                      date: format.dateTime(new Date(page.savedAt).toISOString())
                    })}
                  </small>
                )}
              </li>
            ))}
          </ul>
          <div>
            <Button onClick={() => void clear()} variant="secondary">
              {copy.clear}
            </Button>
          </div>
        </>
      )}
      <p aria-live="polite" className="m-0" role="status">
        {cleared ? copy.cleared : ""}
      </p>
    </section>
  );
}
