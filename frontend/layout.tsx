import "./globals.css";

export const metadata = {
  title: "DNA Genome Analyzer",
  description: "Personal genome interpretation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
