all: build

build:
	poetry build

clean:
	[ -d dist/ ] && rm -rf dist/ || true
	find . -type d -name __pycache__ -exec rm -rf {} \; > /dev/null 2>&1 || true
