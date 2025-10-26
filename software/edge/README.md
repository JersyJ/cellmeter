# Edge Service

This directory contains the code for the Edge Service, a FastAPI application designed to collect data from the Teltonika OTD500 API and other sensors, and store it locally in InfluxDB Edge.

## Development

Edge service uses `uv` for dependency management. To set up the development environment, follow these steps:

1. Ensure you have [uv](https://github.com/astral-sh/uv) installed.

2. Create a virtual environment and install dependencies:

    ```bash
    uv sync
    ```

3. Ensure you have `.env` file configured with necessary environment variables. The example `.env.example` file can be used as a template.

    ```bash
    cp .env.example .env
    ```

4. Run the FastAPI application:

    ```bash
    uv run fastapi dev
    ```

    The service will be accessible at `http://localhost:8000`.

5. To ensure that the code is formatted correctly and linted, you can install pre-commit hooks:

    ```bash
    pre-commit install
    ```

    We use `ruff` for linting and formatting. You can check and format the code using:

    ```
    ruff check
    ruff format
    ```

    and `mypy` for type checking:

    ```bash
    mypy .
    ```