from __future__ import annotations

from pathlib import Path

from .config import UPLOAD_DIR
from .models import (
    AnalysisResult,
    IssueEvidence,
    IssueItem,
    NextTask,
    RewriteSuggestion,
    ScoreSet,
    StrengthItem,
    SummaryBlock,
    VideoMetadata,
)
from .repository import get_practice, save_analysis, update_practice_status


def run_analysis(practice_id: str) -> None:
    practice = get_practice(practice_id)
    if practice is None:
        return

    try:
        update_practice_status(practice_id, "processing")
        reference_path = UPLOAD_DIR / practice.reference_filename
        attempt_path = UPLOAD_DIR / practice.attempt_filename

        reference_video = build_video_metadata(reference_path)
        attempt_video = build_video_metadata(attempt_path)

        analysis = build_placeholder_analysis(
            title=practice.title,
            focus_note=practice.focus_note,
            reference_video=reference_video,
            attempt_video=attempt_video,
        )
        save_analysis(practice_id, analysis)
    except Exception as exc:  # pragma: no cover - defensive fallback
        update_practice_status(practice_id, "failed", str(exc))


def build_video_metadata(path: Path) -> VideoMetadata:
    size_bytes = path.stat().st_size
    return VideoMetadata(
        filename=path.name,
        size_bytes=size_bytes,
        size_mb=round(size_bytes / (1024 * 1024), 2),
        suffix=path.suffix.lower(),
    )


def build_placeholder_analysis(
    title: str,
    focus_note: str | None,
    reference_video: VideoMetadata,
    attempt_video: VideoMetadata,
) -> AnalysisResult:
    size_gap = abs(reference_video.size_mb - attempt_video.size_mb)
    rough_alignment = max(55, min(82, int(78 - size_gap * 4)))
    rhythm_score = max(50, min(78, int(72 - size_gap * 3)))
    concise_score = max(48, min(76, int(70 - size_gap * 3)))

    focus_line = focus_note or "目前还没有填写本轮训练重点。"

    return AnalysisResult(
        summary=SummaryBlock(
            overall_comment=(
                f"“{title}” 的 MVP 反馈已经生成。目前这份结果主要基于视频元数据和固定教练模板，"
                "结构已经可用，但还没有接入真实的转写、语音和视觉模型。"
            ),
            total_score=int((rough_alignment + rhythm_score + concise_score + 68 + 66 + 64) / 6),
            confidence=0.34,
            provisional=True,
        ),
        scores=ScoreSet(
            content_fidelity=rough_alignment,
            structure_clarity=68,
            language_naturalness=66,
            conciseness=concise_score,
            delivery_rhythm=rhythm_score,
            visual_presence=64,
        ),
        strengths=[
            StrengthItem(
                title="训练闭环已经打通",
                evidence="当前可以完整保存目标视频、模仿视频和结构化分析结果，为后续接入真实模型做好了承接。",
            ),
            StrengthItem(
                title="反馈格式适合反复练习",
                evidence="总评、问题、改法和下一轮任务都已经固定下来，后续替换分析引擎后可以直接复用。",
            ),
        ],
        top_issues=[
            IssueItem(
                title="真实内容比对尚未接入",
                severity="high",
                dimension="content_fidelity",
                evidence=IssueEvidence(
                    reference=f"目标视频文件大小 {reference_video.size_mb} MB",
                    attempt=f"模仿视频文件大小 {attempt_video.size_mb} MB",
                    observation="当前还没有 ASR 转写，因此不能判断是否漏信息、改意思或结构变化。",
                ),
                why_it_matters="没有逐句文本对齐时，系统还不能给出真正有证据的内容模仿反馈。",
                fix="下一步接入语音转写和句子对齐，把目标表达与模仿表达映射成可比较的文本段落。",
            ),
            IssueItem(
                title="语音节奏指标仍是占位",
                severity="medium",
                dimension="delivery_rhythm",
                evidence=IssueEvidence(
                    metric=f"placeholder.size_gap_mb={round(size_gap, 2)}",
                    observation="暂时没有语速、停顿、重音等客观语音指标。",
                ),
                why_it_matters="表达教练最有价值的部分之一就是指出哪里说得拖、平或太赶，这需要真实音频特征支撑。",
                fix="接入音频抽取和基础声学指标，先拿到语速、停顿数、平均停顿时长这些稳定信号。",
            ),
            IssueItem(
                title="镜头表现分析还未启用",
                severity="medium",
                dimension="visual_presence",
                evidence=IssueEvidence(
                    observation="目前只保存了视频文件本身，还没有做关键帧抽取和画面观察。",
                ),
                why_it_matters="你的场景是视频模仿，眼神、表情和动作稳定性会显著影响表达效果。",
                fix="在后续版本中增加关键帧抽取，把轻量视觉观察结果交给多模态模型统一生成教练反馈。",
            ),
        ],
        next_task=NextTask(
            focus="接入真实分析链路",
            instruction=(
                "下一步优先补齐转写和句子对齐，让系统先具备可靠的文本诊断能力；"
                f"当前记录的训练重点是：{focus_line}"
            ),
            drill="完成 ASR 接入后，先用 3 到 5 条短视频做试跑，校验输出的差异证据是否足够具体。",
        ),
        rewrite_suggestions=[
            RewriteSuggestion(
                original_attempt="这是一条占位建议，当前还没有拿到你的真实模仿文本。",
                suggested_version="等接入转写后，这里会给出可直接复练的更短、更清晰版本。",
            )
        ],
        coach_message="第一版产品骨架已经支持上传、记录和结构化反馈；接下来最值得做的就是把真实多模态分析接上来。",
        reference_video=reference_video,
        attempt_video=attempt_video,
        pipeline_notes=[
            "当前分析是占位流水线，适合联调前后端和验证产品结构。",
            "后续建议依次接入：音频抽取 -> ASR -> 文本对齐 -> 语音指标 -> 关键帧观察 -> 多模态教练模型。",
            "如果你已经有偏好的模型供应商，下一步可以直接替换 app/analyzer.py 中的占位逻辑。",
        ],
    )
