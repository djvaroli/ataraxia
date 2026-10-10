# Ataraxia

Ataraxia is a personal development app for building habits and encountering something worth learning each day. Habits come first; a daily word, artwork, historical event, insight about the mind, and machine learning paper provide a small, varied reading ritual. Everything remains easy to revisit.

This is an independent project, entirely separate from Osmy. The working name comes from this repository and can change.

Status: A01 runnable foundation, 10 October 2026. The app shell, API health endpoints, idle worker, and persistent Redis run through Docker Compose. Authentication, habits, and discoveries are the next increments; no cloud resources are required yet.

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
| [Product and experience](docs/product.md) | Features, mobile screens, habit rules, motivation, and scope |
| [Architecture and data](docs/architecture.md) | Technical decisions, service boundaries, storage, authentication, and API contracts |
| [Daily discoveries](docs/discoveries.md) | Sources, LLM responsibilities, generation, history, and content quality |
| [Delivery and operations](docs/delivery.md) | Build sequence, GitHub issue drafts, tests, deployment, and backups |

Read the product document first. The other documents specify enough to begin implementation without prescribing every class or component.

## Initial decisions

- One user, mobile first, with Firebase email/password sign-in. The owner manually creates the account in Firebase; end-user sign-up is disabled and the backend accepts only the configured owner UID.
- React, TypeScript, and Vite for the frontend; FastAPI for the backend.
- Redis as the initial persistent database, with repositories separating storage from application behavior.
- nginx as the public entry point; separate frontend, API, worker, and Redis containers managed through Docker Compose.
- A small worker selects and explains source-backed discoveries through a configurable LLM provider. Published cards are saved automatically and remain stable.
- Simple unit tests and a few Docker integration checks. No distributed platform, large testing framework, or microservice split.
- GCP backups are deferred during development and required, with a successful restore, before regular personal use. The GCP project, Firebase configuration, credentials, and storage must be independent of Osmy.

These are implementation defaults unless revised. The LLM provider/model, spending ceiling, deployment host/domain, and dedicated GCP project remain setup decisions; they do not prevent building with fixtures. The initial motivation design uses supportive consistency and milestones, with heavier game mechanics left optional.

## Implementation handoff

[A01 — issue #8](https://github.com/djvaroli/ataraxia/issues/8) establishes this foundation; A02 in [Delivery and operations](docs/delivery.md) adds owner authentication and preferences next. The A-series identifiers are local backlog IDs, separate from GitHub issue numbers. Create external issues and pull requests when publication is authorized, preserving those dependencies.

When behavior or a material decision changes, update the relevant document in the same pull request. Keep routine implementation choices in code and short docstrings rather than expanding the design indefinitely.

## Session skills

Use [$ataraxia-handoff](.agents/skills/ataraxia-handoff/SKILL.md) to save a local
checkpoint, and [$ataraxia-resume](.agents/skills/ataraxia-resume/SKILL.md) to verify
it and continue in a fresh session. [Session continuity](docs/session-continuity.md)
defines the shared record format. `.HANDOFF` and `.handoff/` stay local and are
excluded from Git.
