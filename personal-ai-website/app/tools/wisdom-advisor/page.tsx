import Link from "next/link";
import type { Metadata } from "next";
import { WisdomAdvisorStudio } from "../../../components/WisdomAdvisorStudio";

export const metadata: Metadata = {
  title: "沟通锦囊顾问 | 陈定宇",
  description: "把真实处境讲出来，获得基于沟通资料库的判断、动作建议和避坑提醒。",
};

export default function WisdomAdvisorPage() {
  return (
    <main className="tool-page">
      <Link className="back-link" href="/">
        返回个人网站
      </Link>
      <WisdomAdvisorStudio />
    </main>
  );
}
