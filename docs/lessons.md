# Ataraxia lessons

How lessons are requested, prepared, stored, and recorded. Product rules are in
[product](product.md); tables and endpoints in [architecture](architecture.md).

## Requests and jobs

Every lesson starts as a row in `generation_jobs`:

| Kind | Created by | Brief |
| --- | --- | --- |
| `daily` | Worker at the morning hour, or `POST /today/lesson` | Weighted subject choice; Claude picks the topic |
| `surprise` | "Surprise me" | Same as daily, not tied to the day's slot |
| `subject` | Choosing a subject | That subject; Claude picks the topic |
| `topic` | "Ask for any topic" | The owner's words (up to 300 characters); Claude picks the subject from the catalog |
| `follow_up` | "Go deeper" on a lesson | Parent lesson, plus a suggested direction or the owner's question (up to 500 characters) |

The API only inserts jobs. It refuses a new job (429) when today's calls have reached
`ATARAXIA_MAX_LESSONS_PER_DAY` (default 8) or three jobs are already waiting. There is
at most one `daily` job per local date (unique index), so a repeated ensure request is
harmless.

The worker is one process running a simple loop every few seconds:

1. On start, return interrupted `running` jobs to `queued` if they have an attempt
   left, otherwise mark them `failed` with `interrupted`.
2. If the morning lesson is enabled, the local hour has passed, and today has no daily
   job, insert one. Days when the host was off are not caught up.
3. Take the oldest queued job whose next attempt time has passed. Check the daily cap
   (today's calls, not counting ones refused for login or usage limits), insert a
   `generation_calls` row, and only then call Claude.
4. Validate the result, look up illustrations, and publish the lesson, its state row,
   the job result, and a `lesson.prepared` event in one transaction.
5. Write a heartbeat to `worker_status` every loop.

Only one worker may run. A crash during a call can waste one call; the calls table
still counts it.

### Attempts and errors

A job gets at most two attempts. The error code decides what happens next:

| Code | Meaning | Next |
| --- | --- | --- |
| `claude_auth` | The CLI is not logged in or the login expired | Fail now; the UI shows the login command |
| `claude_usage_limit` | The subscription's session or weekly limit | Stay queued without using an attempt; try again every 30 minutes; fail 24 hours after the request |
| `claude_timeout` | No result within `ATARAXIA_CLAUDE_TIMEOUT_SECONDS` (default 600) | Retry once after 30 seconds |
| `invalid_output` | No structured output, or it failed validation | Retry once |
| `claude_error` | Any other CLI failure | Retry once after 30 seconds |
| `daily_limit` | The cap was reached before the call | Fail; no call made |
| `interrupted` | Worker stopped during the last attempt | See step 1 |

Errors are classified from the CLI's JSON result: `is_error`, `api_error_status`
(401/403 for login, 429 for limits), and loose matches on the documented messages
("Not logged in", "Login expired", "Failed to authenticate", "hit your … limit"). A failed job can be retried from
the UI; a retry gives it two new attempts, and every call still counts toward the
daily cap.

## Choosing the subject and topic

For `daily` and `surprise`, the domain function `choose_subject` takes the enabled
subjects, the subjects of recent lessons, and ratings from the last 60 days, and an
injected random generator:

- weight 1.0 per enabled subject;
- multiplied by `1 + 0.25 × (likes − dislikes)` for that subject, clamped to 0.4–2.0;
- multiplied by 0.15 if the subject was used by either of the last two lessons.

Claude receives the chosen subject, up to 40 recent titles in that subject and 15
across all subjects (so it does not repeat a topic), and up to 8 recently liked and
8 disliked titles as taste hints. For a `topic` request it also receives the subject
catalog and must return a subject ID from it.

## Calling Claude

The worker runs the Claude Code CLI as a subprocess. Verified against version
2.1.332 on 24 November 2026; the worker image pins the native installer's version.

```text
claude -p --safe-mode --tools "" --strict-mcp-config --no-session-persistence
       --max-turns 3 --model <ATARAXIA_CLAUDE_MODEL>
       --system-prompt-file <prompt file> --output-format json
       --json-schema <lesson schema>          (prompt on standard input)
```

- `--safe-mode` skips CLAUDE.md files, skills, plugins, hooks, MCP servers, and
  memory; `--tools ""` removes every built-in tool. Structured output still works
  (Claude Code returns it through its own internal tool, which is why `--max-turns`
  is 3 rather than 1).
- The process runs in a fresh empty temporary directory with an explicit
  environment: `PATH`, `HOME`, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN` when
  set, `DISABLE_UPDATES=1`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`. API-key
  variables are never passed, so the subscription is always what pays.
- The worker enforces its own wall-clock timeout and terminates the process group.
- The JSON result's `structured_output` is validated with Pydantic (field lengths,
  counts, subject ID). `usage`, `total_cost_usd` (an estimate; not a bill on a
  subscription), model, and duration go to `generation_calls`.
  `credential_expires_at` is stored in `worker_status` so the app can warn before
  the login ends.

