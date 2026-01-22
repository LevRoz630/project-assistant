# TODO

## Planned Features

- [ ] Give agent access to web
- [x] Connect with OneNote - native Microsoft integration for mobile note-taking
- [ ] Connect with GitHub - track issues, PRs, commits
- [ ] Investigate different instruction options for different functions
- [ ] Investigate the safeguards against prompt injection
- [ ] Set Up Whatsapp and telegram connections
- [ ] Fix the connection to the st andrews email

## Backlog

- [ ] Telegram Bot - mobile access without native app
- [ ] Deploy, make available on phone
- [ ] Joplin integration (desktop only) - already implemented, use when Joplin desktop is running

---

## Decision Log

### 2026-01-22: OneNote over Joplin for mobile notes

**Decision:** Use OneNote instead of Joplin as the primary note-taking integration.

**Context:** Needed a way to edit notes on mobile that syncs with the assistant.

**Options Considered:**
1. **Joplin** - REST API only works on desktop app; mobile app doesn't expose API
2. **Joplin via OneDrive sync** - Joplin stores notes with UUID filenames, requires parsing metadata
3. **Obsidian** - Plain markdown files, but requires plugin setup for OneDrive sync on mobile
4. **OneNote** - Native Microsoft app, built-in sync, Graph API access

**Decision Rationale:**
- OneNote has native mobile apps (iOS/Android) with seamless sync
- Already using Microsoft Graph API for other integrations (OneDrive, Tasks, Calendar)
- No additional setup required - just sign in with same Microsoft account
- Content automatically indexed in vector store for AI search

**Trade-offs:**
- OneNote uses HTML internally (converted to/from markdown in API)
- Less control over file structure compared to plain markdown
- Joplin integration still available for desktop users who prefer it
