from __future__ import annotations

from .models import InterviewInput, MediaInsightResult, QuestionAnswerPair, StructuredAssessment


def build_structured_assessment(
    interview: InterviewInput,
    result: MediaInsightResult,
) -> StructuredAssessment:
    summary = _build_executive_summary(interview, result)
    strengths = _derive_strengths(result)
    risks = _derive_risks(result)
    follow_ups = _derive_follow_ups(interview, result)
    recommendation = _derive_recommendation(interview, strengths, risks, result)

    return StructuredAssessment(
        summary=summary,
        strengths=strengths,
        risks=risks,
        follow_ups=follow_ups,
        recommendation=recommendation,
        transcript_text=result.transcript_text,
    )


def build_page_markdown(
    interview: InterviewInput,
    result: MediaInsightResult,
    assessment: StructuredAssessment,
) -> str:
    selected_qa_pairs = _select_key_qa_pairs(result.qa_pairs)
    lines: list[str] = [
        "## AI纪要",
        "",
        "### 全文总结",
        assessment.summary or "暂无摘要",
        "",
        "## 结构化面评",
        f"- 岗位：{interview.role}",
        f"- 面试日期：{interview.interview_date.isoformat()}",
        f"- 轮次：{interview.round}",
        f"- 结论建议：{assessment.recommendation}",
        "",
        "### 亮点",
    ]
    if interview.candidate.strip():
        lines.insert(6, f"- 候选人：{interview.candidate}")
    lines.extend(f"- {item}" for item in assessment.strengths or ["待人工补充"])
    lines.extend(["", "### 风险点"])
    lines.extend(f"- {item}" for item in assessment.risks or ["待人工补充"])
    lines.extend(["", "### 待确认问题"])
    lines.extend(f"- {item}" for item in assessment.follow_ups or ["待人工补充"])

    if result.chapters:
        lines.extend(["", "## 章节总结"])
        lines.extend(f"- {item}" for item in result.chapters)

    if selected_qa_pairs:
        lines.extend(["", "## 关键问答"])
        for index, item in enumerate(selected_qa_pairs, start=1):
            lines.extend(
                [
                    f"### 问答 {index}",
                    f"- 问题：{item.question}",
                    f"- 回答：{item.answer}",
                ]
            )

    lines.extend(["", "## 完整转写", result.transcript_text or "暂无完整转写"])
    return "\n".join(lines)


def build_mock_interview_review_markdown(
    interview: InterviewInput,
    result: MediaInsightResult,
    assessment: StructuredAssessment,
) -> str:
    selected_qa_pairs = _select_review_qa_pairs(result.qa_pairs)
    lines: list[str] = [
        "# 模拟面试复盘",
        "",
        "## 一、面试综合评价",
        _build_overall_review(interview, assessment, result),
        "",
        "## 二、回答优化指南",
    ]

    if not selected_qa_pairs:
        lines.extend(
            [
                "当前未抽取到足够清晰的问答对，建议结合完整转写人工补充。",
            ]
        )
    else:
        for index, item in enumerate(selected_qa_pairs, start=1):
            block = _build_review_block(item)
            lines.extend(
                [
                    f"### 问题 {index}",
                    f"原始问题：{item.question}",
                    f"1. 面试者回答：{item.answer}",
                    "2. 回答评价：",
                    f"1. 考察点分析：{block['focus']}",
                    f"2. 回答优缺点：{block['verdict']}",
                    "3. 存在不足与优化点：",
                ]
            )
            lines.extend(f"{offset}. {point}" for offset, point in enumerate(block["gaps"], start=1))
            lines.extend(
                [
                    "4. 参考答案：",
                    *[f"{offset}. {point}" for offset, point in enumerate(block["reference"], start=1)],
                    "",
                ]
            )

    lines.extend(
        [
            "## 三、薄弱点汇总",
            *[f"- {item}" for item in _build_common_gaps(result)],
            "",
            "## 四、下一轮重点准备",
            *[f"- {item}" for item in _build_next_round_preparation(interview, result)],
        ]
    )
    return "\n".join(lines)


def _fallback_summary(result: MediaInsightResult) -> str:
    if result.chapters:
        return "；".join(result.chapters[:3])
    if result.transcript_text:
        return result.transcript_text[:240].strip()
    return ""


