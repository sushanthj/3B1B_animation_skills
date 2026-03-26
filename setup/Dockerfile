## Stage 1: build manimpango (needs compiler + pango headers)
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango1.0-dev pkg-config build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

## Stage 2: runtime (no compiler, no headers)
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
        ffmpeg gifsicle \
        texlive-latex-base texlive-latex-extra texlive-fonts-recommended \
        texlive-science dvisvgm && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /manim
