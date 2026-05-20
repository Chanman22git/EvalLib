# EvalLib — developer entrypoints. `make setup && make run` → working stack.
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help setup run up down logs ps build seed demo reset test test-governance test-orchestrator fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

setup: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — edit it if you want real LLM calls.")
	@mkdir -p otel-collector/output
	@echo "Setup complete."

run: up ## Alias for `up`

up: setup ## Build images and start the full stack
	$(COMPOSE) up --build -d
	@echo "Stack starting. UI(once built):3000  Phoenix:6006  Governance:8001/docs  Orchestrator:8002/docs"

build: setup ## Build all images without starting
	$(COMPOSE) build

down: ## Stop the stack (keep volumes)
	$(COMPOSE) down

reset: ## Stop the stack and delete all data volumes
	$(COMPOSE) down -v
	@rm -f otel-collector/output/*.jsonl 2>/dev/null || true
	@echo "Stack reset (volumes + collector output cleared)."

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

seed: ## Populate the Governance Store with demo data
	$(COMPOSE) run --rm seed python seed_data.py

demo: ## Run the end-to-end demo
	./scripts/demo.sh

test: test-governance test-orchestrator ## Run all backend test suites

test-governance: ## Run governance-api tests
	$(COMPOSE) run --rm governance-api pytest -q

test-orchestrator: ## Run eval-orchestrator tests
	$(COMPOSE) run --rm eval-orchestrator pytest -q
