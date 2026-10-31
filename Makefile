.PHONY: setup test world rounds examples ideate guard truth clean dist

## setup: install the kernel + dev tools (zero runtime deps; dev = pytest)
setup:
	pip install -e ".[dev]"

## test: the whole suite (332 tests, ~7s)
test:
	python -m pytest tests/ -q

## world: the ten-minute organism — the tour
world:
	python experiments/minimal_world.py

## rounds: headless telemetry run (TICKS=300 OUT=runs/exp1)
rounds:
	python scripts/run_rounds.py --ticks $(or $(TICKS),300) --out $(or $(OUT),runs/exp1)

## examples: run every example keyless (mock providers where needed)
examples:
	@for d in examples/*/; do \
		echo "===== $$d ====="; \
		python "$$d/main.py" > /dev/null || exit 1; \
		echo "ok"; \
	done

## soak: the long-run invariant stress test (TICKS=10000)
soak:
	python experiments/soak.py --ticks $(or $(TICKS),10000)

## audit: run an organism and print its conservation receipt
audit:
	python -c "from experiments.minimal_world import build_world; from cognitive_ecology import ConservationAuditor; rt = build_world(7); rt.run(120); print(rt.report()); print(ConservationAuditor().verify(rt.why).summary())"

## attest: the re-attestation economics experiment (use it or lose it)
attest:
	python experiments/reattestation_economics.py

## ideate: dogfood an ideation loop (needs DEEPINFRA_API_KEY; mock otherwise)
ideate:
	python scripts/ideate.py --ask-file $(or $(ASK),scripts/../experiments/dogfood/README.md) \
		--out experiments/dogfood/latest.md

## guard: fail if anything key-shaped is in the tree
guard:
	@echo "scanning for secrets..."
	@if git grep -nE "(ghp_[A-Za-z0-9]{20,}|sk-di-[A-Za-z0-9]{20,}|apikey_[A-Za-z0-9]{20,})" -- . ':!*.md' 2>/dev/null; then \
		echo "GUARD FAILED: key-shaped string found"; exit 1; \
	else \
		echo "clean"; fi
	@if grep -rqE "(ghp_[A-Za-z0-9]{20,}|sk-di-[A-Za-z0-9]{20,}|apikey_[A-Za-z0-9]{20,})" --include="*.py" --include="*.sh" --include="*.toml" --include="*.yml" --include="*.example" . 2>/dev/null; then \
		echo "GUARD FAILED: key-shaped string found"; exit 1; \
	else \
		echo "clean (filesystem)"; fi

## clean: remove caches and run output
clean:
	rm -rf .pytest_cache **/__pycache__ src/cognitive_ecology/__pycache__ \
	       src/cognitive_ecology/agents/__pycache__ runs dist build *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

## help
help:
	@egrep "^## " $(MAKEFILE_LIST) | sed 's/^## //'

## truth: machine-check every documented count against the tree (round 18)
truth:
	python scripts/check_docs.py
