import type { ReactNode } from "react";

type RecoveryPageProperties = Readonly<{
  title: string;
  children: ReactNode;
  reference?: string | undefined;
  action?: ReactNode | undefined;
}>;

export function RecoveryPage({
  title,
  children,
  reference,
  action
}: RecoveryPageProperties): ReactNode {
  return (
    <main aria-labelledby="recovery-title">
      <h1 id="recovery-title">{title}</h1>
      <p>{children}</p>
      {reference ? <p>Support reference: {reference}</p> : null}
      {action}
    </main>
  );
}
