#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify GatewayAPI webhook configuration.
This script checks:
1. If the JWT secret is configured in Odoo
2. If the webhook URL is properly configured
3. Simulates a webhook call to test the endpoint

Usage:
    python3 test_webhook_config.py
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_odoo_config():
    """Get Odoo configuration from environment variables."""
    odoo_url = os.getenv('ODOO_URL', 'http://localhost:8069')
    odoo_db = os.getenv('ODOO_DB', '')
    odoo_user = os.getenv('ODOO_USER', 'admin')
    odoo_password = os.getenv('ODOO_PASSWORD', 'admin')
    
    if not odoo_db:
        logger.error("ODOO_DB environment variable not set")
        sys.exit(1)
    
    return {
        'url': odoo_url,
        'db': odoo_db,
        'username': odoo_user,
        'password': odoo_password
    }

def check_jwt_secret(config):
    """Check if JWT secret is configured in Odoo."""
    try:
        # Authenticate with Odoo
        session = requests.Session()
        auth_url = f"{config['url']}/web/session/authenticate"
        auth_data = {
            'jsonrpc': '2.0',
            'params': {
                'db': config['db'],
                'login': config['username'],
                'password': config['password']
            }
        }
        response = session.post(auth_url, json=auth_data)
        response.raise_for_status()
        
        # Get JWT secret from system parameters
        search_url = f"{config['url']}/web/dataset/search_read"
        search_data = {
            'jsonrpc': '2.0',
            'params': {
                'model': 'ir.config_parameter',
                'domain': [('key', '=', 'gatewayapi.webhook_jwt_secret')],
                'fields': ['key', 'value']
            }
        }
        response = session.post(search_url, json=search_data)
        response.raise_for_status()
        result = response.json()
        
        if result.get('result'):
            secret = result['result'][0]['value']
            if secret:
                logger.info("✅ JWT secret is configured")
                return secret
            else:
                logger.error("❌ JWT secret is empty")
        else:
            logger.error("❌ JWT secret not found in system parameters")
        
    except Exception as e:
        logger.error(f"Error checking JWT secret: {str(e)}")
    
    return None

def test_webhook_endpoint(config, jwt_secret):
    """Test the webhook endpoint with a simulated DLR."""
    if not jwt_secret:
        logger.error("Cannot test webhook without JWT secret")
        return
    
    try:
        # Create a test JWT token
        payload = {
            'iat': datetime.utcnow().timestamp(),
            'exp': datetime.utcnow().timestamp() + 3600,  # 1 hour expiry
            'iss': 'gatewayapi'
        }
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        
        # Prepare test DLR data
        dlr_data = {
            'id': '8001907829504',  # Example message ID
            'status': 'DELIVERED',
            'msisdn': '+4712345678',
            'time': datetime.utcnow().isoformat(),
            'userref': 'test-uuid'
        }
        
        # Send test webhook
        webhook_url = f"{config['url']}/gatewayapi/dlr"
        headers = {
            'Content-Type': 'application/json',
            'X-Gwapi-Signature': token
        }
        
        logger.info(f"Sending test webhook to {webhook_url}")
        response = requests.post(webhook_url, json=dlr_data, headers=headers)
        
        if response.status_code == 200:
            logger.info("✅ Webhook test successful")
            logger.info(f"Response: {response.json()}")
        else:
            logger.error(f"❌ Webhook test failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error testing webhook: {str(e)}")

def main():
    """Main function to run the tests."""
    logger.info("Starting GatewayAPI webhook configuration test")
    
    # Get Odoo configuration
    config = get_odoo_config()
    logger.info(f"Testing against Odoo instance: {config['url']}")
    
    # Check JWT secret
    jwt_secret = check_jwt_secret(config)
    
    # Test webhook endpoint
    if jwt_secret:
        test_webhook_endpoint(config, jwt_secret)
    
    logger.info("Test completed")

if __name__ == '__main__':
    main() 