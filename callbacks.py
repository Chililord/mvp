from dash import Input, Output, State, clientside_callback, html
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
            Output("upload-status-message", "children"),
            Output("enriched-data-table", "data"),
            Output("enriched-data-table", "columns"), 
            Input('submit-button', 'n_clicks'),
            State('upload-data', 'contents'),
            State('upload-data', 'filename'),
            prevent_initial_call=True
        )
    def enrich_data(n_clicks, contents, filename):

        if os.environ['APP_ENV'] == 'local':

            fastapi_endpoint = "http://0.0.0.0:8000/enrich_products"

        else:

            runpod = os.getenv("RUNPOD_ID")

            fastapi_endpoint = f"https://{runpod}-8000.proxy.runpod.net/enrich_products"
        
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
                dynamic_columns = [{"name": i, "id": i} for i in all_keys]

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
        Input('enriched-data-table', 'data')
    )
    def toggle_download_button(table_data):
        return (True, button_disabled_style) if not bool(table_data) else (False, button_active_style)

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