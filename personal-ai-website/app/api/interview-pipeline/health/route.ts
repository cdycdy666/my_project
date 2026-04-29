import { NextResponse } from "next/server";
import { getInterviewPipelineBaseUrl } from "../../../../lib/service-config";

export async function GET() {
  try {
    const response = await fetch(`${getInterviewPipelineBaseUrl()}/api/health`, {
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Interview pipeline service unavailable.",
      },
      { status: 503 }
    );
  }
}