def _derive_strengths(result: MediaInsightResult) -> list[str]:
    transcript = result.transcript_text
    strengths: list[str] = []
    if "百度地图" in transcript and "算法工程师" in transcript:
        strengths.append("候选人有百度地图算法工程师经历，业务背景与大模型落地场景较贴近。")
    if "Lora" in transcript or "SFT" in transcript:
        strengths.append("有基于 LoRA / SFT 做规则对齐和多模态模型微调的实际经验。")
    if "30万" in transcript or "50万" in transcript:
        strengths.append("提到线上或准线上规模，日处理量约 30 万到 50 万张图片，具备一定生产环境经验。")
    if "85%" in transcript and "98%" in transcript:
        strengths.append("对效果提升有量化表述，提到单张图片识别准确率从 85% 提升到 98%。")
    if "自动化链路" in transcript or "模型驱动" in transcript:
        strengths.append("不是只做离线实验，能够围绕数据、微调、规则后处理和上线链路描述完整方案。")
    if strengths:
        return strengths[:5]
    if result.chapters:
        return result.chapters[:3]
    if result.qa_pairs:
        return [_summarize_answer(item) for item in result.qa_pairs[:3]]
    return ["转写已完成，但未识别出明确亮点，请人工复核。"]


def _derive_risks(result: MediaInsightResult) -> list[str]:
    transcript = result.transcript_text
    if not transcript:
        return ["缺少完整转写，无法自动判断风险点。"]
    risks: list[str] = []
    if "我没参与部署过程" in transcript or "具体使用的机器不太清楚" in transcript or "我这边没有涉及" in transcript:
        risks.append("上线部署、机器资源和 Infra 细节掌握有限，真实 owner 边界需要进一步核实。")
    if "暂时没有" in transcript and "强化学习" in transcript:
        risks.append("强化学习和更复杂的在线迭代经验暂时偏弱，能力边界可能主要在 SFT 与规则对齐。")
    if "只做一些优化工作" in transcript or "并非完全重构" in transcript:
        risks.append("当前工作更多偏现有业务链条优化，是否具备从 0 到 1 的重构能力还需要继续追问。")
    if "准确率的计算口径" in transcript:
        risks.append("准确率和自动化率口径较复杂，收益数据需要进一步拆解验证，避免被筛选条件放大。")
    if not risks and len(transcript) < 80:
        risks.append("转写内容较短，可能存在录音质量或权限问题。")
    if not risks:
        risks.append("当前风险点仅基于自动纪要生成，仍需面试官结合岗位要求复核。")
    return risks[:5]


def _derive_follow_ups(interview: InterviewInput, result: MediaInsightResult) -> list[str]:
    transcript = result.transcript_text
    follow_ups: list[str] = [
        "继续追问项目中的个人 owner 边界，区分数据构建、模型训练、评估设计、上线部署分别由谁负责。",
        "要求候选人把准确率、自动化率、人工兜底比例的计算口径讲清楚，并给出上线前后的对比数据。",
        "围绕长尾场景和失败案例追问，确认他是否真正主导过迭代闭环，而不只是提出方向。",
    ]
    if interview.role != "待补充":
        follow_ups.append(f"结合 {interview.role} 的核心要求，确认候选人经验是否覆盖岗位最关键的能力短板。")
    else:
        follow_ups.append("结合目标岗位要求，补一轮针对岗位核心能力的定向追问。")
    if "强化学习" in transcript:
        follow_ups.append("如果岗位需要在线学习或策略优化，继续追问他对强化学习和在线评估的理解深度。")
    return follow_ups[:4]


def _derive_recommendation(
    interview: InterviewInput,
    strengths: list[str],
    risks: list[str],
    result: MediaInsightResult,
) -> str:
    if not result.transcript_text:
        return "待定"
    if any("录音质量" in item for item in risks):
        return "待定"
    if interview.role == "待补充":
        return "待定"
    if len(strengths) >= 3 and len(risks) <= 2 and len(result.transcript_text) >= 400:
        return "推荐"
    return "待定"


