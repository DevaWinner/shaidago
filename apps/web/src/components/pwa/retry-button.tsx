"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/** Reloads the page the visitor was trying to reach; the offline page is only ever a stand-in. */
export function RetryButton({ label }: Readonly<{ label: string }>): ReactNode {
  return (
    <Button
      onClick={() => {
        window.location.reload();
      }}
    >
      {label}
    </Button>
  );
}
