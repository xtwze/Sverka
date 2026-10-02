# syntax=docker/dockerfile:1
FROM fullstack-onec-linux-base:local
ARG INSTALLER=setup-training-8.3.27.1508-x86_64.run
ARG INSTALLER_SHA256=c3f0bbe662f2ac66cf329685b25fc3e73cc8ddcfa85ef47dd2319c9b8396b4d1
RUN --mount=type=bind,from=onecdist,target=/distribution,readonly \
    cp "/distribution/${INSTALLER}" /tmp/setup.run \
    && echo "${INSTALLER_SHA256}  /tmp/setup.run" | sha256sum -c - \
    && chmod +x /tmp/setup.run \
    && /tmp/setup.run --mode unattended --enable-components client_full,ws,ru \
        --disable-components v8_install_deps,desktop_icons \
    && rm /tmp/setup.run

# Подтверждено ldd установленного 1cv8t; зависимости webkit подтягивают libsoup/JSC.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libwebkit2gtk-4.0-37 libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*
