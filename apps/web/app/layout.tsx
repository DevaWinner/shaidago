import type { ReactNode } from "react";

type RootLayoutProperties = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProperties): ReactNode {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
