import { NextResponse } from "next/server";
import { getVerbalCoachBaseUrl } from "../../../../lib/service-config";

export async function GET() {
  try {
    const response = await fetch(`${getVerbalCoachBaseUrl()}/api/practices`, {
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Unable to load practices.",
      },
      { status: 503 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const incomingForm = await request.formData();
    const outgoingForm = new FormData();

    for (const [key, value] of incomingForm.entries()) {
      outgoingForm.append(key, value);
    }

    const response = await fetch(`${getVerbalCoachBaseUrl()}/api/practices`, {
      method: "POST",
      body: outgoingForm,
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Unable to create practice.",
      },
      { status: 503 }
    );
  }
}