The default model is `opus`; quality matters more than speed for a daily read. The
system prompt lives in `backend/src/ataraxia/adapters/prompts/` with a version
string stored on every lesson.

### Logging in

The worker reads its login from the `claude-config` volume (`CLAUDE_CONFIG_DIR`), or
from `CLAUDE_CODE_OAUTH_TOKEN` in `.env` when that is set. Either:

- `docker compose exec -it worker claude auth login`, open the printed URL in any
  browser, and paste the code back; or
- run `claude setup-token` on a computer with a browser (it prints a one-year token)
  and put it in `.env` as `CLAUDE_CODE_OAUTH_TOKEN`, then recreate the worker.

`docker compose exec worker claude auth status` shows the current state.

## Lesson content

The schema Claude must satisfy (limits enforced again after the call):

| Field | Rule |
| --- | --- |
| `subject` | Catalog ID; must equal the requested subject unless the request was `topic` |
| `title` | 3–120 characters |
| `hook` | 20–320 characters, one or two sentences |
| `reading_minutes` | 2–30, Claude's estimate at about 230 words a minute |
| `body_markdown` | 600–40,000 characters; `##`/`###` headings, lists, tables, block quotes, inline and display math (`$…$`, `$$…$$`), fenced code; no HTML, images, or links |
| `key_ideas` | 3–5 items, each up to 240 characters |
| `glossary` | 0–12 terms with definitions up to 300 characters |
| `go_deeper` | Exactly 3, each a title (up to 80) and a one-sentence description (up to 240) |
| `further` | 0–5 items: title, optional creator, kind (book, film, artwork, music, place, article, other), optional note |
| `illustrations` | 0–3 English Wikipedia article titles with a caption, only where an image helps |
| `tags` | 1–6 short tags |

Length targets by setting, at about 230 words a minute: short 1,000–1,300 words
(about 5 minutes), standard 2,300–3,200 (10–15 minutes), long 4,000–5,000 (about 20).

The system prompt asks for writing for one curious, intelligent adult who is not a
specialist: a concrete opening rather than a definition, a clear line of argument,
specific names, dates, and examples, no filler or motivational talk, and honesty
about uncertainty. Each subject adds guidance: Film avoids late spoilers unless
warned; Words teaches a themed set of 5–8 useful words with pronunciation, origin,
and natural example sentences; Mathematics builds intuition before notation and
includes a worked example; Computer science includes a small code or pseudo-code
example when it helps; History separates documented fact from interpretation;
Science says what kind of evidence supports a claim.

### Illustrations

For each requested title the worker asks Wikipedia's Action API (`action=query`,
`prop=pageimages|info`, `pilicense=any`, `redirects=1`, thumbnail width 1280) over
HTTPS with a descriptive User-Agent, a 5-second timeout, and a small response limit.
`pilicense=any` includes the non-free lead images Wikipedia itself shows (film
posters, modern artworks); this private app displays them the same way. Only image
URLs on `upload.wikimedia.org` are kept, with the article's canonical URL as the
source link. Titles that do not resolve are dropped; a lesson without images is fine.
Wikipedia lookups never delay publication by more than about 15 seconds in total.

## Recording activity

Server-side changes write their event in the same transaction as the change.

| Event | Written when | Payload |
| --- | --- | --- |
| `app.opened` | Client reports a fresh app load | — |
| `lesson.requested` | A job is created | kind, subject, topic or question, parent |
| `lesson.prepared` | A lesson is published | job kind, model, reading minutes |
| `lesson.failed` | A job fails for good | error code |
| `lesson.opened` | The reader is opened | — |
| `lesson.finished` / `lesson.unfinished` | Finished is set or cleared | — |
| `lesson.saved` / `lesson.unsaved` | Saved is set or cleared | — |
| `lesson.rated` | Rating changes | rating −1, 0, or 1 |
| `lesson.flagged` | A problem is reported | note (up to 500 characters) |
| `settings.updated` | Settings change | changed field names and new values |

Repeating a state change with the same value writes no event.

Reading time is recorded as sessions rather than events. Opening the reader starts a
session with a random ID; while the page is visible the client sends the session's
cumulative seconds and furthest scroll every 30 seconds, and again when the page is
hidden. The server upserts the `reading_sessions` row (lesson, session ID, start time,
local date, seconds, furthest scroll), keeping the larger values, so a repeated, late,
or lost report costs at most 30 seconds and never double-counts.
`lesson_state.read_seconds` is the sum of a lesson's sessions.

## Using the record later

- `GET /api/v1/export` or `docker compose exec api python -m ataraxia.tools export`
  writes the complete versioned JSON.
- `docker compose exec api python -m ataraxia.tools stats` prints totals by subject
  and recent days.
- The SQLite file can be queried directly with
  `docker compose exec api python -m sqlite3 /data/ataraxia.db`.
- `docker compose exec api python -m ataraxia.tools backup /data/backups/<name>.db`
  writes a consistent copy with SQLite's online backup.

This is how a Claude session reads the data: in a terminal on the machine running
the app (over SSH for the VM), not through the browser-authenticated API. These are
the inputs for recaps, tuning subject weights or prompts, and quizzes.
