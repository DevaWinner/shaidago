"use client";

import { useEffect } from "react";

/**
 * After a filter or page change the URL ends in `#results`. Browsers scroll there but leave keyboard
 * focus at the top, so this moves focus to the results heading. It is the only client code the
 * directory needs; the page works fully without it.
 */
export function FocusResults(): null {
  useEffect(() => {
    if (window.location.hash === "#results") {
      document.getElementById("results")?.focus();
    }
  }, []);

  return null;
}
