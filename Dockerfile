# SPDX-FileCopyrightText: © 2025 VEXXHOST, Inc.
# SPDX-License-Identifier: GPL-3.0-or-later

FROM ghcr.io/vexxhost/openstack-venv-builder:main AS build
RUN --mount=type=bind,target=/src/staffeln,readwrite <<EOF bash -xe
uv pip install \
    --constraint /upper-constraints.txt \
        /src/staffeln
EOF

FROM ghcr.io/vexxhost/python-base:main
RUN <<EOF bash -xe
groupadd -g 42424 staffeln
useradd -u 42424 -g 42424 -M -d /var/lib/staffeln -s /usr/sbin/nologin -c "Staffeln User" staffeln
mkdir -p /etc/staffeln /var/log/staffeln /var/lib/staffeln /var/cache/staffeln
chown -Rv staffeln:staffeln /etc/staffeln /var/log/staffeln /var/lib/staffeln /var/cache/staffeln
EOF
COPY --from=build --link /var/lib/openstack /var/lib/openstack
