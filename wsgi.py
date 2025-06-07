from app import create_app
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

try:
    app = create_app()
    if __name__ == "__main__":
        logger.info("Starting application...")
        try:
            app.run(debug=True, port=5001)
        except Exception as e:
            logger.error(f"Failed to run application: {str(e)}", exc_info=True)
            raise
except Exception as e:
    logger.error(f"Failed to create application: {str(e)}", exc_info=True)
    sys.exit(1)
