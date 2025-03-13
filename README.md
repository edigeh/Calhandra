# LLM Interaction Component

This component provides a function to interact with Openrouter's API to call the Claude 3.5 Sonnet LLM model and generate responses based on user queries and predefined context.

## Features

- Simple Python function to call Openrouter's API
- Uses Claude 3.5 Sonnet model for high-quality responses
- Handles errors gracefully
- Easy to integrate into any chatbot backend
- Supports loading API key from .env file
- Interactive chat-like command-line interface
- Passes context as system prompt for better responses

## Requirements

- Python 3.9+
- `requests` library
- `python-dotenv` library

## Installation

1. Clone this repository or download the `llm_interaction.py` file.
2. Install the required dependencies:

```bash
pip install requests python-dotenv
```

3. Set up your Openrouter API key in one of these ways:

   a. Create a `.env` file in the same directory with the following content:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

   b. Or set it as an environment variable:
   ```bash
   # For Linux/macOS
   export OPENROUTER_API_KEY="your_api_key_here"

   # For Windows (Command Prompt)
   set OPENROUTER_API_KEY=your_api_key_here

   # For Windows (PowerShell)
   $env:OPENROUTER_API_KEY="your_api_key_here"
   ```

## Usage

### As a Module

```python
from llm_interaction import get_response

# Example usage
query = "What's the price?"
context = "What's the price?: $10\nWhat's the return policy?: 30 days"

response = get_response(query, context)
print(response)
```

### Chat Interface

You can also run the script directly to use the interactive chat interface:

```bash
python llm_interaction.py
```

This will start a chat-like session where you can ask questions and get responses based on the predefined context. The interface uses emoji and formatting to create a more engaging chat experience. Type 'quit' to exit the program.

## Function Details

The `get_response` function takes two parameters:

- `query` (str): The user's question or request
- `context` (str): The context data to use for answering the query

The function passes the context as a system prompt and the query as a user message, which helps the LLM understand the information it should use to generate responses.

It returns a string containing the LLM's response or an error message if something goes wrong.

## Error Handling

The function handles various error scenarios:

- Missing API key
- Network errors
- API request failures
- Unexpected response formats

## Security Notes

- Never hardcode your API key in the code
- Always use environment variables or a secure secrets management system
- Be mindful of the data you send to the LLM

## License

[Your License Here] 