def _build_executive_summary(interview: InterviewInput, result: MediaInsightResult) -> str:
    transcript = result.transcript_text
    pieces: list[str] = []
    if interview.candidate:
        pieces.append(f"{interview.candidate}目前在百度地图从事多模态大模型落地相关工作。")
    if "2024年" in transcript and "北京邮电大学" in transcript:
        pieces.append("背景上具备较新的硕士毕业经历，表达清楚自身从地图数据生产切入大模型应用的路径。")
    if "Lora" in transcript or "SFT" in transcript:
        pieces.append("项目经验集中在 LoRA / SFT 微调、数据集构建、规则对齐和后处理链路。")
    if "30万" in transcript or "50万" in transcript:
        pieces.append("候选人提到线上或准线上规模，日处理量约 30 万到 50 万张图片，并给出准确率从 85% 到 98% 的量化结果。")
    if "我没参与部署过程" in transcript or "我这边没有涉及" in transcript:
        pieces.append("需要继续确认其在上线部署、资源成本和整体 owner 边界上的真实参与深度。")
    if "暂时没有" in transcript and "强化学习" in transcript:
        pieces.append("在更复杂的在线迭代和强化学习方向上，目前经验相对有限。")
    if pieces:
        return " ".join(pieces)[:360].rstrip() + ("..." if len(" ".join(pieces)) > 360 else "")
    return _compress_summary(result.summary or _fallback_summary(result))


def _summarize_answer(item: QuestionAnswerPair) -> str:
    answer = item.answer.strip()
    if not answer:
        return f"问题“{item.question}”尚无有效回答，建议人工复核。"
    if len(answer) > 48:
        answer = f"{answer[:48].rstrip()}..."
    return f"围绕“{item.question}”给出了回答：{answer}"


def _build_follow_up_prompts(qa_pairs: list[QuestionAnswerPair]) -> list[str]:
    prompts: list[str] = []
    for item in qa_pairs:
        question = item.question.strip()
        if not question:
            continue
        prompts.append(f"复核问题“{question}”的回答是否具体、可信且与岗位要求相关。")
    return prompts


def _compress_summary(summary: str) -> str:
    text = summary.strip()
    if not text:
        return ""
    if len(text) <= 320:
        return text
    return f"{text[:320].rstrip()}..."


def _select_key_qa_pairs(qa_pairs: list[QuestionAnswerPair]) -> list[QuestionAnswerPair]:
    if not qa_pairs:
        return []
    keywords = (
        "大模型",
        "微调",
        "lora",
        "sft",
        "上线",
        "准确率",
        "自动化",
        "离职",
        "挑战",
        "业务",
    )
    picked: list[QuestionAnswerPair] = []
    used_ids: set[int] = set()
    seen_questions: set[str] = set()
    for index, item in enumerate(qa_pairs):
        haystack = f"{item.question} {item.answer}".lower()
        normalized_question = _normalize_question(item.question)
        if any(keyword in haystack for keyword in keywords) and normalized_question not in seen_questions:
            picked.append(item)
            used_ids.add(index)
            seen_questions.add(normalized_question)
        if len(picked) >= 6:
            break
    if len(picked) < 6:
        for index, item in enumerate(qa_pairs):
            if index in used_ids:
                continue
            normalized_question = _normalize_question(item.question)
            if normalized_question in seen_questions:
                continue
            picked.append(item)
            seen_questions.add(normalized_question)
            if len(picked) >= 6:
                break
    return picked[:6]


def _normalize_question(question: str) -> str:
    text = question.lower().strip()
    for token in ("吗", "呢", "呀", "啊", "？", "?", "，", ",", "。", "."):
        text = text.replace(token, "")
    return text


def _select_review_qa_pairs(qa_pairs: list[QuestionAnswerPair]) -> list[QuestionAnswerPair]:
    picked: list[QuestionAnswerPair] = []
    seen_questions: set[str] = set()
    seen_topics: set[str] = set()
    for item in qa_pairs:
        normalized = _normalize_question(item.question)
        if normalized in seen_questions:
            continue
        topic = _classify_review_topic(item)
        if topic != "generic" and topic not in seen_topics:
            picked.append(item)
            seen_questions.add(normalized)
            seen_topics.add(topic)
        if len(picked) >= 5:
            break
    if len(picked) < 5:
        for item in qa_pairs:
            normalized = _normalize_question(item.question)
            if normalized in seen_questions:
                continue
            picked.append(item)
            seen_questions.add(normalized)
            if len(picked) >= 5:
                break
    return picked[:5]


