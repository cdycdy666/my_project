"use client";

import { FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";

const ACCESS_CODE_STORAGE_KEY = "wisdom-advisor-access-code";

type LibrarySource = {
  id: string;
  title: string;
  sourceType: "录音转写" | "文档摘录" | "手动笔记";
  summary: string;
  tags: string[];
  createdAt: string;
  passageCount: number;
};

type AdviceResponse = {
  situation: string;
  summary: string;
  principles: string[];
  actions: string[];
  pitfalls: string[];
  evidence: Array<{
    sourceId: string;
    sourceTitle: string;
    sourceType: string;
    excerpt: string;
    score: number;
    tags: string[];
  }>;
  relatedSources: Array<{
    id: string;
    title: string;
    sourceType: string;
    summary: string;
    tags: string[];
  }>;
};

type LibraryPayload = {
  totalSources: number;
  totalPassages: number;
  tags: string[];
  sources: LibrarySource[];
};

type LibrarySourceDetail = {
  id: string;
  title: string;
  sourceType: "录音转写" | "文档摘录" | "手动笔记";
  summary: string;
  tags: string[];
  createdAt: string;
  passages: string[];
};

const QUICK_SCENARIOS = [
  {
    title: "边界表达",
    question: "朋友总是动不动就教育我，我心里很烦，但又不想把关系弄僵，我该怎么回应？",
    context: "对方是认识多年的朋友，平时也会帮我，但一聊天就容易高高在上。",
  },
  {
    title: "协作推进",
    question: "同事总是临时改需求，项目推进很卡，我该怎么和他重新拉齐预期？",
    context: "项目已经进入交付周，对方不是恶意，但习惯临时加内容。",
  },
  {
    title: "家庭关系",
    question: "爸妈一直催婚，我不想硬碰硬，但真的压力很大，怎么办？",
    context: "他们会找亲戚朋友轮流施压，我不想每次回家都陷入冲突。",
  },
  {
    title: "机会争取",
    question: "跳槽时想争取更高薪资，但又怕一谈就把 offer 谈没了，怎么办？",
    context: "我有一定成绩，但不确定自己有没有足够筹码开更高价。",
  },
  {
    title: "亲密关系",
    question: "伴侣一吵架就冷处理，我每次都很难受，但越追问关系越僵，该怎么办？",
    context: "对方不是要分开，只是习惯回避冲突，我想让沟通恢复正常。",
  },
  {
    title: "向上沟通",
    question: "领导总是临时改方向，我不敢硬顶，但团队已经被折腾得很累，怎么提意见更稳？",
    context: "领导强势但不是不讲理，我需要让他意识到频繁切换的代价。",
  },
  {
    title: "人情压力",
    question: "熟人总来找我帮忙，我其实不想接，但又怕拒绝了显得我不近人情，怎么办？",
    context: "对方不是一次两次了，而且很多事已经超出正常帮忙范围。",
  },
  {
    title: "团队管理",
    question: "老员工资历深、说话冲，新同事都不太敢合作，我作为负责人该怎么处理？",
    context: "我不想直接压人，但也不能让团队气氛一直这样下去。",
  },
  {
    title: "面试表达",
    question: "我一到面试就容易说散、说长，最后重点不突出，怎么调整表达更有说服力？",
    context: "我专业能力不差，但经常回答完自己都觉得没讲到点上。",
  },
  {
    title: "家庭决策",
    question: "家里人替我安排好了职业选择，但我心里并不想走那条路，怎么沟通才不伤关系？",
    context: "家里是出于好意，也投入了不少资源，所以我不想简单对抗。",
  },
  {
    title: "客户关系",
    question: "客户明明超出约定范围，却总是默认我会继续做，我该怎么把边界重新讲清楚？",
    context: "客户很重要，我不想因为一次沟通把关系搞砸。",
  },
];

const SCENARIO_BATCH_SIZE = 4;

function pickScenarioBatch(excludedTitles: string[] = []) {
  const excluded = new Set(excludedTitles);
  const pool = QUICK_SCENARIOS.filter((item) => !excluded.has(item.title));
  const candidates = pool.length >= SCENARIO_BATCH_SIZE ? pool : QUICK_SCENARIOS;
  const shuffled = [...candidates].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, SCENARIO_BATCH_SIZE);
}

