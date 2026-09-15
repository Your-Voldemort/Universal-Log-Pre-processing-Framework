import type { Metadata } from "next";
import { JetBrains_Mono, Noto_Sans } from "next/font/google";
import Shell from "@/components/Shell";
import "./globals.css";

// next/font downloads these at build time and self-hosts them: no runtime font fetch.
const sans = Noto_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Overview · ULPF", template: "%s · ULPF" },
  description: "Lossless, air-gapped normalization of perimeter security logs into OCSF.",
};

// Runs before first paint, so a saved light/dark choice never flashes the system theme.
const THEME_SCRIPT = `try{var t=localStorage.getItem("ulpf-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