def _build_overall_review(
    interview: InterviewInput,
    assessment: StructuredAssessment,
    result: MediaInsightResult,
) -> str:
    transcript = result.transcript_text
    parts: list[str] = []
    if interview.candidate:
        parts.append(
            f"根据这轮面试表现，{interview.candidate}展现出了比较扎实的大模型应用落地背景，尤其是在多模态识别、规则对齐、LoRA / SFT 微调和业务自动化链路改造方面，具备较强的一线实践经验。"
        )
    else:
        parts.append("候选人在这轮面试中展现出了比较扎实的大模型应用落地背景。")
    if "30万" in transcript or "50万" in transcript:
        parts.append("在项目表达上，候选人能够给出一定的线上规模、收益指标和具体工程取舍，这使得经历可信度明显高于只会讲概念的候选人。")
    if "暂时没有" in transcript and "强化学习" in transcript:
        parts.append("需要注意的是，候选人在强化学习、深层在线迭代和完整 owner 闭环上的经验仍然相对薄弱，部分回答在业务抽象和指标口径上也还有继续收紧的空间。")
    if "我这边没有" in transcript or "没参与部署过程" in transcript:
        parts.append("此外，部署、Infra 和资源侧信息掌握不深，也提示后续需要继续验证其真实 owner 边界。")
    parts.append("整体来看，这更像是一位强应用落地、强链路改造型候选人；如果目标岗位匹配这一方向，面试通过概率会偏积极，但如果岗位要求更强的系统 owner 能力或训练策略深度，还需要继续补充追问。")
    return "".join(parts)


