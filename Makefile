.PHONY: help install install-dev install-playwright test test-fast lint demo demo-full ui clean

help: ## Lista os alvos disponiveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias runtime
	pip install -r requirements.txt

install-dev: install ## Instala extras de dev (pytest, ruff)
	pip install pytest pytest-asyncio ruff

install-playwright: ## Baixa o Chromium do Playwright (scraping real)
	python -m playwright install chromium

test: ## Roda a suite pytest
	pytest

test-fast: ## Roda testes sem o slow path do pipeline demo
	pytest tests/test_normalize.py tests/test_scorer.py tests/test_ig_parser.py tests/test_ad_library_parser.py tests/test_reporter.py

lint: ## Lint com ruff
	ruff check src tests

demo: ## Roda os 3 casos de teste em modo --demo (sem rede)
	./scripts/rodar_casos_teste.sh

demo-full: ## Roda os 3 casos com scraping REAL (precisa de rede aberta)
	USAR_REDE=1 ./scripts/rodar_casos_teste.sh

ui: ## Sobe a UI Streamlit em http://localhost:8501
	PYTHONPATH=src streamlit run app/streamlit_app.py

clean: ## Remove caches e outputs runtime
	rm -rf .cache .pytest_cache outputs/runtime
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
