# Known Issues

## HIGH PRIORITY

* Firestore will increment indefinitely. Near term solution is modulus every 4
far term solution is to pass unique id's instead of hardcoding with environment variable
Maybe it's a good thing to keep the counter to track number of executions?

## LOW PRIORITY

* Test performance of the api call. Measure should it be this much slower with llm call

* Sample Data field in llm prompt may not be interpolating, inspect

* Add cryptographically secure job id that works in all web browsers

* autoscaling issue? not sure... when first function is triggered. maybe its normal
logs" Starting new instance. Reason: AUTOSCALING - Instance started due to configured scaling factors (e.g. CPU utilization, request throughput, etc.) or no existing capacity for current traffic."

* TURNED OFF:
  * VALIDAITON NODE
    * Massively slows down query results when we need fast iterations
  * VECTOR STORE (REQUIRES SENTENCE-TRANSFORMERS in PYPROJECT)
    * Far too slow on startup and docker builds with the library imports
  * LOGGER + CONFIG CLASSES
    * Lose 5 seconds every single reload

* After not using the upload service for it seems like an hour or so, the 0 bytes
bug when uploading happens. Doing just a `task uvicorn-up` fixes the issue. This is
a critical issue for a prod deploy, but not so important for dev. I will be coming back
to this some day...
Today it worked after not being used for many hours, so this bug seems random, most likely
not but it seems that way.

Resolution:

    - Drag and drop works only after a click and upload. This suggests race condition or
        some priming issue with Dash and browser...
    - Ansewr for now is go with the click to upload for developing the app... it's faster
    - Lessons learned: No overengineering, you only need click to upload, you don't need
        both in this stage. LEARN FROM THIS!!! BIG ONE

* There is a line that does not pass through the configured logger, may be only related to
reload. No big deal at the moment
2025-10-12 14:38:52 StatReload detected changes in 'src/app/app_fastapi.py'. Reloading...

* Why is the first upload so slow after a fresh docker build? Does not happen after docker up + down?

* How can I stop this warning from happening?
"component is changing an uncontrolled input to be controlled. This is likely caused by the value changing from undefined to a defined value, which should not happen. Decide between using a controlled or uncontrolled input element for the lifetime of the component. More info:"

* Fails with drop in internet connection

* near/city api param is bugged because our Fake data gives fake cities or foursquare doesn't return
Data for them, and we need data for testing
near: str = Field(description="The location to search in (e.g., 'New York', 'Los Angeles').")

* The validation node can take a long time to validate before the rest of the chain can fire
API calls... not entirely sure what to do about this...

* Not really bugs, but EXTREME pain point in development. 1. Is the vector store takes an insane amount of time for docker builds AND for reload. Terrible for development. 2. The logger and config objects take 5 seconds every reload... disabling for now, will be useful later.

## RESOLVED

* Still hitting memory limit issues on cloud functions
Increaseing memory from 256 to 512... 256 for etl task is far too little
Fixed the memory bug, now we get `starting autoscaling` which is totally normal

* Sometimes on first load there is a massive hang on resumable upload
hangs on chunk
hangs on resumable upload
Not resolved, still hanging, it looks like the chunks may need to be made smaller,
much much smaller
The problem is the internet upload from phone is terrible on hotspot, and
upload speeds are alwasy bottlenecked RIP.

Actually what seems to have resolved this hang during chunking is commenting out the
second clientside callback. Now with just 1 python callback and 1 clientside callback
firing, it is MUCH smoother.

Here is the explanation: R-E-S-O-U-R-C-I-N-G RESOURCING!

If you have TWO clientside callbacks fire from the same dcc.store update, they compete for
resources on the same thread.
Just wrapping the code in async functions COULD have resolved this issue, you forgot to
wrap the parse csv function in async, see "complete: function(results)...
But this does NOT resolve the race condition of having two clientside callbacks and 1
server side python callback firing off of one dcc.store input. This would still cause issues, and can only be fixed by combining the two clientside javascript callbacks...
HOWEVER, this has directed me to a new path... I'm deciding not to go forward with the
schema extraction on the clients browser, this is terrible for security anyways. It was a
fun idea, but a bit of a waste of time, and can be simplified.

The Result of this is we move forward with one clientside javascript callback for a streamed signed url upload from clients browser, and one server side python callback which
posts the user query, job_id and initiates the serverless data pipeline.
Concise - "An interactive, LLM-powered data enrichment pipeline"
Descriptive - "A serverless data pipeline for market research, where a Dash front end
orchestrates an LLM-powered ETL process using Google Cloud Functions, Firebase and Bigquery to respond to user queries with enriched data and insightful visualizations"
