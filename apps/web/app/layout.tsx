import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AUE — Agentic Undercover Environment",
  description: "Multi-agent social deduction game simulation platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} dark h-full`}>
      <body className="min-h-full flex flex-col bg-[#0f0f11] text-[#fafafa] font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
