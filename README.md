# agile-rates

An experiment with [jq.py](https://github.com/mwilliamson/jq.py), [Datasette](https://datasette.io/) and [Observable](https://observablehq.com/).

## Deploy

Deployed on a Digital Ocean droplet. Set up Ubuntu, install Docker and configure key-based SSH authentication.

Use SSH to connect to the Docker daemon on the droplet:

```
cd path/to/agile-rates
export DOCKER_HOST="ssh://tom@agile.tomwphillips.co.uk"
```

### Initial setup

```
docker compose pull
docker compose run --entrypoint alembic scraper upgrade head
```

Optionally, do a backfill:

```
docker compose run scraper --database-url "sqlite:///data/agile.db" backfill 2023-04-27 2023-04-28
```

Then start everything:

```
docker compose up -d
```

### Re-deploy

```
docker compose pull && docker compose up -d
```
