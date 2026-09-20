import type { Route } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { RecoveryPage } from "../_components/recovery-page";

// The link is `/`, not a locale path: the proxy sends it to the visitor's remembered language, and
// avoiding a per-request locale lookup keeps this page static (no headers read at render time).
export default function NotFound(): ReactNode {
  return (
    <RecoveryPage
      title="This page is not available"
      action={
        // `/` is no longer a page: the proxy redirects it, so it is not in the typed route table.
        <Link href={"/" as Route} rel="home">
          Return to ShaidaGo
        </Link>
      }
    >
      Check the address or return to the main page. ShaidaGo does not confirm whether a private
      record exists.
    </RecoveryPage>
  );
}
