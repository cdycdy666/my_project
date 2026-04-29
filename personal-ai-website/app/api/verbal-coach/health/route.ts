import { NextResponse } from "next/server";
import { getVerbalCoachBaseUrl } from "../../../../lib/service-config";

export async function GET() {
  try {
    const response = await fetch(`${getVerbalCoachBaseUrl()}/api/health`, {
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        status: "error",
        error: error instanceof Error ? error.message : "Verbal coach service unavailable.",
      },
      { status: 503 }
    );
  }
}

