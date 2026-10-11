import localFont from "next/font/local";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Providers } from "@/providers/Providers";
import "@/styles/globals.css";

const manrope = localFont({ src: "../../node_modules/@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2", variable: "--font-manrope", display: "swap", weight: "200 800" });
export const viewport: Viewport = { colorScheme: "light dark", width: "device-width", initialScale: 1, viewportFit: "cover" };

export const metadata: Metadata = {
  title: "Geevi | Oncology workspace",
  description: "Fictional full-stack demonstration. Development identities; not clinically validated.",
};

// Patient data is never rendered or cached on the Next.js server: pages are shells and the
// authenticated browser session fetches records from FastAPI through the same-origin proxy.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" data-scroll-behavior="smooth" className={manrope.variable} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('geevi-theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}})()` }} /></head>
      <body>
        <a className="skip-link" href="#main">Skip to main content</a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
