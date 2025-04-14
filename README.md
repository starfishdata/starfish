# Starfish

A lightweight framework for working with structured LLM outputs, supporting both cloud-based and local LLM models.

## About

Starfish allows you to:
- Define structured output schemas for LLM responses
- Work with various LLM providers (OpenAI, Ollama, etc.)
- Run models locally or in the cloud

## Setup

This project uses Poetry for dependency management.

1. Install Poetry if you don't have it:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Clone the repository and install dependencies:
   ```
   git clone [repository-url]
   cd starfish
   poetry install
   ```

3. Set up environment variables:
   ```
   cp .env.template .env
   # Edit .env with your API keys and preferences
   ```


This project is licensed under the [Apache License 2.0](./LICENSE).