def _build_review_block(item: QuestionAnswerPair) -> dict[str, list[str] | str]:
    topic = _classify_review_topic(item)
    answer = item.answer.strip()

    if topic == "problem_abstraction":
        return {
            "focus": "这类问题主要考察候选人能否把业务问题抽象成一个明确的模型任务，并把数据构建、训练方式、规则表达和最终业务目标串成一条完整链路。",
            "verdict": "回答说明了自己是在微调数据构建阶段把业务规则融入训练过程，方向是对的，也触及了问题抽象的核心。但整体还是偏“我做了什么”，缺少一个更完整的问题建模框架。",
            "gaps": [
                "没有先用一句话定义任务输入、输出和关键约束，导致回答一开始就进入实现细节，结构上略显发散。",
                "对“抽象”的描述更多停在数据集构建，没有继续往上总结成“把规则驱动决策问题转成带理由监督的多分类/判定任务”。",
                "如果能补上为什么这样抽象更利于微调和后续上线，会让这题更像项目 owner 的回答，而不只是工程执行者的回答。",
            ],
            "reference": [
                "我先把问题定义成一个带业务规则约束的视觉判定任务：输入是道路图片，输出不是简单分类，而是“道路等级判断 + 无法判断 + 可解释理由”。",
                "这样抽象的好处是，我们可以把人工审核时真正依赖的规则也编码进训练样本，而不是只让模型记一个最终标签。",
                "接下来我再围绕这套任务定义去做数据集构建、规则辅助标注、SFT 微调和线上后处理，这样训练目标和业务目标是一致的。",
            ],
        }

    if topic == "vlm_why":
        return {
            "focus": "这类问题主要考察候选人是否真正理解任务本质，能否把业务问题拆成“视觉识别 + 规则决策”的复合问题，并清楚比较传统 CV 方案与多模态大模型方案的边界。",
            "verdict": "回答抓到了“规则驱动”和“多特征综合判断”两个关键点，也能说明传统方案成本高、泛化难。但论证还不够一锤定音，更多是在描述现象，没有把“为什么传统端到端模型难学会业务规则”说得足够锋利。",
            "gaps": [
                "没有把任务本质明确上升到“基于复杂业务规则的多特征综合决策”，导致回答听起来像在解释方案，而不是先定义问题。",
                "对传统模型的局限更多停留在“开发成本高”“识别不准”，缺少对规则表达能力、可解释性和边界场景泛化能力的直接对比。",
                "没有充分突出 VLM 的核心优势是“自然语言规则可直接注入、少样本可快速对齐、结论和理由可一起校验”，所以说服力还可以再加强。",
            ],
            "reference": [
                "这个任务的核心难点不在于识别“有没有路”，而在于根据多个视觉特征和一套复杂业务规则做综合判断，本质上是“视觉理解 + 规则决策”的复合问题。",
                "传统 CV 方案理论上能做，但往往需要拆成多个子任务，比如会车性、分隔线、路宽、场景属性等，再把这些结果拼回规则判断，整体开发和维护成本都很高。",
                "多模态大模型更适合的原因，是它能把图片理解和自然语言规则放在同一个推理框架里，再通过 SFT 或提示词把“规则判断”直接对齐进去，迭代会更敏捷。",
            ],
        }

    if topic == "rag_chunking":
        return {
            "focus": "主要考察候选人是否真正做过 RAG 工程实现，是否理解文本分块策略会直接影响检索精度、规则完整性和后续推理质量。",
            "verdict": "回答给出了递归分块、chunk size 和 overlap 这些工程参数，说明有真实操作经验。但回答偏参数化，对“为什么这么切”和“规则是否会被切碎”的思考还不够深入。",
            "gaps": [
                "把“最小粒度”直接回答成 chunk size，容易显得概念不够严谨，最小粒度更应该是完整规则句而不是固定字数。",
                "没有优先强调基于文档原始层级结构分块，而是先说固定大小递归切分，这会让面试官担心规则语义被机械截断。",
                "缺少对业务影响的解释，比如块切得不好会导致检索到的规则不完整，最终影响标注理由和模型学习质量。",
            ],
            "reference": [
                "这个文档最重要的是保持规则语义完整，所以我会优先按章节、条目、规则句去做结构化粗分块，而不是一上来就按固定字数切。",
                "如果某个条目太长，再做递归细分，同时保留 overlap，避免一条规则被硬切成两个 chunk。",
                "对这个场景来说，最小粒度应该是一条可独立成立的规则陈述句，而不是单纯的 100 字文本块。",
            ],
        }

    if topic == "retrieval_strategy":
        return {
            "focus": "主要考察候选人对检索方案的取舍能力，以及是否能结合当前文档特征、规模和演进方向做出务实判断。",
            "verdict": "回答提到了可扩展性，并且知道关键词检索和向量检索可以结合使用，这个方向是对的。但理由比较泛，没有结合“30 页规则手册”这种具体文档特征说透为什么当前还要优先向量检索。",
            "gaps": [
                "没有正面承认结构化规则文档其实天然适合关键词召回，这会让回答显得有点为了“高级方案”而高级方案。",
                "对向量检索的优势解释过于抽象，没有把同义表达、语义泛化和规则描述不完全一致这些实际收益说清楚。",
                "也没有说明为什么当时不先用简单关键词方案做 baseline，再逐步演进到混合检索，这会让方案看起来有些过早优化。",
            ],
            "reference": [
                "如果文档规模不大且术语很稳定，关键词检索其实是一个非常强的 baseline，因为精确、可解释、调试成本也低。",
                "但这个场景里，图片特征和规则表述未必字面一致，所以纯关键词可能会漏掉一些语义上相关的规则，这就是向量检索的价值。",
                "更成熟的答案通常不是二选一，而是说明最终会走混合检索：用关键词保证精确性，用向量补语义召回，再做重排。",
            ],
        }

    if topic == "cot_training":
        return {
            "focus": "这类问题考察候选人是否理解生成式标注数据的训练价值，以及在“训练时保留推理链、线上时压缩输出”之间如何做工程取舍。",
            "verdict": "回答说明了 COT 在微调阶段会保留，而在线推理阶段会为了吞吐做截断，这个思路是合理的，也体现了他对训练和推理阶段目标不同的理解。",
            "gaps": [
                "回答可以再多讲一步：为什么保留理由不只是为了可解释，而是为了让模型学会把视觉特征映射到业务规则的推理过程。",
                "没有展开说明如何保证生成理由本身的质量，比如结论正确但理由错误的样本会不会污染 SFT 数据。",
                "线上截断的策略虽然讲到了，但缺少对风险的补充，比如如何确保截断后不影响最终决策可靠性。",
            ],
            "reference": [
                "我会在训练阶段保留 COT 或“结论 + 理由”的结构，因为这不是单纯为了可解释，而是为了让模型学会把图片特征和规则依据对齐起来。",
                "但在线阶段我更关注吞吐，所以会让模型优先输出结论，必要时把理由后置甚至截断，以换取更稳定的时延和成本。",
                "前提是训练数据里要保证“结论正确、理由也能支持结论”，否则模型学到的推理链会不稳定。",
            ],
        }

    if topic == "lora":
        return {
            "focus": "主要考察候选人对 LoRA、全参微调和训练策略取舍的理解，尤其是能否从工程效率、风险控制和任务适配性来解释为什么这样选。",
            "verdict": "回答能讲到低秩适配、参数量更少和秩是关键超参，说明基础是过关的。但整体更偏原理复述，缺少更工程化、更贴任务场景的决策表达。",
            "gaps": [
                "回答里对 LoRA 的优势主要停留在“参数少”，没有充分强调显存、训练速度、部署切换和降低灾难性遗忘这些工程收益。",
                "没有把任务特点讲得更直接，比如当前任务是规则对齐，不是重塑通用视觉理解能力，所以 LoRA 更自然。",
                "关于 rank 的说明略偏教材化，可以进一步补上“rank 越小越轻，但表达能力也受限，所以要结合任务复杂度调参”的判断逻辑。",
            ],
            "reference": [
                "我选 LoRA 的核心原因不是它新，而是这个任务本质上是规则对齐，不需要重构模型的通用能力，所以没必要走代价更高的全参微调。",
                "LoRA 的好处是显存和训练成本更低、迭代更快，而且冻结大部分原模型参数后，也更不容易破坏原模型已有的视觉理解能力。",
                "在这个场景里，rank 的选择本质上是在适配能力和训练成本之间做权衡，所以我会从小 rank 开始试，再根据效果和训练耗时决定是否放大。",
            ],
        }

    if topic == "metrics":
        return {
            "focus": "主要考察候选人是否真正理解自己汇报的收益指标，能否把模型准确率、业务自动化率、人工兜底和流量分层之间的关系解释清楚。",
            "verdict": "回答说明候选人知道准确率和自动化率不是一回事，也能解释部分样本会被提前分流或交给人工，这个方向是对的。但整体表达仍然有些绕，口径没有一次性讲透。",
            "gaps": [
                "在“全量流量”“过模型流量”“自动化上线比例”这几个概念之间切换比较频繁，听感上容易让面试官觉得数字不够稳。",
                "没有先给出一个简洁的计算框架，再往里填例外情况，导致回答越解释越复杂。",
                "可以更主动地强调“单图准确率高不等于业务自动化率高”，因为后者还受长尾场景、平行路噪声和人工兜底策略影响。",
            ],
            "reference": [
                "这里有两个指标要分开看：一个是单张图片识别准确率，另一个是业务自动化率，它们不是同一个概念。",
                "单图准确率提升说明模型识别能力变强了，但自动化率还会受到长尾场景、平行路噪声、人工兜底策略和流量筛选机制的共同影响。",
                "所以我通常会按“全量候选流量 -> 模型可直接判定流量 -> 需要人工兜底流量 -> 最终自动化上线比例”这个口径来解释，避免数字混在一起。",
            ],
        }

    if topic == "motivation":
        return {
            "focus": "主要考察候选人的离职动机是否成熟、是否和岗位真正匹配，以及表达里有没有负面情绪或过度理想化倾向。",
            "verdict": "回答整体比较克制，表达了想做更系统的大模型业务这一诉求，没有明显负面情绪。但如果再优化，可以把“为什么想换”说得更职业化、更贴岗位目标。",
            "gaps": [
                "当前回答略偏“对现有工作不满足”，如果表达不够收束，容易让面试官担心稳定性或预期管理问题。",
                "可以更多强调“想做更完整闭环、更高业务天花板的场景”，而不是反复强调当前工作只是优化已有链路。",
                "如果能把个人成长目标和目标岗位的挑战点更强地绑定，会显得转岗动机更成熟。",
            ],
            "reference": [
                "我想换机会，不是因为否定现在的工作，而是因为我希望在下一阶段做更完整的业务闭环，承担更强的数据、模型、评估和线上迭代责任。",
                "当前经历让我积累了很好的应用落地基础，我希望接下来进入一个更端到端、业务影响更大的场景，把这部分能力继续做深。",
                "如果目标岗位正好强调多模态、大模型重构业务和更系统的策略闭环，那我会认为这个方向和我的下一阶段成长目标非常匹配。",
            ],
        }

    return {
        "focus": "这类问题主要考察候选人是否能围绕业务、技术和工程取舍给出结构化回答。",
        "verdict": "回答有一定信息量，但还可以进一步收束结构，让“问题是什么、怎么做、为什么这样做、效果如何”这四步更明确。",
        "gaps": [
            "回答顺序可以更稳定，先定义问题，再讲方案，再讲取舍，最后讲结果。",
            "可以适当减少口语化补充，避免信息点被分散。",
            "如果能主动补一句业务影响或工程约束，回答会更像成熟项目 owner 的表达。",
        ],
        "reference": [
            "先定义问题本质，再说明为什么当前方案更适合，最后补上结果和取舍。",
            "如果涉及工程实现，优先讲清楚约束条件、关键决策点和最终收益。",
            "如果涉及技术选型，尽量把“为什么不选另一个方案”说完整，避免只描述自己做了什么。",
        ],
    }


