from assets.css.styles import *
from dash import dcc, html, dash_table 

user_interface = html.Div(
    [
        # --- Hidden Component required for client-side downloads + trigger table refresh ---
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='refresh-trigger', data=0),

        # --- Upload Row ---
        html.Div(
            [
                dcc.Upload(
                    id="upload-data",
                    children=html.Div("Click to enrich data"),
                    style=upload_style,
                    multiple=False,
                ),
            ],
            style={'margin': '10px'}
        ),
        # --- Submit and Download Row ---
        html.Div([
            html.Button("Submit CSV Data",
                         id="submit-button", 
                         n_clicks=0, 
                         style=button_disabled_style, 
                         disabled=True),

            html.Button("Re-synthesize Rows",
                         id='batch-resynth-button',
                         n_clicks=0,
                         style=button_disabled_style,
                         disabled=True),      

            html.Button("Download CSV Results",
                         id="download-button",
                         n_clicks=0,
                         style=button_disabled_style,
                         disabled=True),
            ], style={'display': 'flex', 'gap': '10px', 'margin': '10px'}
        ),

        # --- Loading Spinner & Status Message ---
        html.Div(dcc.Loading(
            id="loading-spinner",
            type="default",
            children=[
                # Spinner wait for this update don't move it out
                html.Div(id="upload-status-message", style=response_style)
            ]
        ),style=load_spinner_style),

        # --- Data Table ---
        dash_table.DataTable(
            id='enriched-data-table',
            data=[],      
            columns=[],    
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_data=dark_table_style,
            style_header=header_style,
            style_as_list_view=True,
            editable=True,
            row_selectable='multi',
            selected_rows=[],
        ),
    ]
)
