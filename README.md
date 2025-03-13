# LLM Interaction Component

This component provides functionality to interact with AI language models through OpenRouter's API, primarily using Gemini and other models. It includes features for generating responses based on user queries and integrates with LangChain for additional capabilities.

## Features

- Python-based interface to call OpenRouter's API
- Support for Google's Gemini model
- Streaming responses for better user experience
- LangChain integration for advanced functionality including Google Sheets access
- Handles errors gracefully with comprehensive logging
- Easy to integrate into any chatbot backend
- Supports loading API keys from .env file
- Interactive chat-like command-line interface
- Dynamic data fetching when requested by the model ("NEED_DATA" pattern)
- Warning logging to separate log files

## Requirements

- Python 3.9+
- Libraries:
  - `openai` - For API interaction
  - `python-dotenv` - For environment variable management
  - `langchain` - For advanced AI agent capabilities
  - `langchain_openai` - For OpenAI integration with LangChain
  - `composio_langchain` - For Composio tool integration

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install openai python-dotenv langchain langchain_openai composio_langchain
```

3. Set up your API keys in a `.env` file in the same directory with the following content:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   api_key=your_composio_api_key_here
   ```

## Usage

### Interactive Chat Interface

You can run the script directly to use the interactive chat interface:

```bash
python llm_interaction.py
```

This will start a chat-like session where you can ask questions and get responses. The interface uses streaming to show responses as they're generated. Type 'exit', 'quit', or 'bye' to end the conversation.

### Running With Initial Query

You can also provide an initial query as a command-line argument:

```bash
python llm_interaction.py "What's the weather like today?"
```

### Special Commands

- `exit`, `quit`, `bye`: End the chat session
- `clear`: Clear the conversation history for the current session

## Key Components

### Main LLM Interaction (llm_interaction.py)

The main file handles:
- Setting up API client configuration
- Managing conversation history
- Streaming responses to the console
- Dynamic data fetching when required by the model
- Warning and error logging

### LangChain Integration (correct_langchain.py)

This component provides:
- Integration with LangChain for advanced AI capabilities
- Ability to access Google Sheets data
- Example implementation showing how to create and execute an agent

## Advanced Features

### Dynamic Data Fetching

The system can detect when the model needs additional data (indicated by "NEED_DATA" in the response) and will:
1. Pause the current response stream
2. Fetch the required data from the LangChain component
3. Create a new enhanced query including the data
4. Generate a complete response incorporating the fetched data

### Warning Management

The system includes sophisticated warning handling that:
- Redirects warnings to timestamped log files
- Automatically removes empty log files
- Prevents warnings from cluttering the console output

## Security Notes

- Never hardcode your API keys in the code
- Always use environment variables or a secure secrets management system
- Be mindful of the data you send to the LLM

## License

[Your License Here] 