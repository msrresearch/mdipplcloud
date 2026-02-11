.PHONY: test

PYTHON ?= python3
TEST_ARGS ?=

test:
	PYTHONPATH=. $(PYTHON) -m pytest $(TEST_ARGS)

# BEGIN MDI RELEASE TARGETS
.PHONY: release-check release-version release-bump-patch release-bump-minor release-bump-major release-tag

release-check:
	./scripts/release/release_check.sh

release-version:
	@if [ -f pyproject.toml ] && awk '/^\[project\]/{p=1;next} /^\[/{if(p) p=0} p && /^version *= *"/{print; exit}' pyproject.toml >/dev/null; then \
		awk '/^\[project\]/{p=1;next} /^\[/{if(p) p=0} p && /^version *= *"/{print; exit}' pyproject.toml; \
	elif [ -f VERSION ]; then \
		echo "version=$$(cat VERSION)"; \
	else \
		echo "No version source found"; exit 1; \
	fi

release-bump-patch:
	./scripts/release/bump_version.sh patch

release-bump-minor:
	./scripts/release/bump_version.sh minor

release-bump-major:
	./scripts/release/bump_version.sh major

release-tag:
	./scripts/release/tag_release.sh
# END MDI RELEASE TARGETS

