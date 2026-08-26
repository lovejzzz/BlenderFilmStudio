FROM --platform=linux/amd64 debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ARG BLENDER_ARCHIVE=blender-5.2.0-linux-x64.tar.xz
ARG BLENDER_ARCHIVE_SHA256=96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48
ARG BLENDER_EXECUTABLE_SHA256=60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates xz-utils \
      libasound2 libdbus-1-3 libegl1 libfontconfig1 libfreetype6 libgl1 libgl1-mesa-dri \
      libglib2.0-0 libice6 libpulse0 libsm6 libwayland-client0 libx11-6 libxext6 \
      libxfixes3 libxi6 libxkbcommon0 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY ${BLENDER_ARCHIVE} /tmp/${BLENDER_ARCHIVE}

RUN echo "${BLENDER_ARCHIVE_SHA256}  /tmp/${BLENDER_ARCHIVE}" | sha256sum --check --strict \
    && mkdir -p /opt/bfs/blender \
    && tar --extract --xz --file "/tmp/${BLENDER_ARCHIVE}" --strip-components=1 --directory /opt/bfs/blender \
    && echo "${BLENDER_EXECUTABLE_SHA256}  /opt/bfs/blender/blender" | sha256sum --check --strict \
    && /opt/bfs/blender/blender --version | head -n 1 | grep -Fx 'Blender 5.2.0 LTS' \
    && rm -f "/tmp/${BLENDER_ARCHIVE}" \
    && printf 'bfs:x:65532:65532:Blender Film Studio:/work/home:/usr/sbin/nologin\n' >> /etc/passwd \
    && printf 'bfs:x:65532:\n' >> /etc/group

ENTRYPOINT ["/opt/bfs/blender/blender"]
