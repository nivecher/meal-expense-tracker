import os
import logging
import sys
from app import create_app

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = create_app()

# AWS Lambda support
if os.environ.get("AWS_EXECUTION_ENV"):
    try:
        import awsgi

        def handler(event, context):
            """
            AWS Lambda handler function.
            This is the entry point for AWS Lambda.
            """
            return awsgi.response(app, event, context)

    except ImportError:
        logger.warning("awsgi package not found. AWS Lambda support disabled.")

if __name__ == "__main__":
    # Run the application locally if not running on AWS Lambda
    logger.info("Starting application locally...")
    try:
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=True, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Failed to run application: {str(e)}", exc_info=True)
        raise
