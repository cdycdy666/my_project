---
name: ai-context-feedback-loop
description: Design AI context and personal knowledge feedback loops. Use when Codex needs to help build or improve systems for ongoing memory, daily notes, decision logs, project journals, personal context databases, AI-assisted reflection, capture-to-summary workflows, or "let AI understand my situation over time" products.
---

# AI Context Feedback Loop

Use this skill to design low-friction systems that let users capture messy context and turn it into reusable AI memory.

## Core Pattern

Build the loop explicitly:

```text
capture -> immediate feedback -> batch organization -> durable knowledge -> future reminder/reuse
```

Keep responsibilities separate:

- Capture accepts unstructured text or voice with minimal friction.
- Immediate feedback helps the user add missing context or continue recording.
- Batch organization turns fragments into structured event chains.
- Durable knowledge stores context in a searchable, versioned place.
- Reminder/reuse reads prior notes to guide future action.

## Daily Note Structure

Prefer event grouping over a single global set of fields. A day often contains unrelated topics.

Use this structure unless the user provides a better local convention:

```markdown
# YYYY-MM-DD 日志

## 今日概览
- 

## 事件 1：事件名称
### 发生了什么
- 

### 我怎么处理的
- 

### 我做出的判断
- 

### 判断依据
- 

### 结果 / 反馈
- 

### 后续动作
- 

### 值得沉淀
- 

## 零散记录
- 

## 给 AI 的长期上下文
- 
```

## Prompt Design

Use separate prompts for separate jobs.

For immediate feedback:

- Return 1-2 short sentences.
- Identify whether the record is a problem, judgment, rationale, feedback, next step, or lesson.
- Ask at most one useful follow-up question when context is missing.
- Do not output Markdown.
- Do not merely say the record was saved.

For batch organization:

- Use only raw records.
- Group by event/topic first.
- Preserve concrete situation, actions, judgments, rationale, feedback, and next steps.
- Put unrelated fragments under separate event sections.
- Put weakly connected fragments under "零散记录".
- Put durable preferences, constraints, patterns, and facts under "给 AI 的长期上下文".

## Implementation Guidance

- Store raw records separately from organized notes.
- Keep AI-generated summaries traceable to raw input.
- Avoid making every captured message immediately rewrite the final note.
- Prefer nightly or periodic organization for stable long-form notes.
- Keep durable context concise enough to be read by future agents.

## Failure Modes

- Over-structured capture discourages input.
- Immediate feedback that is generic reduces user motivation.
- Single global daily sections mix unrelated topics.
- Missing long-term context prevents future AI reuse.
- Slow synchronous feedback can trigger duplicate platform delivery in bot systems.

## Validation

Check that:

- The user can record in one natural sentence.
- The system gives exactly one useful response per record.
- The final note separates unrelated events.
- Raw records remain available for audit.
- Future prompts can read durable context without reconstructing history.
