import type { ReactNode } from "react";

export default function RootLoading(): ReactNode {
  return (
    <main aria-busy="true" aria-live="polite">
      <p>Preparing this page.</p>
    </main>
  );
}
