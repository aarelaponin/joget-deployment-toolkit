#!/usr/bin/env python3
"""
Test script for the Form Creator API plugin.

Tests the plugin endpoint: /api/formcreator/formcreator/forms
"""

import json
from joget_deployment_toolkit import JogetClient

# Load form definition
with open('examples/x1_form.json', 'r') as f:
    form_definition = json.load(f)

# API credentials for the plugin
API_ID = "API-4e39106c-67b1-4155-8c80-2f5ed6d1aae5"
API_KEY = "b2cc0157ab464ff5b1f07a5907ef9690"

# Create client from instance config
client = JogetClient.from_instance('jdx4')

# Extract form metadata from the form definition
form_id = form_definition['properties']['id']
form_name = form_definition['properties']['name']
table_name = form_definition['properties'].get('tableName', form_id)

# Build the request payload expected by the plugin
# Field names from ApiConstants.RequestFields:
#   FORM_ID = "formId"
#   FORM_NAME = "formName"
#   TABLE_NAME = "tableName"
#   FORM_DEFINITION = "formDefinition"  (JSON string, not formDefinitionJson)
request_payload = {
    "formId": form_id,
    "formName": form_name,
    "tableName": table_name,
    "formDefinition": json.dumps(form_definition),  # Must be a JSON string
    # Note: targetAppId/targetAppVersion are optional
    # If not specified, the plugin should use some default or the app context
    "createApiEndpoint": False,
    "createCrud": False
}

# Send form definition to plugin API
print(f"Sending form creation request to plugin API...")
print(f"Endpoint: /api/formcreator/formcreator/forms")
print(f"API ID: {API_ID}")
print(f"Form ID: {form_id}")
print(f"Form Name: {form_name}")
print(f"Table Name: {table_name}")
print()

try:
    response = client.post(
        endpoint="/api/formcreator/formcreator/forms",
        json=request_payload,
        api_id=API_ID,
        api_key=API_KEY
    )

    print("Response:")
    print(json.dumps(response, indent=2))

except Exception as e:
    print(f"Error: {e}")
