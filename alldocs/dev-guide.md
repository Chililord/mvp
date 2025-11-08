# Path To Freedom: Technology (The How)

"Don't create the readme for other people, you don't have other people, create it for you"

## The Tech

### Architecture Overview

The core engine behind the service will utilize the latest technologies in the areas of
Big Data and AI. Here is the orchestration:

A Dash frontend will receive a client upload in .csv format, request a signed url
from GCS, and put the .csv data at the GCS url. The data schema (column names + types) will be stored on the backend in memory for the gemini agent to utilize and produce a proper query.

The Dash frontend will receive a client query in SQL or human form and pass to the
backend where fastapi will run a Gemini powered agent to create a validated SQL query
with the schema from the user's uploaded .csv data.

The fastapi backend will store the valid SQL query in memory (no need for database) and a
GCP eventarc will grab the query and run it using bigquery when the user's data finishes uploading.

Bigquery will return the result to the backend where the gemini agent will interleave the result into a natural language summary / answer.

### Artifact

#### Typical user flow

A typical user flow
Let's trace a complete user request through your architecture:
User Action: A user interacts with your Dash app and performs an action that triggers the ETL process (e.g., uploads a CSV).
Data Upload: The Dash app (or its backend) uploads the CSV to Cloud Storage, perhaps triggering API calls for enrichment data.
ETL Jobs (Async): Cloud Functions are triggered by the GCS uploads and run the ETL to load the enriched data into BigQuery.
Completion Signal: After the 4 ETL jobs finish, the final Cloud Function is triggered. It retrieves the final BigQuery table schema.
Schema Transfer: The final Cloud Function sends the schema via an HTTP request to an endpoint on your server.
Server Processes Query: Your server's endpoint receives the schema. The LangGraph node, already holding the user's query from the Dash app, uses the schema to generate a valid BigQuery SQL query.
BigQuery Query: The server executes the LLM-generated query against BigQuery.
Results to Dash: The query results are sent back to the server, which then provides the data to your Dash app for visualization.
Visualization: The user sees the final visual on the Dash app.
This isn't "too much back and forth"; it's a series of purposeful handoffs between specialized services, a hallmark of a robust, modern microservices architecture.

### Tech stack for "The Engine"

#### Google Cloud Infrastructure and AI

* Google Cloud Storage (GCS): Provides scalable object storage for handling raw CSV data uploads from users via signed URLs. It also serves as the data lake for the analytics process.
* Eventarc (Event-driven Automation): Listens for events, such as a user file upload completing in GCS. Eventarc then triggers a Cloud Run service to begin the data analysis process.
* BigLake (Serverless Data Warehouse): A serverless, high-performance data warehouse used for executing SQL queries against the user-uploaded data. BigQuery can query data directly from GCS via external tables, avoiding the need to move data.
* Gemini Flash 2 (AI Agent): A large language model (LLM) for converting natural language questions from users into valid SQL queries that can be executed on BigQuery.
* Google Cloud SDKs (Integration): Provides the core client libraries for programmatic access to various Google Cloud services.
* Langchain: Various llm tooling setup + config

#### Development and Automation

* UV (Dependency Management): A Python package manager for fast and reliable dependency management. It ensures a consistent build environment.
* Docker & Compose (Containerization): Docker packages the application and its dependencies into portable containers. `docker-compose` simplifies the management of multi-container applications during local development.
* Taskfile (Task Automation): A modern alternative to Makefiles, Taskfile automates common development tasks like running tests, linting, and building the application.
* Pre-commit (Code Quality): `pre-commit` hooks automatically check and format code before each commit, enforcing code quality standards.

#### Application Backend (FastAPI)

* FastAPI (Web Framework): A modern, high-performance, asynchronous web framework for building the backend API.
* Uvicorn (ASGI Server): A server that runs the FastAPI application.
* Third-Party APIs (`requests`, `httpx`): Used for making HTTP requests to external APIs and services.
* Configuration Management (`python-dotenv`, `omegaconf`, `pyyaml`): Libraries for managing application configuration and secrets from environment variables and YAML files.
* firebase tools cloud devops for cloud function orchestration
    brew install npm
    npm install -g firebase-tools
    firebase emulators:start --only firestore
    export FIRESTORE_EMULATOR_HOST="localhost:8080"

#### Application Frontend (Dash/Plotly)

