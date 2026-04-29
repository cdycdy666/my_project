import type { CSSProperties } from "react";
import { notes, resourceTypes, resources, tools } from "../data/site";

export default function Home() {
  return (
    <>
      <div className="grain" aria-hidden="true" />
      <header className="site-header">
        <a className="brand" href="#top" aria-label="回到顶部">
          <span className="brand-mark">CY</span>
          <span>AI 工具与学习记录</span>
        </a>
        <nav className="nav" aria-label="主导航">
          <a href="#tools">工具</a>
          <a href="#notes">笔记</a>
          <a href="#resources">资源</a>
        </nav>
      </header>

      <main id="top" className="page-shell">
        <aside className="profile-panel" aria-label="个人简介">
          <div className="portrait-wrap">
            <img
              className="signal-map"
              src="/workbench-signal.svg"
              alt="抽象的学习路径与工具节点图"
            />
          </div>
          <p className="eyebrow">Personal Workbench</p>
          <h1>把 AI 工具、学习过程和好资源，收进同一个工作台。</h1>
          <p className="intro">
            这里记录我正在搭建的 AI 工具、阶段性学习总结，以及值得反复回看的技术资源。
          </p>
          <div className="quick-stats" aria-label="站点概览">
            <span>
              <strong>{tools.length}</strong> 个工具
            </span>
            <span>
              <strong>{notes.length}</strong> 篇记录
            </span>
            <span>
              <strong>{resources.length}</strong> 个资源
            </span>
          </div>
        </aside>

        <section className="content-flow" aria-label="主要内容">
          <section className="section-block current-focus" aria-labelledby="focus-title">
            <div>
              <p className="eyebrow">Now Building</p>
              <h2 id="focus-title">当前重点</h2>
            </div>
            <p>
              第一版先保持轻量：工具用卡片展示，学习内容沉淀为笔记与阶段总结，资源按类型归档。
              后续可以逐步加详情页、标签、搜索、数据库和 Notion 同步。
            </p>
          </section>

          <section id="tools" className="section-block" aria-labelledby="tools-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">AI Tools</p>
                <h2 id="tools-title">个人 AI 工具</h2>
              </div>
              <span className="section-count">工具卡片</span>
            </div>
            <div className="tool-grid">
              {tools.map((tool) => (
                <article
                  className="tool-card"
                  key={tool.name}
                  style={{ "--accent": tool.accent } as CSSProperties}
                >
                  <div className="card-top">
                    <h3>{tool.name}</h3>
                    <span className="status">{tool.status}</span>
                  </div>
                  <p className="card-copy">{tool.description}</p>
                  {tool.url ? (
                    <a className="card-link" href={tool.url} target="_blank" rel="noreferrer">
                      查看工具
                    </a>
                  ) : (
                    <span className="card-link muted-link" aria-disabled="true">
                      暂未公开
                    </span>
                  )}
                </article>
              ))}
            </div>
          </section>

          <section id="notes" className="section-block" aria-labelledby="notes-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Learning Log</p>
                <h2 id="notes-title">学习笔记与阶段总结</h2>
              </div>
              <span className="section-count">持续记录</span>
            </div>
            <div className="note-list">
              {notes.map((note) => (
                <article className="note-item" key={note.title}>
                  <time className="note-date">{note.date}</time>
                  <div>
                    <h3>{note.title}</h3>
                    <p>{note.summary}</p>
                    <div className="note-tags">
                      {note.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section id="resources" className="section-block" aria-labelledby="resources-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Bookmarks</p>
                <h2 id="resources-title">资源收藏</h2>
              </div>
              <div className="filter-bar" aria-label="资源分类">
                {resourceTypes.map((type) => (
                  <span className={type === "全部" ? "filter-chip is-active" : "filter-chip"} key={type}>
                    {type}
                  </span>
                ))}
              </div>
            </div>
            <div className="resource-grid">
              {resources.map((resource) => (
                <article
                  className="resource-card"
                  key={resource.title}
                  style={{ "--resource-color": resource.color } as CSSProperties}
                >
                  <span className="resource-type">{resource.type}</span>
                  <h3>{resource.title}</h3>
                  <p>{resource.reason}</p>
                  <a className="card-link" href={resource.url} target="_blank" rel="noreferrer">
                    打开资源
                  </a>
                </article>
              ))}
            </div>
          </section>
        </section>
      </main>

      <footer className="site-footer">
        <span>Built as a living archive.</span>
        <a
          href="https://github.com/cdycdy666/my_project/blob/main/personal-ai-website/docs/personal-website-prd.md"
          target="_blank"
          rel="noreferrer"
        >
          查看 PRD
        </a>
      </footer>
    </>
  );
}
