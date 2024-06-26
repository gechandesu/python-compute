SRCDIR = compute
DISTDIR = dist
DOCS_SRCDIR = docs/source
DOCS_BUILDDIR = docs/build

.PHONY: docs

all: build debian archlinux

requirements.txt:
	poetry export -f requirements.txt -o requirements.txt

build: version format lint
	poetry build

debian:
	cd packaging/debian && $(MAKE)

archlinux:
	cd packaging/archlinux && $(MAKE)

version:
	VERSION=$$(awk '/^version/{print $$3}' pyproject.toml); \
		sed "s/__version__ =.*/__version__ = $$VERSION/" -i $(SRCDIR)/__init__.py; \
		sed "s/release =.*/release = $$VERSION/" -i $(DOCS_SRCDIR)/conf.py

format:
	poetry run isort $(SRCDIR)
	poetry run ruff format $(SRCDIR)

lint:
	poetry run ruff check $(SRCDIR)

docs:
	poetry run sphinx-build $(DOCS_SRCDIR) $(DOCS_BUILDDIR)

docs-versions:
	poetry run sphinx-multiversion $(DOCS_SRCDIR) $(DOCS_BUILDDIR)

serve-docs:
	poetry run sphinx-autobuild $(DOCS_SRCDIR) $(DOCS_BUILDDIR) \
		--pre-build 'make clean'

clean:
	[ -d $(DISTDIR) ] && rm -rf $(DISTDIR) || true
	[ -d $(DOCS_BUILDDIR) ] && rm -rf $(DOCS_BUILDDIR) || true
	find . -type d -name __pycache__ -exec rm -rf {} \; > /dev/null 2>&1 || true
	cd packaging/debian && $(MAKE) clean
	cd packaging/archlinux && $(MAKE) clean

test-build: build debian
	scp packaging/debian/build/compute*.deb vm:~

upload-docs:
	ssh root@hitomi 'rm -rf /srv/http/nixhacks.net/hstack/compute/*'
	scp -r $(DOCS_BUILDDIR)/* root@hitomi:/srv/http/nixhacks.net/hstack/compute/
