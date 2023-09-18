# syntax=docker/dockerfile:1.5

FROM python:3.10 AS builder
RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH
ADD . /src
RUN --mount=type=cache,target=/root/.cache \
  pip install /src

FROM python:3.10-slim AS runtime
ENV PATH=/venv/bin:$PATH
COPY --from=builder /venv /venv
