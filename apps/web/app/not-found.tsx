import Link from "next/link";
import type { ReactNode } from "react";

import { RecoveryPage } from "./_components/recovery-page";

export default function NotFound(): ReactNode {
  return (
    <RecoveryPage
      title="This page is not available"
      action={
        <Link href="/" rel="home">
          Return to ShaidaGo
        </Link>
      }
    >
      Check the address or return to the main page. ShaidaGo does not confirm whether a private
      record exists.
    </RecoveryPage>
  );
}