export function WisdomAdvisorStudio() {
  const answerRef = useRef<HTMLDivElement | null>(null);
  const [library, setLibrary] = useState<LibraryPayload | null>(null);
  const [libraryError, setLibraryError] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [answer, setAnswer] = useState<AdviceResponse | null>(null);
  const [accessCode, setAccessCode] = useState("");
  const [question, setQuestion] = useState(QUICK_SCENARIOS[0].question);
  const [context, setContext] = useState(QUICK_SCENARIOS[0].context);
  const [scenarioBatch, setScenarioBatch] = useState(() => QUICK_SCENARIOS.slice(0, SCENARIO_BATCH_SIZE));
  const [selectedSource, setSelectedSource] = useState<LibrarySourceDetail | null>(null);
  const [selectedExcerpt, setSelectedExcerpt] = useState("");
  const [selectedMatchMeta, setSelectedMatchMeta] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  async function loadLibrary() {
    const response = await fetch("/api/wisdom-advisor/library", {
      cache: "no-store",
    });
    const payload = (await response.json()) as {
      ok: boolean;
      error?: string;
      library?: LibraryPayload;
    };
    if (!response.ok || !payload.ok || !payload.library) {
      throw new Error(payload.error || "知识库暂时不可用。");
    }
    setLibraryError("");
    setLibrary(payload.library);
  }

  useEffect(() => {
    void loadLibrary().catch((error: Error) => {
      setLibraryError(error.message);
    });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const savedCode = window.localStorage.getItem(ACCESS_CODE_STORAGE_KEY) || "";
    setAccessCode(savedCode);
  }, []);

  const latestSourceDate = useMemo(() => {
    if (!library?.sources.length) {
      return "--";
    }
    return new Date(library.sources[0].createdAt).toLocaleDateString("zh-CN");
  }, [library]);

  const systemStatus = libraryError ? "知识库待修复" : "Qwen + 本地知识库已联动";
  const openingQuestion = answer ? answer.summary.split("。")[0]?.trim() : "";

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitAsk();
  }

  async function submitAsk() {
    setAsking(true);
    setAskError("");

    try {
      const response = await fetch("/api/wisdom-advisor/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          context,
          accessCode,
        }),
      });
      const payload = (await response.json()) as {
        ok: boolean;
        error?: string;
        advice?: AdviceResponse;
      };
      if (!response.ok || !payload.ok || !payload.advice) {
        throw new Error(payload.error || "顾问暂时没有给出建议。");
      }
      if (typeof window !== "undefined") {
        const trimmedCode = accessCode.trim();
        if (trimmedCode) {
          window.localStorage.setItem(ACCESS_CODE_STORAGE_KEY, trimmedCode);
        } else {
          window.localStorage.removeItem(ACCESS_CODE_STORAGE_KEY);
        }
      }
      setAskError("");
      setAnswer(payload.advice);
      requestAnimationFrame(() => {
        answerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (error) {
      setAskError(error instanceof Error ? error.message : "提问失败。");
    } finally {
      setAsking(false);
    }
  }

  function useScenario(questionText: string, contextText: string) {
    setQuestion(questionText);
    setContext(contextText);
  }

  function handleScenarioClick(event: MouseEvent<HTMLButtonElement>, questionText: string, contextText: string) {
    event.preventDefault();
    useScenario(questionText, contextText);
  }

  function refreshScenarioBatch() {
    setScenarioBatch((currentBatch) => pickScenarioBatch(currentBatch.map((item) => item.title)));
  }

  async function openSourceDetail(sourceId: string, excerpt = "", matchMeta = "") {
    setDetailLoading(true);
    setDetailError("");
    setSelectedExcerpt(excerpt);
    setSelectedMatchMeta(matchMeta);

    try {
      const response = await fetch(`/api/wisdom-advisor/library?id=${encodeURIComponent(sourceId)}`, {
        cache: "no-store",
      });
      const payload = (await response.json()) as {
        ok: boolean;
        error?: string;
        source?: LibrarySourceDetail;
      };
      if (!response.ok || !payload.ok || !payload.source) {
        throw new Error(payload.error || "资料详情暂时不可用。");
      }
      setSelectedSource(payload.source);
    } catch (error) {
      setSelectedSource(null);
      setDetailError(error instanceof Error ? error.message : "资料详情加载失败。");
    } finally {
      setDetailLoading(false);
    }
  }

  function closeSourceDetail() {
    setSelectedSource(null);
    setSelectedExcerpt("");
    setSelectedMatchMeta("");
    setDetailError("");
    setDetailLoading(false);
  }

  return (
    <div className="tool-shell wisdom-shell">
      <section className="wisdom-chat-frame">
        <header className="wisdom-chat-header">
          <div className="wisdom-chat-copy">
            <div className="wisdom-header-ribbon">
              <span className="eyebrow">Counsel Console</span>
              <span className="wisdom-ribbon-copy">{systemStatus}</span>
            </div>
            <h1>个人沟通顾问台</h1>
            <p className="tool-intro">把真实处境讲出来，它会先替你过一遍局面，再把能直接拿去说、拿去做的动作给出来。</p>
            <section className="wisdom-proof-strip" aria-label="顾问能力概览">
              <article>
                <strong>{library?.totalSources ?? "--"}+</strong>
                <span>真实资料沉淀</span>
              </article>
              <article>
                <strong>先检索</strong>
                <span>不是凭空给建议</span>
              </article>
              <article>
                <strong>再生成</strong>
                <span>回答更像真人顾问</span>
              </article>
            </section>
          </div>
          <aside className="wisdom-hero-aside">
            <p className="micro-label">适合这样的时刻</p>
            <strong>事情不一定多严重，但你想把话说稳、把关系处理好。</strong>
            <div className="wisdom-inline-meta">
              <span>{library?.totalSources ?? "--"} 条资料</span>
              <span>最近更新 {latestSourceDate}</span>
            </div>
          </aside>
        </header>

        <div className="wisdom-scenario-prompt">
          <div className="wisdom-scenario-header">
            <span>你可以直接点一个，再改成自己的处境</span>
            <button className="wisdom-refresh-button" onClick={refreshScenarioBatch} type="button">
              换一批
            </button>
          </div>
          <div className="wisdom-hero-scenarios">
            {scenarioBatch.map((scenario) => (
              <button
                className="scenario-pill"
                key={scenario.title}
                onClick={(event) => handleScenarioClick(event, scenario.question, scenario.context)}
                type="button"
              >
                <span>{scenario.title}</span>
                <strong>{scenario.question}</strong>
              </button>
            ))}
          </div>
        </div>

        <section className="wisdom-thread" ref={answerRef}>
          <article className="chat-bubble chat-bubble-user">
            <div className="chat-bubble-head">
              <div className="chat-avatar">你</div>
              <div>
                <p className="micro-label">你想处理的处境</p>
                <strong>把问题先说清楚</strong>
              </div>
            </div>

            <form className="stack-form chat-composer" onSubmit={handleAsk}>
              <div className="wisdom-composer-hints" aria-label="提问提示">
                <span>说清楚你最卡的点</span>
                <span>补一句你最担心失去什么</span>
                <span>不需要把前因后果全讲完</span>
              </div>

              <label className="field">
                <span>你的问题</span>
                <textarea
                  name="question"
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="例如：同事总是临时改需求，我心里很烦，但又不想把关系搞僵，我该怎么说？"
                  rows={4}
                  required
                  value={question}
                />
              </label>

              <label className="field">
                <span>补充背景</span>
                <textarea
                  name="context"
                  onChange={(event) => setContext(event.target.value)}
                  placeholder="例如：对方是合作很久的同事，这次项目下周就要交付。"
                  rows={3}
                  value={context}
                />
              </label>

              <details className="wisdom-access-note">
                <summary>访问保护</summary>
                <div className="wisdom-access-inner">
                  <label className="field wisdom-access-field">
                    <span>访问码</span>
                    <input
                      autoComplete="off"
                      name="accessCode"
                      onChange={(event) => setAccessCode(event.target.value)}
                      placeholder="如果这个页面已开启访问保护，就在这里输入"
                      type="password"
                      value={accessCode}
                    />
                  </label>
                  <p>如果你公开分享这个页面，建议给试用者单独发访问码，而不是完全裸放在公网。</p>
                </div>
              </details>

              <div className="chat-composer-footer">
                <button
                  className="primary-button wisdom-submit"
                  disabled={asking}
                  onClick={() => {
                    void submitAsk();
                  }}
                  type="button"
                >
                  {asking ? "顾问正在整理判断..." : "生成顾问建议"}
                </button>
                <p>不用讲得很全，把你最卡、最怕、最难开口的那一点说出来就够了。</p>
              </div>
              {askError ? <p className="error-text">{askError}</p> : null}
            </form>
          </article>

          {answer ? (
            <article className="chat-bubble chat-bubble-advisor">
              <div className="chat-bubble-head">
                <div className="chat-avatar chat-avatar-advisor">顾问</div>
                <div>
                  <p className="micro-label">顾问回答</p>
                  <strong>{answer.situation}</strong>
                </div>
              </div>

              <article className="insight-card wisdom-summary-card">
                {openingQuestion ? <p className="wisdom-summary-kicker">一句总判断 · {openingQuestion}</p> : null}
                <p>{answer.summary}</p>
              </article>

              <div className="wisdom-brief-grid">
                <article className="insight-card wisdom-list-card">
                  <div className="wisdom-list-head">
                    <p className="micro-label">先定判断</p>
                    <span>这件事该怎么看</span>
                  </div>
                  <ul className="plain-list wisdom-bullet-list">
                    {answer.principles.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>

                <article className="insight-card wisdom-list-card">
                  <div className="wisdom-list-head">
                    <p className="micro-label">下一步动作</p>
                    <span>先从哪里下手</span>
                  </div>
                  <ul className="plain-list wisdom-bullet-list">
                    {answer.actions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>
              </div>

              <article className="insight-card caution-card wisdom-list-card">
                <div className="wisdom-list-head">
                  <p className="micro-label">尽量避免</p>
                  <span>最容易搞坏的处理方式</span>
                </div>
                <ul className="plain-list wisdom-bullet-list">
                  {answer.pitfalls.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <details className="wisdom-evidence-wrap">
                <summary>这次回答参考了哪些资料</summary>
                <div className="wisdom-reference-grid">
                  <article className="markdown-card evidence-card">
                    <div className="wisdom-list-head">
                      <p className="micro-label">命中片段</p>
                      <span>{answer.evidence.length} 条证据</span>
                    </div>
                    <div className="evidence-stack">
                      {answer.evidence.map((item) => (
                        <button
                          className="evidence-item evidence-item-button"
                          key={`${item.sourceId}-${item.excerpt}`}
                          onClick={() =>
                            void openSourceDetail(
                              item.sourceId,
                              item.excerpt,
                              `${item.sourceType} · 匹配度 ${Math.round(item.score * 100)}%`
                            )
                          }
                          type="button"
                        >
                          <div className="evidence-head">
                            <strong>{item.sourceTitle}</strong>
                            <span>
                              {item.sourceType} · 匹配度 {Math.round(item.score * 100)}%
                            </span>
                          </div>
                          <p>{item.excerpt}</p>
                        </button>
                      ))}
                    </div>
                  </article>

                  <article className="insight-card related-card">
                    <div className="wisdom-list-head">
                      <p className="micro-label">关联来源</p>
                      <span>{answer.relatedSources.length} 份资料</span>
                    </div>
                    <div className="related-source-list">
                      {answer.relatedSources.map((item) => (
                        <button
                          className="related-source-item related-source-button"
                          key={item.id}
                          onClick={() => void openSourceDetail(item.id)}
                          type="button"
                        >
                          <strong>{item.title}</strong>
                          <p>{item.summary}</p>
                        </button>
                      ))}
                    </div>
                  </article>
                </div>
              </details>
            </article>
          ) : (
            <article className="chat-bubble chat-bubble-placeholder">
              <div className="chat-bubble-head">
                <div className="chat-avatar chat-avatar-advisor">顾问</div>
                <div>
                  <p className="micro-label">顾问回答</p>
                  <strong>等你把问题说出来</strong>
                </div>
              </div>
              <p className="chat-placeholder-copy">这里会先帮你判断局面，再给你几个真能拿去用的动作和提醒，不会只给空泛的大道理。</p>
            </article>
          )}
        </section>
      </section>

      {(selectedSource || detailLoading || detailError) && (
        <div className="wisdom-detail-overlay" onClick={closeSourceDetail} role="presentation">
          <section
            aria-labelledby="wisdom-detail-title"
            className="wisdom-detail-sheet"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="wisdom-detail-head">
              <div>
                <p className="micro-label">资料详情</p>
                <h2 id="wisdom-detail-title">{selectedSource?.title || "正在加载资料..."}</h2>
              </div>
              <button className="wisdom-detail-close" onClick={closeSourceDetail} type="button">
                关闭
              </button>
            </div>

            {detailError ? <p className="error-text">{detailError}</p> : null}
            {detailLoading ? <p className="chat-placeholder-copy">正在读取这份资料的详细内容...</p> : null}

            {selectedSource ? (
              <div className="wisdom-detail-content">
                <div className="wisdom-detail-meta">
                  <span>{selectedSource.sourceType}</span>
                  <span>{new Date(selectedSource.createdAt).toLocaleDateString("zh-CN")}</span>
                  <span>{selectedSource.passages.length} 段内容</span>
                </div>

                {selectedSource.tags.length ? (
                  <div className="note-tags wisdom-detail-tags">
                    {selectedSource.tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </div>
                ) : null}

                {selectedExcerpt ? (
                  <article className="insight-card wisdom-detail-highlight">
                    <div className="wisdom-list-head">
                      <p className="micro-label">本次命中片段</p>
                      <span>{selectedMatchMeta || "参考片段"}</span>
                    </div>
                    <p>{selectedExcerpt}</p>
                  </article>
                ) : null}

                <article className="insight-card wisdom-detail-summary">
                  <div className="wisdom-list-head">
                    <p className="micro-label">摘要</p>
                    <span>这份资料在讲什么</span>
                  </div>
                  <p>{selectedSource.summary}</p>
                </article>

                <article className="insight-card wisdom-detail-passages">
                  <div className="wisdom-list-head">
                    <p className="micro-label">原始段落</p>
                    <span>按知识库切分后的内容</span>
                  </div>
                  <div className="wisdom-detail-passage-list">
                    {selectedSource.passages.map((passage, index) => (
                      <div className="wisdom-detail-passage" key={`${selectedSource.id}-${index}`}>
                        <strong>片段 {index + 1}</strong>
                        <p>{passage}</p>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            ) : null}
          </section>
        </div>
      )}
    </div>
  );
}
