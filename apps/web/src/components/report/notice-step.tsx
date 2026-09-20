import type { ReactNode } from "react";

import type { Copy } from "@/components/report/shared";
import { Callout } from "@/components/ui/feedback";

export function NoticeStep({
  copy,
  trustHref
}: Readonly<{ copy: Copy; trustHref: string }>): ReactNode {
  return (
    <div className="grid gap-4">
      <Callout title={copy.notice.limitTitle} tone="warning">
        {copy.notice.limit}
      </Callout>
      <p className="m-0 max-w-[68ch]">{copy.notice.fictional}</p>
      <p className="m-0 max-w-[68ch]">{copy.notice.private}</p>
      <p className="m-0 max-w-[68ch]">{copy.notice.anonymous}</p>
      <p className="m-0">
        <a className="font-semibold text-ledger-accent-strong underline" href={trustHref}>
          {copy.notice.trust}
        </a>
      </p>
    </div>
  );
}
