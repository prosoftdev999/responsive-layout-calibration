FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash jq ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 agent \
    && useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash agent

RUN mkdir -p /app/output /workspace \
    && chown agent:agent /app/output /workspace

COPY data/ /app/data/
COPY --chown=agent:agent calibrate_layout.py /workspace/calibrate_layout.py

WORKDIR /workspace
USER agent
