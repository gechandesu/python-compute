FROM debian:bookworm-slim
WORKDIR /mnt/build
RUN apt-get update; \
    env DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        build-essential \
        bash-completion \
        debhelper \
        quilt \
        dh-make \
        dh-python \
        pybuild-plugin-pyproject \
        python3-poetry-core \
        python3-all \
        python3-setuptools \
        python3-sphinx \
        python3-sphinx-multiversion \
        python3-libvirt \
        python3-lxml \
        python3-yaml \
        python3-pydantic; \
    apt clean; \
    echo "alias ll='ls -alFh'" >> /etc/bash.bashrc
USER 1000:1000
