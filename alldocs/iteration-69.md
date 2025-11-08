# Pipeline execution architecture

Entrypoint
    User uploads file (Client/Dash App): The user initiates the process by uploading a file and submitting a query through the Dash app. The app's router handles this request.

Dash app's User Data Router (Server):
    Generates a unique jobId.
    Creates a Firestore document with the jobId and the userQuery, and initializes the completedJobs counter to 0.
    Uploads the user's file to Cloud Storage, with the path including the jobId.
    Makes an HTTP POST request to the api_orchestrator Cloud Function, including the jobId and userQuery in the payload.

API Orchestrator Cloud Function (First Cloud Function):
    This function is triggered by the HTTP POST from your server.
    It receives the jobId and userQuery.
    It runs three parallel, asynchronous tasks. Each task performs an LLM call to extract specific parameters from the userQuery and then calls its respective external API.
    For each API call, it writes the result to a file in Cloud Storage, with the path including the jobId.

ETL Cloud Function (Fires 4 times):
    This is your existing function, triggered by the four GCS uploads.
    It performs the ETL into BigQuery for its specific file.
    It atomically increments the completedJobs counter in the Firestore document for the jobId.

Final Cloud Function (Triggered by counter):
    This function is triggered by the Firestore counter reaching 4.
    It retrieves the BigQuery schema and the userQuery from Firestore.
    It uses an LLM to generate the BigQuery SQL query based on the userQuery and schema.
    It executes the generated BigQuery query.
    It stores the results of the query in a persistent store.
    It deletes the job document from Firestore.

Dash App (Retrieves results):
    The Dash app, using the jobId, polls or listens to the persistent store for the final results.
    Once the results are available, it retrieves and displays them.
