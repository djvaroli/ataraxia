# Ataraxia delivery and operations

Build a useful habit tracker first, then connect daily discoveries and their Library. Keep the application runnable with deterministic fixtures before adding external credentials. Backups can be absent throughout development, but automated backups to a dedicated GCP project and a successful restore are required before relying on the app for personal history.

The design session produces documentation only. The following are GitHub issue drafts for future implementation; their A-series identifiers are local references, not existing GitHub issue numbers.

## Milestones and issue workflow

| Milestone | Issues | Outcome |
| --- | --- | --- |
| M1 Habits work locally | A01–A04 | Sign in, create habits, record/undo, inspect the mobile calendar |
| M2 Daily learning works | A05–A07 | All five categories, bounded generation, durable Library |
| M3 Ready for personal use | A08–A09 | Export, targeted checks, HTTPS deployment, backup and restore |

Create GitHub issues from the drafts below as implementation starts. Use labels such as `feature`, `infra`, `quality`, and `later`, plus milestone and dependency links. A pull request references its issue, explains the resulting behavior, and lists relevant validation. Keep each change reviewable; a broad issue may be delivered through a few small pull requests. Do not create an issue for every helper function.

Update these design documents when an implementation changes a user-visible rule or a material technical decision. Keep setup commands, environment variables, and runbooks close to their eventual implementation. Major decision reversals can get a short ADR; routine library or function choices do not need one.

## Initial GitHub issue drafts

### A01 Establish the runnable project

Labels: `infra`. Milestone: M1. Dependencies: none.

Create the frontend/backend layout, locked dependencies, and Compose services for nginx, frontend, API, worker, and Redis. Add clear environment examples, healthchecks, and CI commands. Use separate entry points for API and worker; do not implement a job framework yet.

Acceptance: one documented Compose command starts the development stack; nginx serves the frontend and proxies a health request; only intended edge ports are published; Redis uses a named volume, persistence, and no eviction. Build/lint/typecheck commands run in documented environments. No Osmy configuration or secrets are imported.

### A02 Add owner authentication and preferences

Labels: `feature`. Milestone: M1. Dependencies: A01.

Add Firebase Google sign-in, verified bearer tokens, an explicit allowed UID, and profile settings for time zone, enabled categories, and streak visibility. Provide a local Firebase emulator profile. Document dedicated project/owner setup and nginx auth-helper routing.

Acceptance: missing/invalid tokens and a valid non-owner identity cannot access data or generation; the owner can sign in/out and persist preferences; the time zone is validated. Test auth policy with fakes and manually verify the actual redirect flow on mobile before M3. Test configuration cannot silently authorize users in deployment.

### A03 Implement habit rules and storage

Labels: `feature`. Milestone: M1. Dependencies: A01, A02.

Implement domain models, repository protocols, Redis storage, and habit endpoints. Include schedule versions, dated completion, archive/restore, month queries, and authoritative statistics as specified in [Product and experience](product.md).

Acceptance: repeated Complete/Undo requests are idempotent; future or unscheduled completion is rejected; corrections update statistics; schedule changes preserve earlier due dates; archive/restore preserves history. Focused unit tests cover these rules and a small Redis integration check exercises the repository.

### A04 Build the habit experience

Labels: `feature`. Milestone: M1. Dependencies: A03.

Build Today, habit creation/editing, the month calendar, weekly consistency, completion milestones, and optional streak display. Use shared date/status components and optimistic updates with rollback.

Acceptance: a user can complete or undo directly from Today and correct a past calendar day; filled circles match persisted data after reload; a failed request restores the correct UI state. Verify a 360-pixel viewport, keyboard interaction, screen-reader labels, and reduced motion. Archive and past corrections remain discoverable.

### A05 Implement discovery storage and the worker with fixtures

Labels: `feature`. Milestone: M2. Dependencies: A01, A02.

Create typed category payloads, daily slots, history indexes, source identities, annotations, and worker orchestration using deterministic fake sources and generation. Implement scheduling, current-day ensure, bounded retries, claim recovery, and atomic publication.

