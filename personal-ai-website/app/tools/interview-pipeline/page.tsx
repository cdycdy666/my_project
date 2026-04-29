import Link from "next/link";
import { InterviewPipelineStudio } from "../../../components/InterviewPipelineStudio";

export default function InterviewPipelinePage() {
  return (
    <main className="tool-page">
      <Link className="back-link" href="/">
        返回个人网站
      </Link>
      <InterviewPipelineStudio />
    </main>
  );
}

