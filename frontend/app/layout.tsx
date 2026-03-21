export const metadata = {
  title: "CBT Chatbot",
  description: "Basic psychological chatbot UI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, Noto Sans, sans-serif",
          color: "#EEF0FF",
          background:
            "linear-gradient(135deg, #2A0A5E 0%, #0B0B12 55%, #05050B 100%)",
        }}
      >
        {children}
      </body>
    </html>
  );
}

