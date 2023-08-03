# syntax=docker/dockerfile-upstream:master-labs

ARG BUILDER_IMAGE=quay.io/vexxhost/openstack-builder-focal
ARG RUNTIME_IMAGE=quay.io/vexxhost/openstack-runtime-focal

# hadolint ignore=DL3007
FROM quay.io/vexxhost/bindep-loci:latest AS bindep

FROM ${BUILDER_IMAGE}:ced4522d9a10ba7172f373289af6dace06be3b36 AS builder
COPY --from=bindep --link /runtime-pip-packages /runtime-pip-packages

FROM ${RUNTIME_IMAGE}:a391e31bb33041611e2aa2797debcb21e6f221cd AS runtime
COPY --from=bindep --link /runtime-dist-packages /runtime-dist-packages
COPY --from=builder --link /var/lib/openstack /var/lib/openstack
# hadolint ignore=DL3022
COPY --from=docker.io/alpine/helm:3.11.2 /usr/bin/helm /usr/local/bin/helm
# hadolint ignore=DL3022
COPY --from=gcr.io/go-containerregistry/crane /ko-app/crane /usr/local/bin/crane
