# agile-rates

Experiments with small data.

## Deploy

```
cd path/to/agile-rates
export DOCKER_HOST="ssh://tom@agile.tomwphillips.co.uk"
```

### Initial setup

```
docker compose pull
docker compose run --entrypoint alembic scraper upgrade head
```

Either wait or do a backfill:

```
docker compose run scraper --database-url "sqlite:///data/agile.db" backfill 2023-04-27 2023-04-28
```

### Re-deploy

```
docker compose pull && docker compose up -d
```
