FROM archlinux:latest
WORKDIR /mnt
RUN chown 1000:1000 /mnt; \
    pacman -Sy --noconfirm \
        fakeroot \
        binutils \
        python \
        python-pip; \
    echo "alias ll='ls -alFh'" >> /etc/bash.bashrc
USER 1000:1000
