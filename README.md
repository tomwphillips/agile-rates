# agile-rates

An experiment with [jq.py](https://github.com/mwilliamson/jq.py), [Datasette](https://datasette.io/) and [Observable](https://observablehq.com/) to get Octopus Energy's Agile electricity prices.

On [Agile Octopus](https://octopus.energy/agile/) electricity prices change every half hour.
Every day around 5 pm, Octopus publish the prices for the following day.
This scrapes those prices and stores them in a SQLite database, which you can [query using Datasette](https://agile.tomwphillips.co.uk/).
Datasette provides a quick and easy API, which [Observable queries to generate plots](https://observablehq.com/@tomwphillips/octopus-agile-rates).

Agile is interesting for lots of reasons. But simply I think most people can save money by switching and making minor changes to their habits. [Money Saving Expert explains in more detail](https://www.moneysavingexpert.com/news/2023/02/wholesale-energy-prices-are-falling---is-it-worth-switching-to-o/).

[Sign up with my referral link](https://share.octopus.energy/tan-tiger-133) and we both get £50 credit.

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
