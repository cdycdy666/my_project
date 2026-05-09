import { NextResponse } from "next/server";
import { buildAdvice } from "../../../../lib/wisdom-advisor";

type RateLimitEntry = {
  count: number;
  resetAt: number;
};

const rateLimitStore = globalThis as typeof globalThis & {
  __wisdomAdvisorRateLimit?: Map<string, RateLimitEntry>;
};

const RATE_LIMIT_MAP = rateLimitStore.__wisdomAdvisorRateLimit ?? new Map<string, RateLimitEntry>();
rateLimitStore.__wisdomAdvisorRateLimit = RATE_LIMIT_MAP;

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      question?: string;
      context?: string;
      accessCode?: string;
    };

    const rateLimit = consumeRateLimit(request);
    if (!rateLimit.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: `这段时间问得有点密了，请在 ${rateLimit.retryAfterSeconds} 秒后再试。`,
          retryAfterSeconds: rateLimit.retryAfterSeconds,
        },
        {
          status: 429,
          headers: {
            "Retry-After": String(rateLimit.retryAfterSeconds),
          },
        }
      );
    }

    const expectedAccessCode = process.env.WISDOM_ADVISOR_ACCESS_CODE?.trim();
    if (expectedAccessCode) {
      const receivedAccessCode = payload.accessCode?.trim();
      if (!receivedAccessCode || receivedAccessCode !== expectedAccessCode) {
        return NextResponse.json(
          {
            ok: false,
            error: "访问码不正确，请输入有效访问码后再试。",
            requiresAccessCode: true,
          },
          { status: 401 }
        );
      }
    }

    const advice = await buildAdvice(payload.question || "", payload.context || "");
    return NextResponse.json({
      ok: true,
      advice,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "生成建议失败。",
      },
      { status: 400 }
    );
  }
}

function consumeRateLimit(request: Request) {
  const identifier = getClientIdentifier(request);
  const now = Date.now();
  const limit = getPositiveInteger(process.env.WISDOM_ADVISOR_RATE_LIMIT_MAX, 10);
  const windowMs = getPositiveInteger(process.env.WISDOM_ADVISOR_RATE_LIMIT_WINDOW_MS, 10 * 60 * 1000);
  const current = RATE_LIMIT_MAP.get(identifier);

  if (!current || current.resetAt <= now) {
    RATE_LIMIT_MAP.set(identifier, {
      count: 1,
      resetAt: now + windowMs,
    });
    pruneRateLimitStore(now);
    return { ok: true as const };
  }

  if (current.count >= limit) {
    return {
      ok: false as const,
      retryAfterSeconds: Math.max(1, Math.ceil((current.resetAt - now) / 1000)),
    };
  }

  current.count += 1;
  RATE_LIMIT_MAP.set(identifier, current);
  return { ok: true as const };
}

function getClientIdentifier(request: Request) {
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) {
    return forwardedFor.split(",")[0]?.trim() || "anonymous";
  }

  const realIp = request.headers.get("x-real-ip");
  if (realIp) {
    return realIp.trim();
  }

  const userAgent = request.headers.get("user-agent") || "unknown";
  return `anonymous:${userAgent.slice(0, 80)}`;
}

function getPositiveInteger(value: string | undefined, fallback: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return Math.floor(parsed);
}

function pruneRateLimitStore(now: number) {
  if (RATE_LIMIT_MAP.size < 200) {
    return;
  }

  for (const [key, entry] of RATE_LIMIT_MAP.entries()) {
    if (entry.resetAt <= now) {
      RATE_LIMIT_MAP.delete(key);
    }
  }
}
