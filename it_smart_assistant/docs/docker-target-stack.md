# Docker Target Stack

Stack development target for the current project:

- `db`: `pgvector/pgvector:pg16`
- `redis`: `redis:7-alpine`
- `minio`: object storage for uploaded documents and generated artifacts
- `minio-init`: creates the required bucket on startup
- `app`: FastAPI backend
- `worker`: background worker scaffold for future ingest/OCR/export jobs

## Why `pgvector/pgvector`

The project roadmap now targets semantic retrieval and long-term knowledge storage.
Using `pgvector/pgvector:pg16` avoids a later database migration just to add the
`vector` extension.

## Services and ports

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `localhost:9000`
- MinIO Console: `localhost:9001`
- Backend API: `localhost:8000`

## First run

From the project root:

```powershell
docker compose up -d --build
```

Run database migrations after the stack is up:

```powershell
docker compose exec app alembic upgrade head
```

Check container status:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs -f db redis minio minio-init app worker
```

## Important note if you already created the old PostgreSQL volume

The `01-enable-pgvector.sql` init script only runs when PostgreSQL initializes a
fresh data directory.

If you previously started the project with `postgres:16-alpine`, then after
switching to `pgvector/pgvector:pg16` you should either:

1. recreate the database volume, or
2. connect to PostgreSQL manually and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

To recreate the volume in local development:

```powershell
docker compose down -v
docker compose up -d --build
```

Only do this if you are okay losing local database data.

## Avoiding conflicts with existing Docker images and containers

Existing images on your machine do not cause conflicts by themselves. The real
conflicts usually come from:

- another container already using port `5432`
- another container already using port `6379`
- another container already using port `9000` or `9001`
- reusing an old PostgreSQL volume created before switching to `pgvector`

Safe rules:

- keeping old images is fine
- do not run two PostgreSQL containers on the same published port
- do not run two Redis containers on the same published port
- if you already have an old local project container, stop or remove that old container first

Useful checks:

```powershell
docker ps
docker compose ps
```

If needed, stop only the old conflicting containers manually before bringing this
stack up.

## MinIO defaults in compose

Compose defaults:

- access key: `minioadmin`
- secret key: `minioadmin`
- bucket: `it-smart-assistant`
- Redis local dev password: empty

You can override them with shell env vars before running `docker compose up`.

## Current worker scope

The worker container is a prepared background process, not a full queue system yet.
Right now it:

- verifies Redis connectivity
- prepares knowledge/admin/upload directories
- stays alive as the future home for async jobs

Next infrastructure step after this stack is to move ingest/OCR/export work from
the API process into the worker.
