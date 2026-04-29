import { NextResponse } from "next/server";
import { getVerbalCoachBaseUrl } from "../../../../../lib/service-config";

type Context = {
  params: Promise<{
    practiceId: string;
  }>;
};

export async function GET(_: Request, context: Context) {
  const { practiceId } = await context.params;
  try {
    const response = await fetch(`${getVerbalCoachBaseUrl()}/api/practices/${practiceId}`, {
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Unable to load practice detail.",
      },
      { status: 503 }
    );
  }
}

