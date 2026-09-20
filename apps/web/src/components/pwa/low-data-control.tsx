"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Messages } from "@/i18n/catalogue";
import {
  LOW_DATA_EVENT,
  applyLowData,
  browserAsksToSaveData,
  isLowData,
  readLowDataChoice
} from "@/lib/low-data";

type Copy = Messages["offline"]["lowData"];

const DISMISSED = "sg-low-data-dismissed";

function suggestionSnapshot(): boolean {
  let dismissed = false;

  try {
    dismissed = window.sessionStorage.getItem(DISMISSED) === "1";
  } catch {
    dismissed = false;
  }

  return (
    !isLowData() &&
    !dismissed &&
    readLowDataChoice(document.cookie) === "unset" &&
    browserAsksToSaveData()
  );
}

function subscribe(callback: () => void): () => void {
  window.addEventListener(LOW_DATA_EVENT, callback);

  return () => {
    window.removeEventListener(LOW_DATA_EVENT, callback);
  };
}

/**
 * The low-data switch. The mode changes only cost, never content: motion, background refreshing,
 * and polling frequency drop, while every fact and action stays. The browser's data-saving signal
 * only produces a suggestion that can be declined, and an explicit choice is never overridden.
 */
export function LowDataControl({ copy }: Readonly<{ copy: Copy }>): ReactNode {
  const on = useSyncExternalStore(subscribe, isLowData, () => false);
  const [, refresh] = useState(0);
  // Read after hydration only (the server snapshot is always false), so it can never mismatch.
  const suggest = useSyncExternalStore(subscribe, suggestionSnapshot, () => false);

  return (
    <div className="grid gap-2 text-sm" data-slot="low-data">
      {suggest ? (
        <div
          className="flex flex-wrap items-center gap-3 border border-border bg-card p-2"
          role="status"
        >
          <span>{copy.suggest}</span>
          <Button
            onClick={() => {
              applyLowData(true);
            }}
            variant="secondary"
          >
            {copy.turnOn}
          </Button>
          <Button
            onClick={() => {
              try {
                window.sessionStorage.setItem(DISMISSED, "1");
              } catch {
                // A blocked store only means the suggestion may reappear.
              }
              refresh((value) => value + 1);
              window.dispatchEvent(new Event(LOW_DATA_EVENT));
            }}
            variant="secondary"
          >
            {copy.dismiss}
          </Button>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <span aria-live="polite" role="status">
          {on ? copy.on : copy.off}
        </span>
        <Button
          aria-pressed={on}
          onClick={() => {
            applyLowData(!on);
          }}
          variant="secondary"
        >
          {on ? copy.turnOff : copy.turnOn}
        </Button>
      </div>
      <small className="text-muted-foreground">{copy.note}</small>
    </div>
  );
}
