lint: 
	@echo "Running Linter (Ruff)..."
	poetry run isort tests/ src/ examples --check-only || poetry run isort tests/ src/ examples
	poetry run ruff check src examples --fix --unsafe-fixes --exit-zero
	poetry run ruff format src examples --check || poetry run ruff format src examples
docstring:
	ruff check --select D src/starfish/data_factory
test:
	poetry run pytest tests/	

install:
	@echo "Installing dependencies..."
	poetry install
	poetry run pre-commit install --install-hooks


