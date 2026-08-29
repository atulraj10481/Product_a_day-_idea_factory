# ReferralFlow AI – Automated Referral & Review Workflow

## 1. Company Profile
MyAdvice is an AI‑powered growth platform that serves medical, dental, and legal practices. Its core offerings include AI‑driven marketing automation, reputation management, lead generation, and actionable business insights. Customers struggle with limited marketing expertise, time‑consuming manual outreach, and managing online reputation across multiple channels. MyAdvice’s vision is to become the single AI‑engine that fuels practice growth by automating acquisition, engagement, and reputation loops, allowing providers to focus on care while the platform drives new business.

## 2. Job Description Summary
The Associate Product Manager will partner with senior product leadership, engineering, data science, and go‑to‑market teams to define, prioritize, and ship product features for MyAdvice’s AI‑driven marketing suite. Responsibilities include gathering market & user insights, translating them into clear requirements, managing backlogs, coordinating cross‑functional sprints, and measuring product outcomes. The role also supports roadmap communication, competitive analysis, and early‑stage experimentation for new AI‑powered workflows.

## 3. Product Idea
**Problem Addressed:**
MyAdvice’s internal teams struggle to turn inbound leads into qualified referrals and positive online reviews across medical, dental, and legal practices. The current process is fragmented across marketing automation, reputation management, and CRM tools, leading to delays, inconsistent messaging, and missed revenue opportunities.

## 4. Workflow / Architecture
```mermaid
graph TD;
    A[Lead Capture (Webform/Ads)] --> B[AI Enrichment (Python ML Service)];
    B --> C[Segment & Scoring (Node.js Service)];
    C --> D[Automated Outreach (Email/SMS Templates)];
    D --> E[Review Prompt Scheduler];
    E --> F[Reputation Dashboard (React UI)];
    C --> G[Referral Matching Engine];
    G --> H[Referral Notification to Partner Practices];
    H --> I[Closed‑Loop Analytics];
```

## 5. Tech Stack
```text
Node.js (Express) for API orchestration, Python (FastAPI + scikit‑learn/transformers) for AI enrichment and scoring, React for the front‑end dashboard, and OpenAI API (via LangChain) as the best‑fit tool for natural‑language generation and sentiment analysis.
```

## 6. MVP Score
78/100 – The concept is technically feasible using existing AI APIs and MyAdvice’s data pipelines, with a moderate development timeline (3‑4 months). Market size is strong given the high demand for automated referral and reputation tools in regulated professional services. Competitive advantage hinges on deep AI personalization and seamless integration across practice types, though differentiation from generic CRM/marketing platforms will require rapid go‑to‑market execution.

---
*Source: LINKEDIN | Scraped: Aug 28, 2026 | Role: Associate Product Manager*
