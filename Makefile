SRC = computelib/

all: build

build:
	poetry build

clean:
	[ -d dist/ ] && rm -rf dist/ || true
	find . -type d -name __pycache__ -exec rm -rf {} \; > /dev/null 2>&1 || true

format:
	isort --lai 2 $(SRC)
	autopep8 -riva --experimental --ignore e255 $(SRC)

lint:
	pylint $(SRC)
