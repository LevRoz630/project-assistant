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
- [ ] Daily planning agent (reads calendar + tasks → proposes plan)
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

### M10: Multi-user / Deployment
**Goal:** Run as a hosted service.

- [ ] User isolation (separate vector stores per user)
- [ ] Production database (PostgreSQL for sessions)
- [ ] Cloud deployment (Azure App Service / Railway / Fly.io)
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
- [ ] Wake word activation (optional)

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

---

## Architecture Decision Records

Documenting key decisions for future developers.

### ADR-001: Joplin for Notes (replacing OneDrive + Markdown)

**Date:** 2026-01-22

**Status:** Accepted

**Context:**
The original design used OneDrive + raw Markdown files for notes. This works but has limitations:
- No offline support (requires internet for all operations)
- No dedicated note-taking UX (just files in a folder)

Alternatives considered:
- **Obsidian** — Excellent local app, but no API for integration. Would require accessing local vault files (breaks web deployment) or manual folder-in-OneDrive workaround.
- **OneNote** — Already in M365 stack, great offline support, but proprietary format. Parsing OneNote pages for RAG is painful (complex HTML with positioning data, embedded content). Poor data portability.
- **Joplin** — Markdown-based, local-first with offline support, has REST API, supports OneDrive sync natively, open source.

**Decision:**
Use **Joplin** for notes storage.

**Rationale:**
1. **RAG quality** — Joplin stores plain Markdown. Parsing for embeddings is trivial and clean. This directly impacts AI assistant quality.
2. **Offline support** — Local-first architecture means notes work without internet.
3. **API access** — Joplin's REST API allows programmatic access to notes.
4. **Data portability** — Markdown files, no lock-in.
5. **OneDrive sync** — Still syncs to OneDrive, maintaining some M365 integration.

**Trade-offs accepted:**
- Requires Joplin desktop app installed and running for API access
- Separate from M365 OAuth flow (Joplin uses OneDrive as storage, not Graph API)
- Less polished than OneNote apps
- No handwriting/drawing support

**Implementation notes:**
- Joplin REST API runs on localhost when desktop app is open
- Will need to handle case when Joplin isn't running (graceful degradation)
- Sync configured to use OneDrive folder
