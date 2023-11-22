SRCDIR = compute
DISTDIR = dist
DOCS_SRCDIR = docs/source
DOCS_BUILDDIR = docs/build

.PHONY: docs

all: build

requirements.txt:
	poetry export -f requirements.txt -o requirements.txt

build: format lint
	awk '/^version/{print $$3}' pyproject.toml \
		| xargs -I {} sed "s/__version__ =.*/__version__ = '{}'/" -i $(SRCDIR)/__init__.py
	poetry build

build-deb: build
	cd packaging && $(MAKE)

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
	poetry run sphinx-autobuild $(DOCS_SRCDIR) $(DOCS_BUILDDIR)

clean:
	[ -d $(DISTDIR) ] && rm -rf $(DISTDIR) || true
	[ -d $(DOCS_BUILDDIR) ] && rm -rf $(DOCS_BUILDDIR) || true
	find . -type d -name __pycache__ -exec rm -rf {} \; > /dev/null 2>&1 || true
	cd packaging && $(MAKE) clean

test-build: build-deb
	scp packaging/build/compute*.deb vm:~
