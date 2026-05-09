import path from "node:path";
import { NextResponse } from "next/server";
import { getInterviewPipelineBaseUrl } from "../../../../lib/service-config";
import { appendKnowledgeSource } from "../../../../lib/wisdom-advisor";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      audioUrl?: string;
      title?: string;
      summary?: string;
      tags?: string;
    };

    const audioUrl = (payload.audioUrl || "").trim();
    if (!audioUrl) {
      throw new Error("录音链接不能为空。");
    }

    const title = (payload.title || deriveTitleFromAudioUrl(audioUrl)).trim();
    const importForm = new FormData();
    importForm.append("audio_url", audioUrl);
    importForm.append("candidate", title);
    importForm.append("role", "沟通与处事知识库");
    importForm.append("round", "录音转写入库");
    importForm.append("date", new Date().toISOString().slice(0, 10));
    importForm.append("write_to_notion", "false");
    importForm.append("include_mock_review", "false");

    const response = await fetch(`${getInterviewPipelineBaseUrl()}/api/run`, {
      method: "POST",
      body: importForm,
    });
    const result = (await response.json()) as {
      ok?: boolean;
      error?: string;
      result?: {
        summary?: string;
        transcript_text?: string;
      };
    };

    if (!response.ok || !result.ok || !result.result?.transcript_text) {
      throw new Error(result.error || "转写服务没有返回有效文本。");
    }

    const source = await appendKnowledgeSource({
      title,
      sourceType: "录音转写",
      summary: (payload.summary || result.result.summary || `${title} 的录音转写入库`).trim(),
      tags: (payload.tags || "").split(/[，,]/),
      content: result.result.transcript_text,
    });

    return NextResponse.json({
      ok: true,
      source,
      transcriptLength: result.result.transcript_text.length,
      pipelineSummary: result.result.summary || "",
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "录音导入失败。",
      },
      { status: 400 }
    );
  }
}

function deriveTitleFromAudioUrl(audioUrl: string) {
  try {
    const parsed = new URL(audioUrl);
    const fileName = decodeURIComponent(path.basename(parsed.pathname));
    return fileName.replace(/\.[a-z0-9]+$/i, "") || "录音转写";
  } catch {
    return "录音转写";
  }
}
