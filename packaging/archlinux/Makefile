DOCKER_CMD ?= docker
DOCKER_IMG = computebuilder:archlinux
BUILDDIR = build

all: docker-build build

clean:
	test -d $(BUILDDIR) && rm -rf $(BUILDDIR) || true

docker-build:
	$(DOCKER_CMD) build -f Dockerfile -t $(DOCKER_IMG) .

build: clean
	mkdir -p $(BUILDDIR)
	VERSION=$$(awk '/^version/{print $$3}' ../../pyproject.toml | sed s'/-/\./'); \
		sed "s/pkgver=.*/pkgver=$$VERSION/" PKGBUILD > $(BUILDDIR)/PKGBUILD
	cp -v ../../dist/compute-*[.tar.gz] $(BUILDDIR)/
	cp ../../extra/completion.bash $(BUILDDIR)/
	$(DOCKER_CMD) run --rm -i -v $$PWD/$(BUILDDIR):/mnt --ulimit "nofile=1024:1048576" \
		$(DOCKER_IMG) makepkg --nodeps --clean
	# Remove unwanted files from build dir
	rm $(BUILDDIR)/compute*.tar.gz $(BUILDDIR)/PKGBUILD
