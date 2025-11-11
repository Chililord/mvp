from dash import Input, Output, State, clientside_callback
import dash
from loguru import logger
import requests
import base64
import io 
import os

import dash_html_components as html 

def register_data_callbacks(app_dash):

    @app_dash.callback(
        Output('submit-button', 'disabled'),
        Input('upload-data', 'filename')
    )
    def toggle_submit_button(contents):

        return contents is None

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
