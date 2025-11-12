upload_style = {
    "width": "100%",
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "dashed",
    "borderRadius": "5px",
    "textAlign": "center",
    "position": "relative",
}

button_active_style = {
    "width": "100%",  # Use 100% width, managed by the parent flex container
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "solid",  # Changed to solid border for buttons
    "borderRadius": "5px",
    "textAlign": "center",
    "position": "relative",
    "cursor": "pointer",     # Changes mouse cursor to a hand pointer
    "backgroundColor": "#007bff", # A standard blue color
    "color": "white",        # White text for contrast
}

# Style for when the button is DISABLED (grey, not clickable)
button_disabled_style = button_active_style.copy()
button_disabled_style["backgroundColor"] = "#cccccc" # Grayed out background
button_disabled_style["color"] = "#666666"            # Darker text
button_disabled_style["cursor"] = "not-allowed"      # Changes mouse cursor to a not-allowed symbol


response_style = {
    "width": "100%",
    "lineHeight": "normal", # Use normal line height for expansion
    "textAlign": "center",
    "margin": "10px",
    "borderRadius": "5px",
    "position": "relative",
    "wordBreak": "break-word", # Breaks long words to fit the container
    "overflowWrap": "break-word", # Legacy property for older browsers
}

load_spinner_style = {
    'marginTop': '20px'
}

# Define a dark style dictionary
dark_table_style = {
    'backgroundColor': '#2c3e50',  # Dark background color (from DARKLY theme palette)
    'color': '#ecf0f1'             # Light text color (from DARKLY theme palette)
}

# Define the style for headers
header_style = {
    'height': 'auto', 
    'backgroundColor': '#34495e',  # Slightly lighter dark for headers
    'color': 'white',
    'fontWeight': 'bold'
}
