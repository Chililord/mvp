from dash import Input, Output, State, clientside_callback, html, dcc, dash_table
from dash.exceptions import PreventUpdate
import csv
from assets.css.styles import *
from loguru import logger
import requests
import base64
import json
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
            Output("enriched-data-table", "style_data_conditional"), # <-- Add this output
            Output("enriched-data-table", "style_header_conditional"), # <-- Add this output
            Input('submit-button', 'n_clicks'),
            State('upload-data', 'contents'),
            State('upload-data', 'filename'),
            State('schema-mode-selector', 'value'), # 'defaults' or 'custom'
            State('custom-schema-store', 'data'),   # List of {'name':..., 'description':...}
            prevent_initial_call=True
        )
    def enrich_data(n_clicks, contents, filename, mode_selection, custom_schema_data):

        # ... (omitted environment variable logic for fastapi_endpoint) ...
        fastapi_endpoint = "http://localhost:8000/enrich-products" # Define your endpoint here

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        decoded_io = io.StringIO(decoded.decode('utf-8'))
        decoded_bytes_io = io.BytesIO(decoded) 

        try:
            reader = csv.reader(decoded_io)
            csv_header_sequence = next(reader)
        except Exception as e:
            return html.Div(f"Error reading CSV headers: {str(e)}", style={'color': 'red'}), [], [], [], [] # Handle error returns with empty styles

        if mode_selection == 'custom':
            if not custom_schema_data:
                return html.Div("Error: Custom schema selected but no fields added.", style={'color': 'red'}), [], [], [], []
            schema_payload_dict = {'mode': 'custom', 'fields': custom_schema_data}
        else: 
            schema_payload_dict = {'mode': 'defaults', 'fields': []}

        # CRITICAL CHANGE 1: Convert the dictionary to a JSON string
        schema_payload_json_str = json.dumps(schema_payload_dict)

        # CRITICAL CHANGE 2: Send the file as bytes
        files = {'file': (filename, decoded_bytes_io, 'text/csv')} 
        
        # CRITICAL CHANGE 3: Use the 'data' parameter to include non-file form fields
        # We are sending a dictionary where the key matches the FastAPI endpoint parameter name
        # The value is the JSON string we created above
        data = {'schema_config_str': schema_payload_json_str} 
        
        logger.info("Posting from Dash to fastapi endpoint")

        response = requests.post(fastapi_endpoint, files=files, data=data)
        
        if response.status_code == 200:
            enriched_data_list = response.json()
            num_items = len(enriched_data_list)

            if num_items == 0:
                # Return empty styles for 0 items processed scenario
                return "Processed 0 items.", [], [], [], [] 

            # --- Column Ordering Logic (Your Solution) ---
            all_returned_keys_set = set(enriched_data_list[0].keys())
            
            original_column_order = [
                col for col in csv_header_sequence 
                if col in all_returned_keys_set
            ]

            # 2. Identify new columns NOT present in the original order list
            original_set = set(original_column_order) 
            new_columns = sorted(list(all_returned_keys_set - original_set))

            # 3. Combine the lists: Original order first, new columns appended at the end
            final_display_order = original_column_order + new_columns
            
            # 4. Filter out the 'id' column from the final display list
            columns_to_display = [col for col in final_display_order if col != 'id']

            # 5. Create the dynamic columns list using the guaranteed order
            dynamic_columns = [{"name": i, "id": i} for i in columns_to_display]
            
            # 6. Calculate the index where synthesized columns start for styling purposes
            synth_start_index = len(original_column_order) 
            
            # --- Styling Logic (Combined Solution) ---
            data_conditional_styles = [
                { 
                    'if': {'state': 'active'}, 
                    'backgroundColor': '#FFD700', 
                    'color': 'black', 
                    'border': '1px solid #FFD700',
                    'textAlign': 'left' # <--- ADDED HERE
                }
            ]            
            header_conditional_styles = []

            SYNTH_BG_COLOR = '#1a252f' 
            SYNTH_TEXT_COLOR = '#95a5a6' # A contrasting light gray color

            if columns_to_display and synth_start_index is not None:
                for i in range(synth_start_index, len(columns_to_display)):
                    col_id = columns_to_display[i]
                    data_conditional_styles.append({
                        'if': {'column_id': col_id}, 
                        'backgroundColor': SYNTH_BG_COLOR, 
                        'color': SYNTH_TEXT_COLOR, # <-- Use the contrasting color here
                    })
                    header_conditional_styles.append({
                        'if': {'column_id': col_id}, 
                        'backgroundColor': SYNTH_BG_COLOR, 
                        'color': SYNTH_TEXT_COLOR, # <-- Use the contrasting color here
                    })


            # --- Return all outputs ---
            return (
                f"Successfully processed {num_items} items!",
                enriched_data_list,                          
                dynamic_columns,
                data_conditional_styles, # Return the generated data styles
                header_conditional_styles # Return the generated header styles
            )
        else:
            error_detail = response.json().get("detail", "Unknown error")
            # Handle error returns with empty styles
            return html.Div(f"Error from API: {error_detail}", style={'color': 'red'}), [], [], [], []

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

    @app_dash.callback(
        Output('custom-schema-wrapper', 'style'),
        Input('schema-mode-selector', 'value'),
        State('custom-schema-wrapper', 'style')
    )
    def toggle_custom_schema_ui_visibility(mode_selection, current_style):
        if mode_selection == 'custom':
            # Return the style to SHOW the div (e.g., block display)
            return {'display': 'block'} 
        else:
            # Return the style to HIDE the div
            return {'display': 'none'}
        
    @app_dash.callback(
        Output('schema-fields-table', 'data'),
        Output('custom-schema-store', 'data', allow_duplicate=True),
        Output('field-name-input', 'value'),
        Output('description-input', 'value'),
        Output('schema-limit-feedback', 'children', allow_duplicate=True),
        Input('add-field-button', 'n_clicks'),
        State('field-name-input', 'value'),
        State('description-input', 'value'),
        State('schema-fields-table', 'data'), # The current state of the displayed table
        prevent_initial_call=True # We prevent initial call as this only runs on button click
    )
    def manage_custom_schema(n_clicks, name, description, current_rows):
        if n_clicks is None:
            raise PreventUpdate

        MAX_COLS = 3
        feedback = ""

        if name and description:
            # Check if we hit the limit before adding
            if len(current_rows) >= MAX_COLS:
                feedback = f"Limit reached. Maximum of {MAX_COLS} custom fields allowed."
                # Return current state without adding new row, keep inputs filled, show error
                return current_rows, current_rows, name, description, feedback

            new_row = {'name': name, 'description': description}
            current_rows.append(new_row)
        
        # Return the updated list to both the visible table and the hidden store, clearing inputs
        return current_rows, current_rows, "", "", "" # Clear feedback and inputs on success/empty add
    
    @app_dash.callback(
        Output('custom-schema-store', 'data', allow_duplicate=True),
        Output('add-field-button', 'disabled'), # Manage button disabled state here too
        Output('schema-limit-feedback', 'children', allow_duplicate=True), 
        Input('schema-fields-table', 'data'), # This input triggers on load, but we handle it:
        prevent_initial_call=True # <-- Ensure this is present
    )
    def sync_table_to_store_and_manage_limit(table_data_after_change):
        MAX_COLS = 3
        
        # Sync the store with the new table data (handles both additions and deletions)
        updated_store_data = table_data_after_change
        
        # Check the limit status
        if len(updated_store_data) >= MAX_COLS:
            # Disable the add button and show feedback
            return updated_store_data, True, f"Limit reached. Maximum of {MAX_COLS} custom fields allowed."
        else:
            # Enable the add button and clear feedback
            return updated_store_data, False, ""