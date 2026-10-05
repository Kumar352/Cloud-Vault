import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudVault",
  description: "Local-first secure file collaboration portfolio project",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
