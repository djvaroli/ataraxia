# Ataraxia

Ataraxia is a private learning app: one Claude-written lesson a day on art, history,
film, words, geography and geopolitics, science, mathematics, computer science, and
more. Lessons start as a 10–15 minute read and can be saved, rated, and continued
into deeper follow-ups. Every action is recorded so the history can be reviewed,
summarized, and used to tune what comes next.

The app runs in Docker on one machine, uses the owner's Claude subscription through
the Claude Code CLI, and is reached from a phone over a private network with Firebase
sign-in. It is an independent project, entirely separate from Osmy.

Status, 24 November 2026: the runnable shell from A01 is merged; the lessons plan
(L01) is in review and L02–L06 follow. See the [roadmap](docs/roadmap.md).
Contributors and coding agents follow [AGENTS.md](AGENTS.md) and the
[agent delivery loop](docs/agent-workflow.md).

## Run locally

With Docker Engine and Docker Compose v2.20+ installed, run from this directory:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait
```

Open [localhost:8080](http://localhost:8080). nginx is the only published service and binds to loopback. Source edits reload the frontend and API; restart the worker after editing it. No environment file or credentials are needed for this foundation. Copy `.env.example` to `.env` if you need to change the port.

```sh
curl --fail http://localhost:8080/api/health/ready
docker compose down
```

Stopping the stack retains Redis data. See [Local development](docs/development.md) for compiled builds, logs, configuration, and storage details.

## Validate

These commands use the locked dependencies and pinned container runtimes. Checks do not require Firebase or an LLM provider:

```sh
bash scripts/check
python3 scripts/smoke.py
```

The first runs formatting, lint, Python/TypeScript typechecks, tests, the frontend build, and generated API contract checks. The second checks real nginx routing, private service ports, Redis persistence, and failure recovery in its own disposable Compose project. Both remove only their temporary containers and volumes. CI runs the same commands.

## Design documents

| Document | Purpose |
| --- | --- |
| [Product and experience](docs/product.md) | The lesson loop, screens, activity record, look and feel, limits |
| [Lessons](docs/lessons.md) | Jobs, subject choice, calling Claude, content rules, events |
| [Architecture and data](docs/architecture.md) | Services, storage, API, authentication, security |
| [Deployment](docs/deployment.md) | VM, private network, hardening, backups |
| [Delivery](docs/delivery.md) | Acceptance per roadmap item and the test strategy |

Read the product document first.

## Session skills

Use [$ataraxia-handoff](.agents/skills/ataraxia-handoff/SKILL.md) to save a
checkpoint, and [$ataraxia-resume](.agents/skills/ataraxia-resume/SKILL.md) to verify
it and continue in a fresh session. [Session continuity](docs/session-continuity.md)
defines the shared record format. The current checkpoint in [.HANDOFF.md](.HANDOFF.md)
and history in [.handoff/](.handoff/) are tracked in Git and travel with the branch
once committed. Temporary handoff drafts (`*.tmp`) remain ignored.
