SRC = compute/
DIST = dist/
DOCS_SRC = docs/source/
DOCS_BUILD = docs/build/

.PHONY: docs

all: build

build: format lint
	poetry build

format:
	poetry run isort --lai 2 $(SRC)
	poetry run ruff format $(SRC)

lint:
	poetry run ruff check $(SRC)

docs:
	poetry run sphinx-build $(DOCS_SRC) $(DOCS_BUILD)

serve-docs:
	poetry run sphinx-autobuild $(DOCS_SRC) $(DOCS_BUILD)

clean:
	[ -d $(DIST) ] && rm -rf $(DIST) || true
	[ -d $(DOCS_BUILD) ] && rm -rf $(DOCS_BUILD) || true
	find . -type d -name __pycache__ -exec rm -rf {} \; > /dev/null 2>&1 || true

test-build:
	poetry build
	scp $(DIST)/*.tar.gz vm:~
