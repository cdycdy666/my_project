import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "陈定宇的 AI 工具与学习记录",
  description: "个人 AI 工具、学习笔记、阶段总结与资源收藏。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
