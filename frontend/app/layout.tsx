import type { Metadata } from "next";
import AuthGate from "@/app/ui/AuthGate";
import "./styles.css";

export const metadata: Metadata = {
  title: "Screenwise — Resume Screening",
  description: "Evidence-backed, human-reviewed resume screening",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
