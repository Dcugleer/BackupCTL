import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BackupCTL - Dashboard",
  description: "Sistema empresarial de backup PostgreSQL",
  keywords: ["BackupCTL", "Backup", "PostgreSQL", "Dashboard", "Next.js", "TypeScript", "Tailwind CSS"],
  authors: [{ name: "Dcugleer" }],
  icons: {
    icon: "/logo.png",
  },
  openGraph: {
    title: "BackupCTL",
    description: "Sistema empresarial de backup PostgreSQL",
    url: "https://bnfdhszfrsxzdgfzjxvy.supabase.co",
    siteName: "BackupCTL",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "BackupCTL",
    description: "Sistema empresarial de backup PostgreSQL",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
