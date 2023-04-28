FROM python:3.11-slim-buster AS dependencies

RUN apt-get update && apt-get -y upgrade

RUN pip install pipenv
ENV PIPENV_VENV_IN_PROJECT=1

RUN useradd --create-home scraper && chown -R scraper /home/scraper
USER scraper
WORKDIR /home/scraper/src

COPY --chown=user Pipfile* .
RUN pipenv sync --keep-outdated
ENV PATH="/home/scraper/src/.venv/bin:$PATH"
ENV PYTHONPATH=.


FROM dependencies AS app

COPY --chown=scraper  . .
ENTRYPOINT ["python", "agile.py"]


FROM dependencies AS tests

RUN pipenv sync --keep-outdated --dev
ENV PYTEST_ADDOPTS="-p no:cacheprovider"
COPY --chown=user . .
CMD ["pytest"]
