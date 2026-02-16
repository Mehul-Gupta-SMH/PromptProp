"""
Main entry point for launching the PromptProp Backend API server.

This script initializes and runs the FastAPI application defined in route.py,
which handles prompt refinement, jury evaluation, and experiment management.
"""

import uvicorn
import logging
from configs.getConfig import getConfig
from db import Base, engine
from db.session import database_url
from resources.registerMetrics import configure as mlflow_configure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Main function to launch the FastAPI server with uvicorn.

    Loads configuration from the environment and starts the server
    on the specified host and port.
    """
    try:
        # Load configuration
        config = getConfig()
        logger.info(f"Configuration loaded successfully")

        # Extract server settings from config
        host = config.get('server', {}).get('host', '0.0.0.0')
        port = config.get('server', {}).get('port', 8000)
        reload = config.get('server', {}).get('reload', False)
        workers = config.get('server', {}).get('workers', 1)

        # Create tables for dev (SQLite). Prod uses Alembic migrations.
        if database_url.startswith("sqlite"):
            logger.info("Dev mode: creating SQLite tables via create_all()")
            Base.metadata.create_all(bind=engine)

        # Configure MLflow tracking
        mlflow_uri = config.get('mlflow', {}).get('tracking_uri')
        if config.get('mlflow', {}).get('enabled', False):
            mlflow_configure(mlflow_uri)
            logger.info(f"MLflow tracking enabled")

        logger.info(f"Starting PromptProp Backend API")
        logger.info(f"Server Configuration:")
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Workers: {workers}")
        logger.info(f"  Reload: {reload}")

        # Available endpoints
        logger.info("Available Endpoints:")
        logger.info("  GET  /health-check - Health check endpoint")
        logger.info("  GET  /jury - Jury evaluation endpoint")
        logger.info("  GET  /evaluate - Evaluation processing endpoint")
        logger.info("  GET  /evaluation_metrics - Evaluation metrics endpoint")
        logger.info("  POST /train_data - Training data upload endpoint")
        logger.info("  POST /validation_data - Validation data upload endpoint")
        logger.info("  POST /test_data - Test data upload endpoint")
        logger.info(f"\nServer will be available at http://{host}:{port}")
        logger.info(f"API Documentation available at http://{host}:{port}/docs")

        # Launch the server using import string for app
        # This is required when using 'reload' or 'workers' options
        uvicorn.run(
            "route:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,  # Single worker when reload is enabled
            log_level="info"
        )

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
