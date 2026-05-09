import { NextResponse } from "next/server";
import { appendKnowledgeSource, getKnowledgeSourceDetail, listKnowledgeSummary } from "../../../../lib/wisdom-advisor";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const sourceId = searchParams.get("id");

    if (sourceId) {
      const source = await getKnowledgeSourceDetail(sourceId);
      return NextResponse.json({
        ok: true,
        source,
      });
    }

    const library = await listKnowledgeSummary();
    return NextResponse.json({
      ok: true,
      library,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "读取知识库失败。",
      },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      title?: string;
      sourceType?: "录音转写" | "文档摘录" | "手动笔记";
      summary?: string;
      tags?: string;
      content?: string;
    };

    const source = await appendKnowledgeSource({
      title: payload.title || "",
      sourceType: payload.sourceType || "手动笔记",
      summary: payload.summary || "",
      tags: (payload.tags || "").split(/[，,]/),
      content: payload.content || "",
    });

    return NextResponse.json({
      ok: true,
      source,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "写入知识库失败。",
      },
      { status: 400 }
    );
  }
}
