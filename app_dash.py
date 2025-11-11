from dash_extensions.enrich import DashProxy
import pathlib
import dash_bootstrap_components as dbc
from loguru import logger
from component import user_interface
from callbacks import register_data_callbacks
import os

def create_app_dash():

    logger.info("setting up app_dash")

    # Define the absolute path to the assets folder


    # Define the absolute path to the assets folder reliably
    # Use pathlib to construct the absolute path if running locally
    if os.environ['APP_ENV'] == 'local':
        assets_path = pathlib.Path(__file__).parent.resolve() / "assets"
    else:
        # Default to runpod path if needed
        assets_path = "/workspace/mvp/assets"

    app_dash = DashProxy(
            requests_pathname_prefix="/dash/",
            external_stylesheets=[dbc.themes.DARKLY],
            assets_folder=assets_path # Provide the absolute path here

        )

    configure_dev_tools(app_dash, os.getenv("ENVIRONMENT", "DEV"))


    register_data_callbacks(app_dash)

    app_dash.layout = user_interface

    logger.info("app_dash is configured")
    return app_dash

def configure_dev_tools(app, env):
    """
    Enables Dash dev tools on the provided app instance with given options.
    """
    if env == "DEV":
        dev_tools_options = {
            "debug": True,
            "dev_tools_ui": True,
            "dev_tools_props_check": True,
            "dev_tools_serve_dev_bundles": True,
            "dev_tools_hot_reload": True,
        }
    else:
        dev_tools_options = {"debug": False}



    app.enable_dev_tools(**dev_tools_options)
