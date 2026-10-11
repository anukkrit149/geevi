import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Providers } from "@/providers/Providers";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Geevi — oncology department journey (fictional demonstration)",
  description: "Fictional full-stack demonstration. Development identities; not clinically validated.",
};

// Patient data is never rendered or cached on the Next.js server: pages are shells and the
// authenticated browser session fetches records from FastAPI through the same-origin proxy.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">Skip to main content</a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
