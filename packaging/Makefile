DOCKER_CMD ?= docker
DOCKER_IMG = pybuilder:bookworm
DEBBUILDDIR = build

all: docker-build build

clean:
	test -d $(DEBBUILDDIR) && rm -rf $(DEBBUILDDIR) || true

docker-build:
	$(DOCKER_CMD) build -f Dockerfile -t $(DOCKER_IMG) .

build: clean
	mkdir -p $(DEBBUILDDIR)
	cp -v ../dist/compute-*[.tar.gz] $(DEBBUILDDIR)/
	cp -r ../docs $(DEBBUILDDIR)/
	if [ -f build.sh.bak ]; then mv build.sh{.bak,}; fi
	cp build.sh{,.bak}
	awk '/authors/{gsub(/[\[\]]/,"");print $$3" "$$4}' ../pyproject.toml \
		| sed "s/['<>]//g" \
		| tr ' ' '\n' \
		| xargs -I {} sed "0,/%placeholder%/s//{}/" -i build.sh
	$(DOCKER_CMD) run --rm -i -v $$PWD:/mnt $(DOCKER_IMG) bash < build.sh
	mv build.sh{.bak,}
