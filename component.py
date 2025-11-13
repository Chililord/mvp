from assets.css.styles import *
from dash import dcc, html, dash_table 

user_interface = html.Div(
    [
        # --- Hidden Component required for client-side downloads + trigger table refresh ---
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='refresh-trigger', data=0),
       # This stores the list of custom schema fields globally
        dcc.Store(id='custom-schema-store', data=[]), 

        # --- Upload Row ---
        html.Div(
            [
                dcc.Upload(
                    id="upload-data",
                    children=html.Div("Click to upload data"),
                    style=upload_style,
                    multiple=False,
                ),
            ],
            style={'margin': '10px'}
        ),

        # --- Schema Selection Row---
         html.Div([
            html.Label("Choose Enrichment Mode:"),
            dcc.RadioItems(
                id='schema-mode-selector',
                options=[
                    {'label': ' Defaults (Insight, Score, Anomaly)', 'value': 'defaults'},
                    {'label': ' Custom Schema', 'value': 'custom'}
                ],
                value='defaults', # Default selection
                style={'marginBottom': '10px'}
            ),

            # --- ALL dynamic components are now here on initial load ---
            html.Div(id='custom-schema-wrapper', children=[
                html.Div([
                    dcc.Input(id='field-name-input', type='text', placeholder='Field Name'),
                    dcc.Input(id='description-input', type='text', placeholder='Description for LLM'),
                    html.Button('Add Field', id='add-field-button', n_clicks=0),
                ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '10px'}),
                
                html.Div(id='schema-limit-feedback', style=warning_text_style),
                
                dash_table.DataTable(
                    id='schema-fields-table',
                    columns=[{"name": "Field Name", "id": "name"}, {"name": "Description", "id": "description"}],
                    data=[], 
                    row_deletable=True,
                    style_table={'margin-top': '10px'},
                    style_data=dark_table_style, 
                    style_header=header_style, # Use your existing header style
                ),
            ], style={'display': 'none'}), # <-- THIS DIV STARTS HIDDEN

        ], style={'margin': '10px 10px 0 10px', 'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px'}), 




        # --- Submit, Re-synthesize, Download Row ---
        html.Div([
            html.Button("Upload & Synthesize",
                         id="submit-button", 
                         n_clicks=0, 
                         style=button_disabled_style, 
                         disabled=True),

            html.Button("Re-synthesize Rows",
                         id='batch-resynth-button',
                         n_clicks=0,
                         style=button_disabled_style,
                         disabled=True),      

            html.Button("Download CSV Data",
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
        html.Div([
                # --- Data Table ---
                dash_table.DataTable(
                    id='enriched-data-table',
                    data=[],      
                    columns=[],    
                    page_size=20,
                    style_table={
                        'overflowX': 'auto',
                    },
                    style_cell={
                        'textAlign': 'left',         # Align text to the left
                        
                        # --- MODIFIED PROPERTIES FOR SCROLLING ---
                        'whiteSpace': 'pre',         # Allow content to stay on one line, respecting whitespace
                        'overflowX': 'auto',         # Add horizontal scrollbar if needed
                        'textOverflow': 'clip',      # Do not show "..." ellipsis
                        # ----------------------------------------
                        'minWidth': '200px',         # Minimum width
                        'width': '200px',            # Fixed width
                        'maxWidth': '200px',         # Maximum width

                        'border-right': '1px solid #34495e', # A solid line matching your header background color
       
                    },
                    style_data=dark_table_style,
                    style_header=header_style,
                    editable=True,
                    row_selectable='multi',
                    selected_rows=[],
                    style_data_conditional=[
                        {
                            'if': {'state': 'active'},
                            'backgroundColor': '#FFD700', # Gold
                            'color': 'black', # Black text
                            'border': '1px solid #FFD700',
                            'textAlign': 'left',         # Align text to the left

                        }
                    ]
                ),
            ],
            # Fix pagination arrows bottom right
            style={'margin-left': '10px', 'margin-right': '10px'}
        )
    ]
)
