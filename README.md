## Deploy

```
cd path/to/agile-rates
export DOCKER_HOST="ssh://tom@agile.tomwphillips.co.uk"
```

### Initial setup

```
docker volume create agile_scraper_data
docker compose pull
docker compose run --entrypoint "alembic" scraper upgrade head
```

### Re-deploy

```
docker compose pull && docker compose up -d
```
