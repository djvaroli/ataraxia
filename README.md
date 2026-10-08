# Ataraxia

Ataraxia is a personal development app for building habits and encountering something worth learning each day. Habits come first; a daily word, artwork, historical event, insight about the mind, and machine learning paper provide a small, varied reading ritual. Everything remains easy to revisit.

This is an independent project, entirely separate from Osmy. The working name comes from this repository and can change.

Status: design only, 8 October 2026. Application code, infrastructure, and cloud resources have not been created.

## Design documents

| Document | Purpose |
| --- | --- |
| [Product and experience](docs/product.md) | Features, mobile screens, habit rules, motivation, and scope |
| [Architecture and data](docs/architecture.md) | Technical decisions, service boundaries, storage, authentication, and API contracts |
| [Daily discoveries](docs/discoveries.md) | Sources, LLM responsibilities, generation, history, and content quality |
| [Delivery and operations](docs/delivery.md) | Build sequence, GitHub issue drafts, tests, deployment, and backups |

Read the product document first. The other documents specify enough to begin implementation without prescribing every class or component.

## Initial decisions

- One user, mobile first, with Firebase Google sign-in and a backend UID allowlist.
- React, TypeScript, and Vite for the frontend; FastAPI for the backend.
- Redis as the initial persistent database, with repositories separating storage from application behavior.
- nginx as the public entry point; separate frontend, API, worker, and Redis containers managed through Docker Compose.
- A small worker selects and explains source-backed discoveries through a configurable LLM provider. Published cards are saved automatically and remain stable.
- Simple unit tests and a few Docker integration checks. No distributed platform, large testing framework, or microservice split.
- GCP backups are deferred during development and required, with a successful restore, before regular personal use. The GCP project, Firebase configuration, credentials, and storage must be independent of Osmy.

These are implementation defaults unless revised. The LLM provider/model, spending ceiling, deployment host/domain, and dedicated GCP project remain setup decisions; they do not prevent building with fixtures. The initial motivation design uses supportive consistency and milestones, with heavier game mechanics left optional.

## Implementation handoff

Start with issue A01 in [Delivery and operations](docs/delivery.md). The A-series identifiers are local backlog IDs, not published GitHub issue numbers. Turn the drafts into GitHub issues when implementation begins, preserve their dependencies, and reference them from pull requests.

When behavior or a material decision changes, update the relevant document in the same pull request. Keep routine implementation choices in code and short docstrings rather than expanding the design indefinitely.
