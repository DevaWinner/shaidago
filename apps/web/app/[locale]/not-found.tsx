import type { Route } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import en from "../../messages/en.json";
import { RecoveryPage } from "../_components/recovery-page";

const copy = en.recovery.notFound;

// Static English for now: reading the request locale here would make the page dynamic. The layout
// declares `lang="en"` for any locale without reviewed copy, and the link is `/`, which the proxy
// sends to the visitor's remembered language.
export default function NotFound(): ReactNode {
  return (
    <RecoveryPage
      title={copy.title}
      action={
        // `/` is no longer a page: the proxy redirects it, so it is not in the typed route table.
        <Link href={"/" as Route} rel="home">
          {copy.home}
        </Link>
      }
    >
      {copy.body}
    </RecoveryPage>
  );
}
