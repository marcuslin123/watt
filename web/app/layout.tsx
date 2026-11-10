import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Watt | Portfolio workspace",
  description: "Trace the economics of a retail electricity portfolio."
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