Acceptance: one ready item per date/category; refreshing and re-requesting do not duplicate it; a crash/expired claim can be recovered; an unavailable category leaves others and habits usable. History is retained automatically, including unread items. Source/LLM calls never run inside the API request handler.

### A06 Connect sources and one LLM provider

Labels: `feature`. Milestone: M2. Dependencies: A05.

Implement the category sources in [Daily discoveries](discoveries.md), seed/fallback records, structured generation, source validation, repeat suppression, and usage accounting. Select one provider/model and set an explicit spending ceiling; record these choices in configuration and the runbook.

Acceptance: all five categories produce source-backed cards; exact titles/IDs/links come from fetched records; source failure and malformed model output fail gracefully; retry cannot bypass limits. Check current source endpoints, attribution requirements, and provider terms during implementation. Manually inspect a few cards per category and keep sanitized parsing fixtures. Confirm how the candidate pool is replenished.

### A07 Build discoveries and the Library

Labels: `feature`. Milestone: M2. Dependencies: A04, A05; A06 for live-content acceptance.

Build daily previews, category detail cards, artwork display, source links, automatic history, favorites, read state, filters, and basic search. Connect ensure/retry controls and bounded status polling.

Acceptance: all five categories render on a phone; Library finds older words, artwork, events, mind cards, and papers; a favorite can be toggled without altering the saved card. Loading, partial failures, empty history, and failed images have clear states. Ready content cannot be rerolled accidentally.

### A08 Add export and verify the full personal workflow

Labels: `quality`. Milestone: M3. Dependencies: A03, A07.

Implement a versioned JSON export, final targeted integration checks, and a small operations view or status command for generation errors, usage, and storage health. Complete setup documentation and verify the app on a phone.

Acceptance: export contains all durable domain records and provenance, and its schema is documented. Run the test strategy below, manually verify sign-in → habit → discovery → history → export, and check container recreation preserves data. No real provider credentials are needed in CI. Fix concrete accessibility and error-state issues found during this pass.

### A09 Deploy independently and enable GCP recovery

Labels: `infra`. Milestone: M3. Dependencies: A08.

Choose the host/domain and dedicated GCP project; configure HTTPS, deployment secrets, the Firebase production flow, scheduled backups, retention, and restore instructions. Keep all identities, resources, and configuration separate from Osmy.

Acceptance: only nginx is publicly reachable; the owner can use the app from a phone over HTTPS; an automatic off-host backup succeeds; restore it into an empty isolated Redis volume and verify habits, schedules, completions, discoveries, and annotations. Record the restore result and enable backup-failure visibility before regular use.

## Testing strategy

Use small tests that exercise observable behavior. Test domain rules with a fixed clock and plain fixtures; test application services with small in-memory protocol implementations. Avoid elaborate mock graphs, exact LLM prose snapshots, a numerical coverage target, or a large browser suite.

| Layer | Useful checks |
| --- | --- |
| Habit unit tests | Selected weekdays, past corrections, future rejection, tomorrow-effective edits, archive/restore, incomplete today, zero-opportunity windows, representative timezone/DST boundary |
| Content unit tests | Repeat identity normalization, supplied-source-only output, category validation, budget exhaustion, attempts including manual retries, stable published slots |
| Auth/API unit tests | Owner allowlist, rejected identity, ownership lookup, request validation and error mapping |
| Frontend component tests | Completion/undo and rollback, calendar status labels, category payload rendering, favorite/filter interaction |
| Redis integration tests | Repository round trip/idempotent completion; atomic publication/history with a shared-date page boundary; expired-job recovery |
| Thin HTTP integration check | Authenticate with a controlled test identity, create a habit, complete it, retrieve calendar/history through the real API and Redis |

Run integration checks in a Compose test profile against a separate disposable Redis volume and project name. The API check uses dependency overrides or the Firebase emulator, fake content sources, and a fake LLM; it does not contact paid providers. Keep fixtures isolated and teardown explicit so tests cannot operate on personal data.

CI should run formatting/lint checks, Python and TypeScript typechecks, unit/component tests, frontend build, and this small integration set. Keep external source smoke checks opt-in and manual because network/provider availability should not destabilize ordinary CI. Manually test mobile Google sign-in and a real generated sample before deployment.

