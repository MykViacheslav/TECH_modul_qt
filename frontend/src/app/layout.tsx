import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TECH MODU Professional",
  description: "Modularny system projektowania mebli - panel inzynierski",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl">
      <body className="bg-canvas text-slate-100 antialiased" style={{ fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
