# Product Requirements Document: Personal AI Tools Website

**Version**: 1.0
**Date**: 2026-04-29
**Author**: Sarah (Product Owner)
**Quality Score**: 93/100

---

## Executive Summary

This project is a personal Chinese website for recording ongoing learning, summarizing development progress, and collecting self-built AI tools in one place. The first version should feel simple, thoughtful, and easy to maintain, with a clear focus on personal growth and tool building rather than commercial promotion.

The site will help the owner preserve a visible trail of learning notes, phase summaries, AI experiments, and curated resources. It should also make it easy for future visitors to quickly understand what tools have been built, what each tool does, and where to access them.

The initial release will prioritize a lightweight content structure: tool cards, learning notes, stage summaries, and resource collections. Future versions can add detail pages, search, tags, analytics, or a CMS after the core habit of publishing content is established.

---

## Problem Statement

**Current Situation**: Personal AI tools, learning plans, study notes, and useful resources are likely scattered across different places, making them hard to review, share, and maintain over time.

**Proposed Solution**: Build a clean Chinese personal website that organizes AI tools, learning notes, phase summaries, and resource collections into a coherent personal knowledge hub.

**Business Impact**: The website creates a durable personal archive, improves self-review efficiency, and provides a polished public home for personal AI projects and learning progress.

---

## Success Metrics

**Primary KPIs:**
- Content coverage: At least 3 AI tool cards, 3 learning notes or summaries, and 8 resource links added before first launch.
- Update efficiency: Adding or editing a tool, note, or resource should take less than 10 minutes.
- Navigation clarity: A first-time visitor should be able to find tools, notes, and resources from the homepage within one click.

**Validation**: Validate after MVP launch by reviewing whether the initial content is complete, whether updates are easy to make, and whether the main sections are visually and structurally clear.

---

## User Personas

### Primary: Site Owner

- **Role**: Personal builder and learner.
- **Goals**: Record learning progress, summarize stages, collect resources, and display self-built AI tools.
- **Pain Points**: Content is scattered, progress is hard to review, and project links are not organized in a presentable way.
- **Technical Level**: Intermediate to advanced.

### Secondary: Visitor

- **Role**: Friend, collaborator, recruiter, or someone interested in the owner's AI tools and learning path.
- **Goals**: Quickly understand what the owner is building, what each tool does, and what topics the owner is studying.
- **Pain Points**: Without a structured site, it is hard to discover the owner's projects and learning focus.
- **Technical Level**: Mixed.

---

## User Stories & Acceptance Criteria

### Story 1: Browse AI Tools

**As a** visitor  
**I want to** see a list of AI tools with short descriptions and links  
**So that** I can quickly understand what has been built and open the tools that interest me.

**Acceptance Criteria:**
- [ ] The homepage or tools section displays tool cards with name, short description, status, and link.
- [ ] Each card clearly distinguishes available tools from planned or in-progress tools.
- [ ] If a tool has no public link yet, the card still displays its current status without creating a broken link.

### Story 2: Record Learning Notes And Stage Summaries

**As the** site owner  
**I want to** publish learning notes and phase summaries  
**So that** I can review my progress and preserve useful insights over time.

**Acceptance Criteria:**
- [ ] The site includes a learning section for notes and stage summaries.
- [ ] Each entry includes a title, date or phase, topic, and summary.
- [ ] The content structure supports both short notes and longer stage reviews.

### Story 3: Maintain Curated Resources

**As the** site owner  
**I want to** collect AI tools, technical articles, courses, and videos  
**So that** useful references are easy to revisit.

**Acceptance Criteria:**
- [ ] The site includes a resources section grouped by category.
- [ ] Each resource includes a title, type, short reason for saving it, and external link.
- [ ] The section can support categories such as AI tools, technical articles, courses, and videos.

### Story 4: Navigate The Site Easily

**As a** visitor  
**I want to** understand the site structure immediately  
**So that** I can move between tools, learning notes, and resources without confusion.

**Acceptance Criteria:**
- [ ] The first screen clearly signals the site's purpose.
- [ ] Primary navigation links to tools, learning, and resources.
- [ ] The layout works well on desktop and mobile.

---

## Functional Requirements

### Core Features