Container recreation, an initial migration dry run, and the restore drill are release checks, not a large continuous failure-injection suite. Add regression tests when real bugs justify them.

## Deployment and operations

A small single Linux host running Docker Compose is the initial deployment shape. The hosting provider and machine size remain setup choices. Firebase handles identity; no Firebase database or managed application platform is required. GCP is the backup destination and may also host the VM if convenient.

Use immutable image versions or digests for deployments, restart policies, healthchecks, TLS renewal, and bounded log retention. Track API errors, worker heartbeat, last successful generation, Redis persistence status, disk/memory usage, and backup age. Structured logs and a simple owner-only status command/page are sufficient; do not add an observability stack initially.

Store secrets outside Git and mount them or inject them at runtime. On GCP prefer an attached identity; elsewhere use an explicit app-specific credential mechanism. Do not silently borrow the developer machine's active GCP project. Example environment files contain placeholders only.

Before a schema-changing deployment, take a recoverable snapshot, run the versioned migration, then start the new application. If rollback would require an older schema, restore the pre-migration snapshot into a separate volume and accept the documented loss of writes since that snapshot; do not blindly start old code on new records.

## Deferred GCP backups

Development can proceed with local persistent Redis only. Before regular use, add a backup Compose service or scheduled container command that produces and uploads a completed RDB snapshot to a private bucket in the dedicated project. Keeping an AOF or a volume on the same host is not an off-host backup.

Initial targets are a daily off-host snapshot, at most roughly 24 hours of data loss after complete host loss, and a restore achievable within a couple of hours using the runbook. These are design targets to verify, not guarantees. The local AOF reduces ordinary restart loss but does not improve the age of an off-host snapshot.

The backup process should:

1. Trigger or await a fresh Redis RDB snapshot and confirm successful completion through persistence status.
2. Copy the completed snapshot to staging, calculate a checksum, and record timestamp, Redis version, application schema version, and record counts.
3. Upload under a unique timestamped object name with the manifest; verify the uploaded object metadata/checksum before reporting success.
4. Retain daily snapshots for 14 days and separately marked weekly snapshots for eight weeks, with cleanup handled by a small explicit retention policy.
5. Surface failures and backup age through a simple status check; retain enough recent local staging data for troubleshooting without exhausting disk.

Use a private bucket and narrowly scoped identities. A backup writer should not need project-wide administration; grant restore access to a separate operator identity. Configure object lifecycle rules deliberately for the chosen daily/weekly prefixes. See [Cloud Storage IAM roles](https://cloud.google.com/storage/docs/access-control/iam-roles) and [object lifecycle management](https://cloud.google.com/storage/docs/lifecycle).

Restore into an empty volume using the compatible pinned Redis version and documented RDB import procedure. Ensure an old AOF cannot override the restored snapshot; validate the loaded records before enabling normal persistence and application writes. Run the app against the isolated restored store, check representative records and counts, then document cutover. Do not overwrite the live volume during a drill.

Backups include saved text, provenance, and image URLs, not permanent copies of remote artwork or papers. Preserve deployment configuration and a secure way to re-provision secrets separately; never put credentials in a user-data export or ordinary backup manifest.

## Decisions intentionally left for setup

| Decision | Default direction | Needed by |
| --- | --- | --- |
| Final app name | Ataraxia as the working name | Visual polish or deployment |
| LLM provider/model and currency budget | One low-cost structured-output model, bounded calls/tokens | A06 live integration |
| Owner UID, time zone, Firebase project | Dedicated project; browser-suggested time zone confirmed in app | A02 live sign-in |
| Host, domain, TLS provisioning | One Compose host | A09 |
| Backup project, bucket, identity | Dedicated GCP resources independent of Osmy | A09, before regular use |
| More intensive game mechanics | Supportive milestones first | Review after actual use |

## Follow-up ideas

The first candidates for later issues are flexible weekly targets, an optional weekly reflection, and active recall of saved words or concepts. A garden/constellation that grows with cumulative completions could make progress tangible without penalizing missed days. A small calendar heatmap can complement the required completion circles after enough history exists. Treat these as experiments driven by personal usefulness, not prerequisites for the initial release.
