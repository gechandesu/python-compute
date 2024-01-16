DOCKER_CMD ?= docker
DOCKER_IMG = computebuilder:debian-bookworm
BUILDDIR = build
KEEP_BUILDFILES ?=

all: docker-build build

clean:
	test -d $(BUILDDIR) && rm -rf $(BUILDDIR) || true

docker-build:
	$(DOCKER_CMD) build -f Dockerfile -t $(DOCKER_IMG) .

build: clean
	mkdir -p $(BUILDDIR)
	cp -v ../../dist/compute-*[.tar.gz] $(BUILDDIR)/
	cp -r ../../docs $(BUILDDIR)/
	cp ../../extra/completion.bash $(BUILDDIR)/compute.bash-completion
	if [ -f build.sh.bak ]; then mv build.sh{.bak,}; fi
	cp build.sh{,.bak}
	awk '/authors/{gsub(/[\[\]]/,"");print $$3" "$$4}' ../pyproject.toml \
		| sed "s/['<>]//g" \
		| tr ' ' '\n' \
		| xargs -I {} sed "0,/%placeholder%/s//{}/" -i build.sh
	$(DOCKER_CMD) run --rm -i -v $$PWD:/mnt $(DOCKER_IMG) bash < build.sh
	mv build.sh{.bak,}
	# Remove unwanted files from build dir
	find $(BUILDDIR) -mindepth 1 -type d -exec rm -rf {} +
	[ -z $(KEEP_BUILDFILES) ] && find $(BUILDDIR) ! -name '*.deb' -type f -exec rm -f {} + || true