**Feature 1: Homepage Overview**
- Description: Introduce the site as a personal AI tools and learning archive.
- User flow: Visitor opens the site, reads a concise introduction, and sees entry points for tools, learning notes, and resources.
- Edge cases: If some sections have limited content, the layout should still look intentional.
- Error handling: External links should open safely and avoid broken empty states.

**Feature 2: AI Tool Cards**
- Description: Display self-built AI tools as simple cards with name, summary, status, and link.
- User flow: Visitor scans cards, compares tools, and opens an available tool link.
- Edge cases: Some tools may be private, experimental, or unfinished.
- Error handling: Unavailable links should be omitted or replaced with a clear status.

**Feature 3: Learning Notes And Stage Summaries**
- Description: Present learning records as dated or phased entries.
- User flow: Visitor or owner browses recent notes and reads summaries by topic.
- Edge cases: Notes may vary in length.
- Error handling: Empty states should guide future content additions without feeling broken.

**Feature 4: Resource Collection**
- Description: Organize saved AI tools, technical articles, courses, and videos.
- User flow: Visitor filters or scans grouped resources and opens external references.
- Edge cases: Resources may belong to multiple categories in future versions.
- Error handling: Invalid links should be easy to update in the content source.

### Out of Scope

- Full user account system.
- Comments, likes, or community features.
- Complex CMS integration.
- Search and advanced filtering in MVP.
- Individual detail pages for each AI tool in MVP.
- Multilingual support in MVP.

---

## Technical Constraints

### Performance

- Initial page should load quickly on desktop and mobile.
- Static content should be preferred for MVP to reduce maintenance cost.
- Images and assets should be optimized if added.

### Security

- External links should use safe link attributes when opening new tabs.
- No private credentials, internal service URLs, or secrets should be exposed in client code.
- If future tools require authentication, they should be handled outside the static content layer.

### Integration

- **External AI Tools**: Tool cards link to hosted tools or repositories when available.
- **Resource Links**: Resource items link to external articles, courses, videos, or AI tools.
- **Future CMS**: Content can later move to Notion, Markdown files, or another CMS if publishing volume grows.

### Technology Stack

- Recommended MVP stack: Next.js or another React-based static site setup.
- Content source: Local structured data or Markdown for the first version.
- Language: Chinese-first.
- Compatibility: Responsive support for modern desktop and mobile browsers.

---

## MVP Scope & Phasing

### Phase 1: MVP

- Chinese homepage with clear personal positioning.
- AI tools section using cards with description, status, and links.
- Learning notes and stage summaries section.
- Resource collection section with categories for AI tools, technical articles, courses, and videos.
- Responsive visual design that is simple but polished.

**MVP Definition**: A visitor can open the website, understand the owner's focus, browse AI tools, read learning summaries, and access curated resources without needing any backend system.

### Phase 2: Enhancements

- Dedicated detail pages for important AI tools.
- Tagging and filtering for notes and resources.
- Markdown-based publishing workflow.
- Better project screenshots or demos.
- Deployment automation.

### Future Considerations

- Notion or CMS integration for easier updates.
- Search across notes, tools, and resources.
- Timeline view for learning and project progress.
- Analytics for understanding which tools or resources visitors use most.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| Content maintenance becomes inconsistent | Medium | High | Keep MVP content editing lightweight and structured. |
| Scope expands before launch | Medium | Medium | Limit MVP to cards, notes, summaries, and resources. |
| Visual design feels generic | Medium | Medium | Use a focused design direction and avoid template-like layouts. |
| Tool links change or become unavailable | Medium | Low | Store links in one structured content source for quick updates. |

---

## Dependencies & Blockers

**Dependencies:**
- Initial AI tool names, descriptions, statuses, and links.
- Initial learning note or stage summary content.
- Initial resource links grouped by category.
- Hosting target, such as Vercel, Netlify, GitHub Pages, or a personal server.

**Known Blockers:**
- None for local MVP implementation. Real public launch will require choosing a deployment target and domain strategy.

---

## Appendix

### Glossary

- **AI Tool Card**: A compact display unit for a self-built AI tool, including its name, summary, status, and link.
- **Stage Summary**: A reflective learning entry that summarizes progress over a period or topic.
- **Resource Collection**: A categorized list of saved references such as tools, articles, courses, and videos.

### References

- Current workspace: `/Users/chendingyu/MyWeb`
- Initial user goal: self-recording and personal AI tool aggregation.

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage of business, functional, UX, and technical dimensions.*