* Dash (Frontend Framework): A Python-based framework for building analytical web applications.
* Plotly (Charting): The core charting library used by Dash to create interactive and high-quality data visualizations.
* Dash Extensions (Custom Components): Provides additional functionality for Dash applications.
* Dash Mantine Components (UI/UX): A library for creating user interfaces within Dash.
* Dash Uploader (File Uploads): Handles file uploads directly from the browser within the Dash environment.
* Dash AG Grid (Data Tables): Used for displaying large, interactive data tables in the user interface.
* Dash Bootstrap Components (Styling): Provides Bootstrap-based components for consistent styling.

#### Data Processing and Validation

* Pandas (Data Manipulation): The library for data manipulation and analysis, used for tasks like schema inference. **Note** This is only used for testing data gen with `csvdatagen`.
* Pydantic (Data Validation): Enforces data types and validates data schemas, ensuring data integrity within the application.
* JSON Schema (`jsonschema`): A library for validating JSON data structures against a defined schema.
* Faker (Testing Data): Used to generate realistic fake data for testing purposes.
* Papaparse: extract user's csv column headers + infer column types in user's browser
  * Yes, use their power, save our server
* Foursquare: External API for enhanced insight to be merged with proprietary data for predictive analytics (foot traffic)
* Openmeteo: External API for weather data (foot traffic)
* BLS: External API for bureau of labor statistics data (socioeconomic)

#### Deployment

This application is designed to be deployed on Google Cloud Run. The containerized setup ensures a consistent and reliable deployment process.

* Build and push the container image to Google Artifact Registry.
* Deploy the image to Cloud Run and configure settings for "min instances" to ensure the app is always on.
* Map a custom domain (e.g., `your-app.com`) to the Cloud Run service.
* Set up Eventarc triggers to connect GCS events to the appropriate Cloud Run event handler.

## Project setup

* Clone the repo from <>
* Change directory with `cd <project_name>`
* Install `uv` by running `curl -LsSf https://astral.sh/uv/install.sh | sh` in your terminal
  * Verify with `uv --version`
* Run `uv sync`
  * Creates the `.venv`, reads project's `pyproject.toml`, installs deps into `.venv`, and creates the `uv.lock` file.
* Run `task uvicorn-build`
* Run `task uvicorn-up`
* Visit <http://0.0.0.0:8000/dash/>

**Notes on UV:**

* `pytest` works in the virtual env, so does `uv run pytest`. `pytest` will not work outisde the virtual environment, however `uv run pytest` will, it uses .venv behind the scenes.
* `uv cache clean`: clear everything if your doing fresh runs and deleting .venv
* `uv sync`: creates the .venv for you and updates .lock. You can enter .venv with source `.venv/bin/activate` but no need to if you run `uv run pytest`.
* Run to update local env with an updated uv.lock file.
* `uv lock`: run whenever pyproject.toml is updated.
* Run `uv run --env-file .env pytest` so `uv run pytest` sees your .env file, this way you can prevent

**Notes on Docker:**

When to rebuild:

* You've edited the Dockerfile
* You've updated pyproject.toml
* You've changed imports + file names
* You've added new dependencies in pyproject.toml. Invalidates uv sync layer in Dockerfile

When to compose down + up:

* Server is crashing
* Dash web browser is not functioning
* .env file updates / changes
* Changes to compose.yaml such as container settings, port mappings, or environment variables
* Added a new project file under src (ie. adding papaparse.min.js requires an up+down)

**Notes (misc):**

pyproject.toml

* `pyproject.toml`: don't specifiy 3.13.X just do >=3.13, a specific version causes all sorts of problems

**Notes on GCP:**

Process to follow when adding a new bucket

1. Run `task configure-cors -- <bucket-name>`
2. Add storage.object.admin role to the service account using the bucket. Don't forget to make sure your local credentials are using that same service account!

## Testing

Review `tests/test_app_dash.py` and `tests/test_app_fastapi.py` for proper fixture + pytest configurations for apps.

Review `tests/test_config.py` and `tests/test_logger.py` to understand how objects are mocked in fixtures for pytests such as how the config object is mocked for the logger class.

## Debugging

You can pause javacscript execution by placing `debugger` anywhere in your `.js` file.

Utilize Dash UI built in errors + callbacks monitor

Use browser inspect (f12), utilize filters in the console and network tabs to trace callbacks

## Tips

`git pull --rebase -X theirs` or `git pull --rebase -X ours`

* Rebase your local commits on top of the remote ones, and automatically resolve conflicts in favor of the remote's changes. Use when you have local changes but need to pull in remote changes (someone pushed to it) and you want it auto resolved with your changes or with theirs.
