const trimSlash = (value: string) => value.replace(/\/+$/, "");

export function getInterviewPipelineBaseUrl() {
  return trimSlash(process.env.INTERVIEW_PIPELINE_BASE_URL || "http://127.0.0.1:8787");
}

export function getVerbalCoachBaseUrl() {
  return trimSlash(process.env.VERBAL_COACH_BASE_URL || "http://127.0.0.1:8000");
}

