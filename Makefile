# edgekpi: one KPI definition, three backends, and a React demo.
#
#   make            show this help
#   make demo       install what is missing, start the service and the demo, open nothing until you ask (OPEN=1)
#   make tf-plan    plan the Cloud Run demo (deploy happens by merging to main)
#
# Works with GNU Make 3.81 (the one macOS ships). Set NO_COLOR=1 for plain output.

SHELL        := /bin/bash
.DEFAULT_GOAL := help

VENV         ?= .venv
PY           := $(VENV)/bin/python
API_PORT     ?= 8765
WEB_PORT     ?= 5173
OPEN         ?= 0
WEB          := demo/web
MALLOY       := edgekpi/backends/malloy_runtime

PY_STAMP     := $(VENV)/.edgekpi-installed
MALLOY_STAMP := $(MALLOY)/node_modules/.installed
WEB_STAMP    := $(WEB)/node_modules/.installed

ifdef NO_COLOR
  B :=
  D :=
  G :=
  Y :=
  R :=
  C :=
  X :=
else
  B := $(shell printf '\033[1m')
  D := $(shell printf '\033[2m')
  G := $(shell printf '\033[32m')
  Y := $(shell printf '\033[33m')
  R := $(shell printf '\033[31m')
  C := $(shell printf '\033[36m')
  X := $(shell printf '\033[0m')
endif

.PHONY: help doctor install install-python install-malloy install-web \
        demo api web open example test test-py test-web e2e check mutation evidence docs \
        stop clean distclean deploy deploy-url deploy-logs deploy-delete tf-plan

# ---- help --------------------------------------------------------------------------------------------------------

help: ## Show this help
	@printf '\n$(B)edgekpi$(X)  one KPI definition, three backends\n\n'
	@printf '$(B)Start here$(X)\n'
	@printf '  $(C)make install$(X)    install everything the demo and the tests need\n'
	@printf '  $(C)make demo$(X)       start the service and the demo  $(D)(http://localhost:$(WEB_PORT))$(X)\n\n'
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  $(C)%-16s$(X) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@printf '\n$(B)Options$(X)  $(D)(make demo API_PORT=9000 WEB_PORT=3000 OPEN=1)$(X)\n'
	@printf '  API_PORT=$(API_PORT)   WEB_PORT=$(WEB_PORT)   OPEN=$(OPEN)   VENV=$(VENV)\n'
	@printf '  PROJECT=$(PROJECT)   REGION=$(REGION)   SERVICE=$(SERVICE)\n\n'

# ---- prerequisites -----------------------------------------------------------------------------------------------

