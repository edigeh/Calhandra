#!/usr/bin/env python
import requests
import json

def send_query(query_text, api_key=None):
    """
    Send a POST request to the chatbot API with the provided query text
    
    Args:
        query_text (str): The query to send to the chatbot
        api_key (str, optional): API key for authentication
        
    Returns:
        dict: The JSON response from the API
    """
    # API endpoint
    url = "http://localhost:8000/api/chatbot"
    
    # Prepare the JSON payload
    payload = {
        "query": query_text
    }
    
    # Set up headers with API key if provided
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Send the POST request
    response = requests.post(url, json=payload, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    # You can hardcode your API key here if needed
    # api_key = "your_api_key_here"
    api_key = None
    
    # Example usage
    query = input("Enter your query: ")
    result = send_query(query, api_key)
    
    if result:
        print("\nResponse from chatbot:")
        print(json.dumps(result, indent=2))