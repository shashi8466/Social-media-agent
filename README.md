# Social Media Content Agent

> Multi-agent AI workflow for automated social media content generation — powered by **Claude API** + **DALL-E 3**

---

## 🏗️ Architecture

```
User Input (Topic + Platforms)
          ↓
    Manager Agent
          ↓
  ┌───────────────────────────────────────────────────┐
  │  Research Agent  → News feeds + company context   │
  │  Content Agent   → Claude (LinkedIn/IG/X/Reels)   │
  │  Hashtag Agent   → Claude (platform-optimized)    │
  │  Image Agent     → Claude prompt + DALL-E 3       │
  │  Database Agent  → SQLite persistence             │
  └───────────────────────────────────────────────────┘
          ↓
    [Future] Scheduler Agent → LinkedIn/Meta/X API
```

---

## 🚀 Quick Start

### 1. Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Dashboard: http://localhost:3000

---

## 📁 Project Structure

```
social-media-agent/
│
├── backend/
│   ├── app.py                    # FastAPI entry point
│   ├── requirements.txt
│   ├── .env                      # API keys (NEVER commit this)
│   │
│   ├── agents/
│   │   ├── manager_agent.py      # Orchestrator
│   │   ├── research_agent.py     # News & web research
│   │   ├── content_agent.py      # Claude content generation
│   │   ├── hashtag_agent.py      # Hashtag optimization
│   │   ├── image_agent.py        # Claude + DALL-E 3
│   │   ├── database_agent.py     # SQLite CRUD
│   │   └── scheduler_agent.py    # Phase 5 stub
│   │
│   ├── prompts/
│   │   ├── linkedin.txt
│   │   ├── instagram.txt
│   │   ├── twitter.txt
│   │   ├── reels.txt
│   │   ├── hashtags.txt
│   │   └── image.txt
│   │
│   ├── database/posts.db         # Auto-created on first run
│   └── output/                   # Generated image files
│
└── frontend/
    ├── app/
    │   ├── page.tsx              # Dashboard
    │   ├── generate/page.tsx     # Content generation
    │   └── posts/page.tsx        # Post library
    └── components/
        ├── Sidebar.tsx
        ├── StatCard.tsx
        ├── GenerateForm.tsx
        ├── ResultsPanel.tsx
        └── RecentPosts.tsx
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/generate` | Run full pipeline |
| `GET`  | `/api/posts` | List all posts |
| `GET`  | `/api/posts/{id}` | Get single post |
| `DELETE` | `/api/posts/{id}` | Delete post |
| `GET`  | `/api/stats` | Platform statistics |

### Generate Request Body
```json
{
  "topic": "AI Automation",
  "platforms": ["linkedin", "instagram", "twitter", "reels"],
  "generate_images": true,
  "run_research": true
}
```

---

## 🤖 Agents

| Agent | Role | AI Used |
|-------|------|---------|
| Manager Agent | Orchestrates the pipeline | — |
| Research Agent | Fetches news & synthesizes context | Claude |
| Content Agent | Generates platform-specific posts | Claude (`claude-sonnet-4-5`) |
| Hashtag Agent | Creates optimized hashtag sets | Claude |
| Image Agent | Prompt engineering + image generation | Claude + DALL-E 3 |
| Database Agent | Persists all data to SQLite | — |
| Scheduler Agent | Social media posting (Phase 5) | — |

---

## 🗺️ Roadmap

- [x] Phase 1 & 2: Content Generation (LinkedIn, Instagram, X, Reels)
- [x] Phase 3: Research Agent
- [x] Phase 4: Image Agent (Claude + DALL-E 3)
- [ ] Phase 5: Scheduler Agent (LinkedIn API, Meta API, Twitter API)
- [ ] Phase 6: Approval workflow UI
- [ ] Phase 7: Analytics & performance tracking

---

## ⚙️ Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-proj-...
```

---

## 🏢 Company: GigaTech Services

- AI Development & Automation
- Web Development
- Mobile App Development
- Cloud Solutions
