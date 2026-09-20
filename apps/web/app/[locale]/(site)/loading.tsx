import type { ReactNode } from "react";

import en from "../../../messages/en.json";

export default function RootLoading(): ReactNode {
  return (
    <main aria-busy="true" aria-live="polite">
      <p>{en.recovery.loading}</p>
    </main>
  );
}