doctor: ## Check the tools this project needs, and say how to get each one
	@fail=0; \
	ok()   { printf '  $(G)✓$(X) %-14s %s\n' "$$1" "$$2"; }; \
	warn() { printf '  $(Y)!$(X) %-14s %s\n' "$$1" "$$2"; }; \
	bad()  { printf '  $(R)✗$(X) %-14s %s\n' "$$1" "$$2"; fail=1; }; \
	printf '\n$(B)Prerequisites$(X)\n'; \
	if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then \
	  ok python3 "$$(python3 --version 2>&1)"; \
	else bad python3 "needs 3.10 or newer: https://www.python.org/downloads/ or 'brew install python'"; fi; \
	if command -v node >/dev/null 2>&1 && [ "$$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; then \
	  ok node "$$(node --version)"; \
	else bad node "needs 18 or newer: https://nodejs.org/ or 'brew install node'"; fi; \
	if command -v npm >/dev/null 2>&1; then ok npm "$$(npm --version)"; else bad npm "comes with node"; fi; \
	if command -v curl >/dev/null 2>&1; then ok curl "$$(curl --version | head -1 | cut -d' ' -f1-2)"; else bad curl "needed to wait for the service"; fi; \
	if command -v uv >/dev/null 2>&1; then ok uv "$$(uv --version) (faster installs)"; else warn uv "optional: 'brew install uv' or pip; falls back to python -m venv"; fi; \
	if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then \
	  ok chrome "found (browser tests)"; \
	else warn chrome "only needed for 'make e2e': https://www.google.com/chrome/"; fi; \
	for p in $(API_PORT) $(WEB_PORT); do \
	  if python3 -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1', $$p)) else 1)"; then ok "port $$p" "free"; \
	  else warn "port $$p" "in use: 'make stop' or choose another with API_PORT= / WEB_PORT="; fi; \
	done; \
	printf '\n'; \
	if [ $$fail -ne 0 ]; then printf '$(R)Install the missing tools above, then run make install.$(X)\n\n'; exit 1; \
	else printf '$(G)Ready. Next: make install, then make demo.$(X)\n\n'; fi

# ---- install (each step is skipped when it is already up to date) ------------------------------------------------

install: install-python install-malloy install-web ## Install the Python package, the Malloy runtime and the demo
	@printf '\n$(G)$(B)Installed.$(X)  Start the demo with $(C)make demo$(X)\n\n'

install-python: $(PY_STAMP) ## Create .venv and install the library with its dev tools
$(PY_STAMP): pyproject.toml
	@command -v python3 >/dev/null 2>&1 || { printf '$(R)python3 not found. Run make doctor.$(X)\n'; exit 1; }
	@printf '$(B)[1/3] Python$(X)  creating $(VENV) and installing edgekpi\n'
	@if command -v uv >/dev/null 2>&1; then \
	  [ -x $(PY) ] || uv venv $(VENV) --python 3.12 -q || uv venv $(VENV) -q; \
	  uv pip install -q --python $(PY) -e ".[dev]"; \
	else \
	  [ -x $(PY) ] || python3 -m venv $(VENV); \
	  $(PY) -m pip install -q --upgrade pip; \
	  $(PY) -m pip install -q -e ".[dev]"; \
	fi
	@touch $@
	@printf '      $(G)✓$(X) %s\n' "$$($(PY) --version)"

install-malloy: $(MALLOY_STAMP) ## Install the Malloy runtime (needed for the Malloy backend)
$(MALLOY_STAMP): $(MALLOY)/package.json
	@command -v npm >/dev/null 2>&1 || { printf '$(R)npm not found. Run make doctor.$(X)\n'; exit 1; }
	@printf '$(B)[2/3] Malloy$(X)  installing the runtime\n'
	@cd $(MALLOY) && npm install --no-audit --no-fund --loglevel=error >/dev/null
	@touch $@
	@printf '      $(G)✓$(X) @malloydata/malloy\n'

install-web: $(WEB_STAMP) ## Install the demo's npm packages
$(WEB_STAMP): $(WEB)/package.json
	@command -v npm >/dev/null 2>&1 || { printf '$(R)npm not found. Run make doctor.$(X)\n'; exit 1; }
	@printf '$(B)[3/3] Demo$(X)  installing the npm packages\n'
	@cd $(WEB) && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --no-audit --no-fund --loglevel=error >/dev/null
	@touch $@
	@printf '      $(G)✓$(X) vite, react, playwright\n'

# ---- run ---------------------------------------------------------------------------------------------------------

demo: install ## Start the service and the demo together; Ctrl-C stops both
	@python3 -c "import socket,sys; \
	[sys.exit('port %d is already in use. Run make stop, or choose another: make demo API_PORT=9000 WEB_PORT=3000' % p) \
	 for p in ($(API_PORT), $(WEB_PORT)) if socket.socket().connect_ex(('127.0.0.1', p)) == 0]"
	@printf '\n$(B)Starting the service$(X)  on http://127.0.0.1:$(API_PORT)\n'
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m edgekpi.server --port $(API_PORT) >.edgekpi-service.log 2>&1 & \
	api=$$!; \
	trap 'kill $$api 2>/dev/null; wait $$api 2>/dev/null; printf "\n$(D)stopped the service$(X)\n"' EXIT INT TERM; \
	printf '  waiting for it'; \
	for i in $$(seq 1 60); do \
	  if curl -fs http://127.0.0.1:$(API_PORT)/api/evidence >/dev/null 2>&1; then ready=1; break; fi; \
	  if ! kill -0 $$api 2>/dev/null; then break; fi; \
	  printf '.'; sleep 0.5; \
	done; \
	if [ -z "$$ready" ]; then \
	  printf ' $(R)failed$(X)\n\n$(D)--- .edgekpi-service.log ---$(X)\n'; tail -20 .edgekpi-service.log; exit 1; \
	fi; \
	printf ' $(G)ready$(X)\n\n'; \
	printf '$(B)Demo$(X)  $(C)http://localhost:$(WEB_PORT)$(X)\n'; \
	printf '$(D)  Report · Catalogue · Backends · Migration · Assistant · Edge-case lab$(X)\n'; \
	printf '$(D)  Ctrl-C stops everything. Service log: .edgekpi-service.log$(X)\n\n'; \
	if [ "$(OPEN)" = "1" ]; then (sleep 2; open http://localhost:$(WEB_PORT) 2>/dev/null || xdg-open http://localhost:$(WEB_PORT) 2>/dev/null) & fi; \
	cd $(WEB) && npm run dev --silent -- --host 127.0.0.1 --port $(WEB_PORT) --strictPort

api: install-python ## Start only the service (http://127.0.0.1:8765)
	@printf '$(B)edgekpi service$(X) on http://127.0.0.1:$(API_PORT)  $(D)(Ctrl-C to stop)$(X)\n'
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m edgekpi.server --port $(API_PORT)

web: install-web ## Start only the demo front end (needs the service: make api)
	@printf '$(B)demo$(X) on http://localhost:$(WEB_PORT)  $(D)(proxies /api to port $(API_PORT))$(X)\n'
	@cd $(WEB) && npm run dev --silent -- --host 127.0.0.1 --port $(WEB_PORT) --strictPort

open: ## Open the demo in your browser
	@open http://localhost:$(WEB_PORT) 2>/dev/null || xdg-open http://localhost:$(WEB_PORT) 2>/dev/null || printf 'Open http://localhost:$(WEB_PORT)\n'

example: install-python install-malloy ## Run the library from the command line: all backends against the reference
	@printf '$(B)Report$(X)\n'
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m edgekpi run examples/registry/model.yaml examples/registry/request-small.json \
	  --data examples/registry/data.sql | head -14
	@printf '\n$(B)Do the backends agree?$(X)\n'
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m edgekpi verify examples/registry/model.yaml examples/registry/request-pivot.json \
	  --data examples/registry/data.sql

stop: ## Stop a demo left running on the demo ports
	@for p in $(API_PORT) $(WEB_PORT); do \
	  pids=$$(lsof -ti tcp:$$p -sTCP:LISTEN 2>/dev/null); \
	  if [ -n "$$pids" ]; then kill $$pids && printf '  stopped what listened on port %s\n' $$p; else printf '  $(D)nothing on port %s$(X)\n' $$p; fi; \
	done

# ---- tests -------------------------------------------------------------------------------------------------------

test: test-py test-web ## Run the Python and the front-end unit tests (no browser, no warehouse)

test-py: install-python install-malloy ## Python tests: library, service layer, documents
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m pytest -q

test-web: install-web ## Type-check the demo and run its unit tests
	@cd $(WEB) && npx tsc --noEmit && npx vitest run

e2e: install ## Browser tests against the real service; screenshots go to specs/ux-demo/e2e/screenshots
	@cd $(WEB) && EDGEKPI_PYTHON=$(abspath $(PY)) npm run e2e --silent

check: test e2e docs ## Everything: types, unit, service, documents and browser tests
	@printf '\n$(G)$(B)All checks passed.$(X)\n\n'

docs: install-python ## Check the documents: links, citations, screenshots, edge-case coverage
	@PYTHONDONTWRITEBYTECODE=1 $(PY) -m pytest -q tests/test_docs.py tests/test_ux_demo_docs.py

mutation: install-python ## Break one rule at a time and check the tests notice (about 4 minutes)
	@$(PY) scripts/mutation_check.py

evidence: install ## Record a run on a Databricks warehouse (needs DATABRICKS_CONFIG_PROFILE and EDGEKPI_DBX_WAREHOUSE)
	@[ -n "$$DATABRICKS_CONFIG_PROFILE" ] && [ -n "$$EDGEKPI_DBX_WAREHOUSE" ] || { \
	  printf '$(R)Set DATABRICKS_CONFIG_PROFILE and EDGEKPI_DBX_WAREHOUSE first.$(X)\n'; exit 1; }
	@PYTHONDONTWRITEBYTECODE=1 $(PY) scripts/record_evidence.py --databricks

# ---- clean -------------------------------------------------------------------------------------------------------

clean: ## Remove build output, logs and test results (keeps installed packages)
	@rm -rf $(WEB)/dist $(WEB)/e2e/.results $(WEB)/test-results .edgekpi-service.log edgekpi.egg-info
	@find . -name __pycache__ -not -path './node_modules/*' -not -path './$(VENV)/*' -not -path '*/node_modules/*' -prune -exec rm -rf {} +
	@printf '$(G)✓$(X) cleaned\n'

distclean: clean ## Also remove .venv and every node_modules (make install again afterwards)
	@rm -rf $(VENV) $(WEB)/node_modules $(MALLOY)/node_modules
	@printf '$(G)✓$(X) removed .venv and node_modules\n'

# ---- deploy ------------------------------------------------------------------------------------------------------

PROJECT ?= saas-app-001
REGION  ?= us-central1
SERVICE ?= edgekpi-demo

deploy: ## Deploy happens by merging to main; GitHub Actions builds the image and applies Terraform
	@printf '$(B)Deploy$(X)  merge a pull request to $(C)main$(X).\n'
	@printf '  GitHub Actions builds the image and applies $(C)terraform/$(X).\n'
	@printf '  A local plan, without applying: $(C)make tf-plan$(X)\n\n'

tf-plan: ## Plan the demo infrastructure against the image that is already deployed
	@image=$$(gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) --format=json | python3 -c 'import json,sys; print(json.load(sys.stdin)["spec"]["template"]["spec"]["containers"][0]["image"])'); \
	terraform -chdir=terraform init -input=false && \
	terraform -chdir=terraform plan -input=false -var="image=$$image"

deploy-url: ## Print the demo's Cloud Run URL
	@gcloud run services describe $(SERVICE) --project $(PROJECT) --region $(REGION) --format='value(status.url)'

deploy-logs: ## Tail the demo's Cloud Run logs
	gcloud beta run services logs tail $(SERVICE) --project $(PROJECT) --region $(REGION)

deploy-delete: ## Refuse: Terraform owns the Cloud Run service
	@printf '$(R)The demo is managed by Terraform.$(X) Delete it with terraform destroy in terraform/, not from here.\n'
	@exit 1
