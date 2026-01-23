# Personal AI Assistant — Development Plan

## Current State

A working personal productivity assistant integrated with Microsoft 365:

| Component | Status | Technology |
|-----------|--------|------------|
| Authentication | Done | Azure AD OAuth (MSAL) |
| Notes/Diary | Planned | Joplin (see ADR-001) |
| AI Chat + RAG | Done | LangChain + ChromaDB |
| Tasks | Done | Microsoft To Do |
| Calendar | Done | Outlook Calendar |
| Email | Done | Outlook Mail (read + send) |
| AI Actions | Done | Approval workflow UI |
| Auto-sync | Done | Background vector indexing |

**Architecture:**
```
React Frontend → FastAPI Backend → Microsoft Graph API
                      ↓
                LangChain + ChromaDB (RAG)
                      ↓
                OpenAI / Anthropic API
```

---

## Completed Milestones

- [x] **M1:** Foundation — OAuth, basic UI, project structure
- [x] **M2:** Notes & Diary — OneDrive CRUD, folder structure
- [x] **M3:** AI Chat + RAG — vector embeddings, auto-sync
- [x] **M4:** Tasks — Microsoft To Do integration
- [x] **M5:** Calendar & Email — read/write calendar, email context
- [x] **M6:** AI Actions — approval workflow for AI-proposed changes

---

## Future Enhancements

### M7: Agentic Workflows (LangGraph)
**Goal:** Enable multi-step AI workflows that can chain actions.

- [ ] Integrate LangGraph for workflow orchestration
- [ ] Email triage agent (summarizes + drafts replies)
- [ ] Study assistant (generates flashcards from notes)

### M8: Notifications & Reminders
**Goal:** Proactive assistant that surfaces relevant info.

- [ ] Daily digest email/notification (intergation with arxiv summaries)
- [ ] Task due date reminders
- [ ] Calendar event prep summaries

### M9: Mobile Access
**Goal:** Use from phone/tablet.

- [ ] Responsive UI improvements
- [ ] PWA support (installable app)
- [ ] Push notifications

### M10: Deployment
**Goal:** Run as a hosted service.

- [ ] Production database (PostgreSQL for sessions)
- [ ] Cloud deployment (Fly.io)
- [ ] HTTPS with proper domain

### M11: Advanced RAG
**Goal:** Better retrieval and context.

- [ ] Hybrid search (keyword + semantic)
- [ ] Citation sources in responses
- [ ] Conversation memory persistence
- [ ] Document chunking improvements

### M12: Voice Interface
**Goal:** Hands-free interaction.

- [ ] Speech-to-text input
- [ ] Text-to-speech responses

---

## Technical Debt / Improvements

- [ ] Add unit tests for backend services
- [ ] Add E2E tests for critical flows
- [ ] Implement proper error handling UI
- [ ] Add loading states throughout
- [ ] Token refresh handling improvements
- [ ] Rate limiting for API endpoints

---

## Configuration

Current setup requires:

| Item | Source |
|------|--------|
| Azure Client ID | Azure Portal → App Registration |
| Azure Client Secret | Azure Portal → Certificates & secrets |
| OpenAI API Key | platform.openai.com |
| (Optional) Anthropic API Key | console.anthropic.com |

**API Permissions (Microsoft Graph - Delegated):**
- User.Read
- Files.ReadWrite.All
- Tasks.ReadWrite
- Calendars.ReadWrite
- Mail.Read
- Mail.Send

---

## Running Locally

```bash
# Docker
docker-compose up --build

# Manual
cd backend && uvicorn main:app --reload
cd frontend && npm run dev
```

Open http://localhost:5173
