.PHONY: install test run dry-run lint format lambda-layer clean

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Install complete. Activate with: source .venv/bin/activate"

# ── Run ───────────────────────────────────────────────────────────────────────

dry-run:
	python -m src.orchestrator --dry-run

run:
	python -m src.orchestrator

# ── Test ──────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

test-coverage:
	pytest tests/ -v --cov=src --cov-report=term-missing

# ── Code Quality ──────────────────────────────────────────────────────────────

lint:
	python -m py_compile src/orchestrator.py src/**/*.py

format:
	black src/ tests/

# ── AWS Lambda Packaging ──────────────────────────────────────────────────────

lambda-layer:
	@echo "Building Lambda deployment package..."
	mkdir -p dist/python
	pip install -r requirements.txt -t dist/python
	cd dist && zip -r9 ../lambda_layer.zip python/
	@echo "✅ Lambda layer built: lambda_layer.zip"

lambda-package:
	@echo "Building Lambda function package..."
	zip -r9 lambda_function.zip src/ requirements.txt \
		--exclude "*.pyc" \
		--exclude "*/__pycache__/*" \
		--exclude "*.env"
	@echo "✅ Function package built: lambda_function.zip"

# ── Terraform ─────────────────────────────────────────────────────────────────

tf-init:
	cd infra && terraform init

tf-plan:
	cd infra && terraform plan

tf-apply:
	cd infra && terraform apply

tf-destroy:
	cd infra && terraform destroy

# ── Utilities ─────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	rm -rf dist/ lambda_layer.zip lambda_function.zip .pytest_cache/
	@echo "✅ Cleaned"
