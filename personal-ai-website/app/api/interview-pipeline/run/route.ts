import { NextResponse } from "next/server";
import { getInterviewPipelineBaseUrl } from "../../../../lib/service-config";

export async function POST(request: Request) {
  try {
    const incomingForm = await request.formData();
    const outgoingForm = new FormData();

    for (const [key, value] of incomingForm.entries()) {
      outgoingForm.append(key, value);
    }

    const response = await fetch(`${getInterviewPipelineBaseUrl()}/api/run`, {
      method: "POST",
      body: outgoingForm,
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Interview pipeline request failed.",
      },
      { status: 503 }
    );
  }
}

