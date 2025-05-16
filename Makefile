lint: 
	@echo "Running Linter (Ruff)..."
	poetry run isort tests/ src/ examples --check-only || poetry run isort tests/ src/ examples
	poetry run ruff check src examples --fix --unsafe-fixes --exit-zero
	poetry run ruff format src examples --check || poetry run ruff format src examples
docstring:
	ruff check --select D src/starfish/data_factory
test:
	poetry run pytest tests/	

install: install-extras

#poetry install --extras "code_execution vllm" --with dev
# Install with specific extras
#make install EXTRAS="pdf"
# Install all extras
#make install EXTRAS="all"
# Install without extras (default)
#make install
install-extras:
	@echo "Installing dependencies with extras: $(EXTRAS)"
	poetry install $(if $(EXTRAS),--extras "$(EXTRAS)",) --with dev

start-client_claude:
	python src/starfish/data_mcp/client_claude.py  src/starfish/data_mcp/server.py

start-client_openai:
	python src/starfish/data_mcp/client_openai.py 