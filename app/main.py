import sys
import logging
from wsgi import app


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    This is the entry point for AWS Lambda.
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    try:
        # Import awsgi here to avoid import errors in non-Lambda environments
        import awsgi

        logger.info("Starting AWS Lambda handler")
        return awsgi.response(app, event, context)
    except ImportError:
        logger.error(
            "awsgi package not found. Make sure to include it in your deployment\n"
            "package."
        )
        raise
    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        raise
