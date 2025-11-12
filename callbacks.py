from dash import Input, Output, State, clientside_callback, html
from dash.exceptions import PreventUpdate

from assets.css.styles import *
from loguru import logger
import requests
import base64
import io 
import os

def register_data_callbacks(app_dash):

    @app_dash.callback(
        Output('submit-button', 'disabled'),
        Output('submit-button', 'style'),
        Input('upload-data', 'filename')
    )
    def toggle_submit_button(filename):
        return (True, button_disabled_style) if filename is None else (False, button_active_style)


    @app_dash.callback(
            Output("upload-status-message", "children", allow_duplicate=True),
            Output("enriched-data-table", "data"),
            Output("enriched-data-table", "columns"), 
            Input('submit-button', 'n_clicks'),
            State('upload-data', 'contents'),
            State('upload-data', 'filename'),
            prevent_initial_call=True
        )
    def enrich_data(n_clicks, contents, filename):

        if os.environ['APP_ENV'] == 'local':

            fastapi_endpoint = "http://0.0.0.0:8000/enrich-products"

        else:

            runpod = os.getenv("RUNPOD_ID")

            fastapi_endpoint = f"https://{runpod}-8000.proxy.runpod.net/enrich-products"
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        try:
            files = {'file': (filename, io.BytesIO(decoded), 'text/csv')} 

            logger.info("Posting from Dash to fastapi endpoint")

            response = requests.post(fastapi_endpoint, files=files)
            
            if response.status_code == 200:
                enriched_data_list = response.json()
                num_items = len(enriched_data_list)
                
                if num_items == 0:
                    return "Processed 0 items.", [], [], True

                all_keys = enriched_data_list[0].keys()
                dynamic_columns = [{"name": i, "id": i} for i in all_keys if i != 'id']

                return (
                    f"Successfully processed {num_items} items!",
                    enriched_data_list,                          
                    dynamic_columns,                                                              
                )
            else:
                error_detail = response.json().get("detail", "Unknown error")
                return html.Div(f"Error from API: {error_detail}", style={'color': 'red'}), [], []

        except Exception as e:
            return html.Div(f"An error occurred: {str(e)}", style={'color': 'red'}), [], []



    @app_dash.callback(
        Output('download-button', 'disabled'),
        Output('download-button', 'style'),
        Output('batch-resynth-button', 'disabled'),
        Output('batch-resynth-button', 'style'),
        Input('enriched-data-table', 'data')
    )
    def toggle_download_button(table_data):
        return (True, button_disabled_style, True, button_disabled_style) if not bool(table_data) else (False, button_active_style, False, button_active_style)

    clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                // This forces the browser to navigate to the URL and initiate the download prompt
                window.location.href = '/download-results'; 
            }
            // Return a dummy value, since the action is handled client-side
            return '';
        }
        """,
        Output('url', 'href'), 
        Input('download-button', 'n_clicks'),
        prevent_initial_call=True
    )

    @app_dash.callback(
    Output('upload-status-message', 'children', allow_duplicate=True),
    Output('refresh-trigger', 'data'), # <-- Add this output
    Input('enriched-data-table', 'data'),
    State('enriched-data-table', 'data_previous'),
    State('refresh-trigger', 'data') # <-- Add this state
    )
    def update_database_full_row(current_data, previous_data, trigger_data):
        if current_data is None or previous_data is None:
            raise PreventUpdate

        # This finds the difference based on comparing list lengths/content
        # A simplified way to find *which* specific row was just edited
        changed_row = next((row for row in current_data if row not in previous_data), None)

        if changed_row:
            # We found the dictionary of the entire row that was modified
            payload = changed_row 
            if os.environ['APP_ENV'] == 'local':

                fastapi_endpoint = "http://0.0.0.0:8000/update-row"

            else:
                runpod = os.getenv("RUNPOD_ID")

                fastapi_endpoint = f"https://{runpod}-8000.proxy.runpod.net/update-row"

            response = requests.put(fastapi_endpoint, json=payload)
            
            if response.status_code == 200:
                return f"Updated row {changed_row.get('product_name', 'N/A')} in the database.", trigger_data + 1 
            else:
                return f"Error updating database: {response.json().get('detail', 'Unknown error')}", trigger_data

        raise PreventUpdate 
    


    @app_dash.callback(
        Output('upload-status-message', 'children', allow_duplicate=True),
        Output('refresh-trigger', 'data', allow_duplicate=True),
        Input('batch-resynth-button', 'n_clicks'), # The new button's n_clicks is the input
        State('enriched-data-table', 'data'),      # The full dataset in the table
        State('enriched-data-table', 'selected_rows'), # The indices of selected rows
        State('refresh-trigger', 'data')
    )
    def handle_batch_resynthesis(n_clicks, table_data, selected_row_indices, trigger_data):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate

        if not selected_row_indices:
            return "Please select at least one row to process.", trigger_data

        # Extract the full dictionary data for the selected rows
        # The indices refer to the position in the 'data' list
        rows_to_process = [table_data[i] for i in selected_row_indices]

        # Determine FastAPI endpoint URL (your local/runpod logic here)
        fastapi_endpoint = "http://localhost:8000/resynthesize-batch" 

        logger.info("test from inside resynth function")
        # Send the list of dictionaries as a JSON payload
        response = requests.post(fastapi_endpoint, json=rows_to_process)

        if response.status_code == 200:
            # Increment trigger and return success message
            msg = f"Batch processing of {len(rows_to_process)} rows started successfully."
            return msg, trigger_data + 1
        else:
            # Return error message
            error_msg = response.json().get("detail", "Unknown API error during batch resynthesis.")
            return error_msg, trigger_data


    @app_dash.callback(
        Output('enriched-data-table', 'data', allow_duplicate=True), 
        Input('refresh-trigger', 'data')       
    )
    def refresh_table_data_from_db(n_triggers):
        # Prevents running when the app first loads (n_triggers is None or 0 initially)
        if n_triggers is None or n_triggers == 0:
            raise PreventUpdate
            
        # Determine the FastAPI endpoint URL to GET ALL data from the DB
        # You need this endpoint to exist in app_fastapi.py, e.g., "/get-all-data-json"
        fastapi_endpoint = "http://localhost:8000/get-all-data-json" 
        
        # Send a GET request to the backend to retrieve the *entire* dataset
        response = requests.get(fastapi_endpoint)
        
        if response.status_code == 200:
            # The data returned is a list of dictionaries (JSON)
            # This repopulates the entire Dash DataTable UI with the freshest data
            return response.json() 
        else:

            return [] 