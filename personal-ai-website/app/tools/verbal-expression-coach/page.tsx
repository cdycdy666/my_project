import Link from "next/link";
import { VerbalExpressionCoachStudio } from "../../../components/VerbalExpressionCoachStudio";

export default function VerbalExpressionCoachPage() {
  return (
    <main className="tool-page">
      <Link className="back-link" href="/">
        返回个人网站
      </Link>
      <VerbalExpressionCoachStudio />
    </main>
  );
}

