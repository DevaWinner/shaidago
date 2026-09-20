import type { ReactNode } from "react";

import { RECOVERY } from "@/lib/recovery-copy";

/** A private page is streaming in. Nothing about the report is known here, so nothing is shown. */
export default function ReviewerLoading(): ReactNode {
  return (
    <p className="m-0 p-6" role="status">
      {RECOVERY.loading}
    </p>
  );
}
