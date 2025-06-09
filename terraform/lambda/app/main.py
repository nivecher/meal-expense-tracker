"""
AWS Lambda handler for the Meal Expense Tracker application.
This file serves as the entry point for AWS Lambda.
"""
import os
import sys
import logging
from mangum import Mangum
from app.main import create_app

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create the Flask application
app = create_app()

# Create the Mangum handler
handler = Mangum(app, api_gateway_base_path=os.environ.get('API_GATEWAY_BASE_PATH', ''))


def lambda_handler(event, context):
    """Handle incoming Lambda requests.
    
    This is the main entry point for AWS Lambda. It uses Mangum to handle
    the translation between API Gateway/Lambda events and ASGI.
    
    Args:
        event: The event dict containing request data.
        context: The context object for the Lambda function.
        
    Returns:
        The response from the Flask application.
    """
    logger.info("Received event: %s", event)
    
    # Handle warm-up events
    if 'warmup' in event.get('resource', ''):
        return {
            'statusCode': 200,
            'body': 'Warmed up!'
        }
    
    # Process the request through Mangum
    response = handler(event, context)
    
    # Log the response status code
    if isinstance(response, dict) and 'statusCode' in response:
        logger.info("Response status: %s", response['statusCode'])
    
    return response
