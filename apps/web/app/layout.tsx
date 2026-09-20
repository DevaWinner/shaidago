import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  applicationName: "ShaidaGo",
  title: {
    default: "ShaidaGo",
    template: "%s | ShaidaGo"
  },
  description: "Source-backed project records and safer next actions for Abuja communities.",
  formatDetection: {
    address: false,
    email: false,
    telephone: false
  }
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#F7F2E8",
  width: "device-width",
  initialScale: 1
};

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
