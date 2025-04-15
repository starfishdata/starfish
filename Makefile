lint: 
	@echo "Running Linter (Ruff)..."
	isort tests/ starfish/ examples
#	poetry run ruff check tests starfish examples --fix
	poetry run ruff format tests starfish examples

test:
	poetry run pytest tests/	

install:
	@echo "Installing dependencies..."
	poetry install
	poetry run pre-commit install	


