# Platform Productization: Milestones 15–18

Skills Agent now supports two complementary operating modes:

- local/offline dashboard with the Coordinator and local stores;
- authenticated multi-tenant REST API backed by SQLite locally or PostgreSQL
  in production.

## Architecture

```mermaid
flowchart LR
    U[User or client] --> G[Nginx gateway]
    G --> D[Dash dashboard]
    G --> A[Authenticated REST API]
    A --> J[Bounded analysis workers]
    J --> C[Coordinator]
    C --> PI[Product Intelligence]
    A --> P[(PostgreSQL)]
    C --> T[Tenant-scoped KG and Experience]
    A --> M[Health and Prometheus metrics]
```

## Milestone 15 — Analysis Quality and Dashboard UX

- fixed the Pandas `Index` boolean ambiguity in CSV/Excel query suggestions;
- deduplicated one observed anomaly detected by multiple methods while keeping
  `detection_methods` and `detection_count` provenance;
- added a full Coordinator CSV regression test;
- rendered reports as Markdown, including tables;
- added responsive Product Intelligence cards and a highlighted next action.

## Milestone 16 — Multi-user Data Foundation

`PlatformRepository` applies versioned schema migrations and stores tenants,
users, and analysis jobs. Every analysis read/update requires `tenant_id`.

Configuration:

```bash
# Offline/local default
DATABASE_URL=sqlite:///data/platform/platform.db

# Production
DATABASE_URL=postgresql://user:password@postgres:5432/skills_agent
```

In containers, prefer `DATABASE_URL_FILE` and Docker secrets. Raw uploaded rows
are used in memory by the Coordinator but are not included in persisted API
requests or results. Query history, analysis history, Knowledge Graph and
Experience paths are isolated per tenant.

SQLite backup:

```bash
python3 scripts/backup_platform.py --output-dir backups
```

PostgreSQL deployments use `pg_dump` from the secured database host.

## Milestone 17 — API, Authentication and Security

Run locally:

```bash
python3 api_server.py
```

Primary endpoints:

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/v1/auth/register` | configurable self-registration |
| POST | `/api/v1/auth/login` | public with tenant id |
| POST | `/api/v1/users` | admin |
| POST | `/api/v1/analyses` | admin, analyst |
| GET | `/api/v1/analyses` | authenticated |
| GET | `/api/v1/analyses/{id}` | authenticated, tenant-scoped |
| GET | `/health/live` | infrastructure |
| GET | `/health/ready` | infrastructure |
| GET | `/metrics` | infrastructure |

Passwords use PBKDF2-HMAC-SHA256 with a per-password random salt. Access tokens
are time-bounded and HMAC-signed. Roles are `admin`, `analyst`, and `viewer`.
Production must set a random `PLATFORM_AUTH_SECRET` of at least 32 characters
and disable self-registration.

Example:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"organization":"Acme","email":"admin@acme.test","password":"replace-this-password"}'
```

## Milestone 18 — Production Deployment

The root `Dockerfile` runs as a non-root user. `docker-compose.yml` provides:

- PostgreSQL 16 with a persistent volume;
- Gunicorn API service;
- single-process, threaded Gunicorn dashboard because dashboard state remains
  process-local;
- Nginx reverse proxy with request limits and security headers;
- readiness probes, restart policies, and internal service networking.

Setup:

```bash
cp .env.production.example .env.production
mkdir -p secrets
printf '%s' 'strong-db-password' > secrets/postgres_password.txt
printf '%s' 'postgresql://skills_agent:strong-db-password@postgres:5432/skills_agent' > secrets/database_url.txt
docker compose up --build -d
```

Terminate TLS at the ingress/load balancer or extend the supplied Nginx server
with managed certificates. Do not commit `.env.production`, `secrets/`, database
files, logs, or backups.

## Current production boundary

The API job executor is bounded but process-local. A deployment requiring
horizontal API scaling should replace it with a durable queue (for example
Celery/RQ plus Redis) before increasing Gunicorn processes. The dashboard also
keeps one process until its runtime state is moved into shared persistence.
