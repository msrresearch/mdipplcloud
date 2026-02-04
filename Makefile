.PHONY: test

PYTHON ?= python3
TEST_ARGS ?=

test:
	PYTHONPATH=. $(PYTHON) -m pytest $(TEST_ARGS)