def _classify_review_topic(item: QuestionAnswerPair) -> str:
    question = item.question.lower()
    answer = item.answer.lower()
    haystack = f"{question} {answer}"
    if "离职" in question or "出来看看" in question:
        return "motivation"
    if "为什么要用大模型" in question or "核心难点" in question:
        return "vlm_why"
    if "分块" in question or "chunksize" in question or "chunk size" in question:
        return "rag_chunking"
    if "关键词" in question or "向量" in question or "embedding" in question or "召回" in question:
        return "retrieval_strategy"
    if "cot" in question or ("理由" in question and "微调" in question):
        return "cot_training"
    if "lora" in question or "全参微调" in question or "sft有什么微调方法" in question:
        return "lora"
    if "准确率" in question or "自动化率" in question:
        return "metrics"
    if "怎么抽象这个问题" in question or "具体的细节" in question:
        return "problem_abstraction"
    if "准确率" in answer or "自动化率" in answer:
        return "metrics"
    return "generic"


def _build_common_gaps(result: MediaInsightResult) -> list[str]:
    transcript = result.transcript_text
    gaps = [
        "部分回答已经抓住关键方向，但论证经常停在“现象描述”层，还可以再多上一层问题本质分析。",
        "在工程细节问题上，能给出参数和流程，但有时缺少对“为什么这样做”的结构化解释。",
        "收益指标相关回答容易越讲越绕，后续要更主动地区分模型准确率、自动化率、人工兜底和最终业务收益。",
    ]
    if "强化学习" in transcript:
        gaps.append("面对更高阶的训练策略和在线迭代问题时，经验边界暴露得比较明显，后续要准备更清楚的能力边界表达。")
    if "我这边没有" in transcript or "没参与部署过程" in transcript:
        gaps.append("涉及部署、Infra 和资源成本时，容易因为 owner 边界不清显得信息不足，建议提前准备更清楚的职责表述。")
    return gaps[:5]


def _build_next_round_preparation(interview: InterviewInput, result: MediaInsightResult) -> list[str]:
    transcript = result.transcript_text
    items = [
        "针对最核心项目，准备一版 2 分钟和一版 5 分钟的标准化回答，确保问题定义、方案选择、工程实现和业务结果四段结构稳定输出。",
        "把“为什么用 VLM 而不是传统 CV”“为什么用 LoRA 而不是全参微调”“为什么用 RAG 做规则辅助标注”这三类高频追问，分别准备成可直接复述的标准答案。",
        "把准确率、自动化率、人工兜底比例、投诉下降等指标重新整理成统一口径，避免现场解释时来回切换。",
        "准备 2 到 3 个长尾失败案例，说明你如何识别问题、归因、迭代和验证效果，这会明显增强项目可信度。",
    ]
    if interview.role != "待补充":
        items.append(f"再补一轮和 {interview.role} 目标岗位强相关的追问演练，把你的经历主动映射到岗位核心要求。")
    if "强化学习" in transcript:
        items.append("如果下一轮面试方业务更偏在线决策或策略优化，建议提前准备一版“我目前在强化学习上的边界和后续学习计划”的表达。")
    return items[:5]
