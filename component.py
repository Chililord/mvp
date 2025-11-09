from assets.css.styles import *
from dash import dcc, html, dash_table

user_interface = html.Div(
    [
        html.Div(
            [
                dcc.Upload(
                    id="upload-data",
                    children=html.Div("Click to enrich data"),
                    style=upload_style,
                    multiple=False,
                ),
            ]
        ),
        html.Div(html.Button("Submit",
                     id="submit-button", 
                     n_clicks=0, 
                     style=upload_style, 
                     disabled=True)),
    
        html.Div(dcc.Loading(
            id="loading-spinner",
            type="default",
            children=[
                html.Div(id="upload-status-message", style=response_style)
            ],
        ),style=load_spinner_style),
        dash_table.DataTable(
            id='enriched-data-table',
            data=[],      
            columns=[],    
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_data=dark_table_style,
            style_header=header_style,
            # This style makes the borders collapse for a cleaner look
            style_as_list_view=True,
        ),
    ]
)
