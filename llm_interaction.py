from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import importlib.util
import io
import contextlib
import warnings
import atexit
import logging
import asyncio
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Define the request model for the API
class QueryRequest(BaseModel):
    query: str

# Configure logging
log_filename = f"warnings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.WARNING, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Redirect warnings to log file
def handle_warning(message, category, filename, lineno, file=None, line=None):
    logging.warning(f"{category.__name__}: {message}")

# Set the warning filter to redirect warnings
warnings.showwarning = handle_warning

# Function to close the log file when the program exits
def cleanup():
    logging.shutdown()
    # Check if the log file is empty (no warnings)
    if os.path.exists(log_filename) and os.path.getsize(log_filename) == 0:
        os.remove(log_filename)  # Remove empty log file

# Register the cleanup function to run at exit
atexit.register(cleanup)

load_dotenv()

api_key = os.environ.get("OPENROUTER_API_KEY")

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=api_key,
)

# Initialize the FastAPI app with CORS support
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Maximum number of exchanges to keep in memory (to avoid token limits)
# 4 means 4 pairs of messages (4 user messages + 4 assistant responses = 8 total messages)
MAX_HISTORY_LENGTH = 3  # Reduced to optimize token usage

# Define the system prompt (optimized to be more concise)
system_prompt = """You are a helpful assistant that answers user questions in Portuguese. You have access to a table containing information about available properties, with columns: IMOVEL (property name or description), STATUS (all 'LIVRE'), ENDEREÇO (address), and DESCRIÇÃO (brief description).

For questions about these properties, use the table to provide accurate information. Handle queries such as:

Location-based: Filter by ENDEREÇO and list properties with their descriptions.
Specific property: Provide the address, status, and description.
Characteristic-based: Search DESCRIÇÃO for relevant keywords and list matching properties.
If the user asks a question that requires information about properties, disponibility, address, or any data that would typically be found in a database or spreadsheet, respond with "NEED_DATA" at the very beginning of your message followed by your normal response.

When using the table, incorporate the information naturally as if you already knew it, without mentioning its source.

Use your best judgment to determine if the question can be answered with the property table or if additional data is needed based on the context and nature of the question."""

# Thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=2)

def add_to_history(history, role, content):
    """Add a new message to the conversation history"""
    history.append({"role": role, "content": content})
    return history

def run_langchain_tool():
    """Execute the correct_langchain.py script and return its output"""
    try:
        # Capture stdout to get the output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Load the correct_langchain.py module dynamically
        spec = importlib.util.spec_from_file_location("correct_langchain", "./correct_langchain.py")
        langchain_module = importlib.util.module_from_spec(spec)
        
        # Redirect stdout and stderr to our capture buffers and execute the module
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            # Use a context manager to suppress warnings to console
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Don't show warnings in terminal
                spec.loader.exec_module(langchain_module)
        
        # Log any stderr output to the warnings log
        stderr_content = stderr_capture.getvalue()
        if stderr_content.strip():
            logging.warning(f"Stderr from langchain tool: {stderr_content}")
        
        # Return the captured output
        return stdout_capture.getvalue()
    except Exception as e:
        error_msg = f"Error executing langchain tool: {str(e)}"
        logging.error(error_msg)
        return error_msg

def prefetch_data():
    """Prefetch data in a separate thread to have it ready if needed"""
    try:
        return run_langchain_tool()
    except Exception as e:
        logging.error(f"Error prefetching data: {str(e)}")
        return f"Error prefetching data: {str(e)}"

async def process_stream(stream, messages):
    """Process a streaming response and return the complete message without printing"""
    full_response = ""
    need_data_detected = False
    buffer = ""  # Buffer to hold potential fragments of NEED_DATA
    
    for chunk in stream:
        delta = chunk.choices[0].delta
        
        # If there's no content in this chunk, skip
        if not hasattr(delta, "content") or delta.content is None:
            continue
            
        content = delta.content
        full_response += content
        
        # Check if we need to inject data
        if "NEED_DATA" in full_response:
            need_data_detected = True
            # Break the loop to fetch data
            break
            
        buffer += content
    
    # If we detected a need for data, make a new request with the data included
    if need_data_detected:
        # Fetch the data
        data = run_langchain_tool()
        
        # Extract the original user query from the messages
        original_query = messages[-1]["content"]
        
        # Create a new message that includes both the query and the data
        enhanced_query = f"""Original question: {original_query}
        
Here is the data you requested:
{data}

Please use this data to provide a complete response to the original question. DO NOT include the phrase "NEED_DATA" in your response."""
        
        # Make a new request with the enhanced query
        new_messages = messages.copy()
        new_messages[-1]["content"] = enhanced_query
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            new_stream = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001",
                messages=new_messages,
                stream=True
            )
            
            # Stream the new response and get the full text
            new_full_response = ""
            for chunk in new_stream:
                delta = chunk.choices[0].delta
                
                if not hasattr(delta, "content") or delta.content is None:
                    continue
                    
                content = delta.content
                new_full_response += content
                
            full_response = new_full_response  # Use the new response
    
    # Clean up response if needed - remove any NEED_DATA that might still be present
    full_response = full_response.replace("NEED_DATA", "").strip()
        
    return full_response

def stream_to_console(stream, needs_data=False, data=None):
    """Process a streaming response and print tokens as they arrive"""
    full_response = ""
    current_display = ""  # Track what's been displayed to the user
    chunks_received = 0
    data_injected = False
    start_time = time.time()
    need_data_detected = False
    buffer = ""  # Buffer to hold potential fragments of NEED_DATA
    
    print("\nAssistant:", end="", flush=True)
    for chunk in stream:
        delta = chunk.choices[0].delta
        
        # If there's no content in this chunk, skip
        if not hasattr(delta, "content") or delta.content is None:
            continue
            
        content = delta.content
        full_response += content
        
        # Check if we need to inject data
        if not data_injected and "NEED_DATA" in full_response:
            need_data_detected = True
            # Silently fetch data if not prefetched
            if data is None:
                try:
                    data = run_langchain_tool()
                except Exception as e:
                    logging.error(f"Error fetching data: {str(e)}")
                    data = f"Error fetching data: {str(e)}"
            
            # Stop processing this stream - we'll make a new request with the data
            break
            
        elif not need_data_detected:
            # Add the current content to our buffer
            buffer += content
            
            # Check if the buffer contains NEED_DATA
            if "NEED_DATA" in buffer:
                # Only print the part after NEED_DATA if any
                filtered_buffer = buffer.replace("NEED_DATA", "")
                # Clear the buffer after filtering
                buffer = ""
                if filtered_buffer:
                    print(filtered_buffer, end="", flush=True)
                    current_display += filtered_buffer
            # If buffer doesn't contain NEED_DATA and is not a potential fragment
            elif not any(fragment in "NEED_DATA" for fragment in [buffer[-i:] for i in range(1, min(9, len(buffer) + 1))]):
                # Print the buffer and clear it
                print(buffer, end="", flush=True)
                current_display += buffer
                buffer = ""
            # Otherwise, keep the buffer for now (it might be a fragment of NEED_DATA)
            
        chunks_received += 1
    
    # If we've buffered content and didn't detect NEED_DATA, print it
    if buffer and not need_data_detected:
        print(buffer, end="", flush=True)
        current_display += buffer
    
    # If we detected a need for data, make a new request with the data included
    if need_data_detected and data:
        # Quietly replace the current line without drawing attention to the process
        print("\r\033[K\nAssistant:", end="", flush=True)
        current_display = ""  # Reset what's been displayed
        
        # Extract the original user query from the messages
        original_query = messages[-1]["content"]
        
        # Create a new message that includes both the query and the data
        enhanced_query = f"""Original question: {original_query}
        
Here is the data you requested:
{data}

Please use this data to provide a complete response to the original question. DO NOT include the phrase "NEED_DATA" in your response."""
        
        # Make a new request with the enhanced query
        new_messages = messages.copy()
        new_messages[-1]["content"] = enhanced_query
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            new_stream = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001",
                messages=new_messages,
                stream=True
            )
            
            # Stream the new response and get the full text
            new_full_response = ""
            for chunk in new_stream:
                delta = chunk.choices[0].delta
                
                if not hasattr(delta, "content") or delta.content is None:
                    continue
                    
                content = delta.content
                new_full_response += content
                
                # Make sure we're not displaying NEED_DATA (shouldn't happen, but just to be safe)
                filtered_content = content.replace("NEED_DATA", "")
                print(filtered_content, end="", flush=True)
                current_display += filtered_content
                
            full_response = new_full_response  # Use the new response
    
    print()  # New line after response
    elapsed = time.time() - start_time
    logging.info(f"Response completed in {elapsed:.2f} seconds")
    
    # Clean up response if needed - remove any NEED_DATA that might still be present
    full_response = full_response.replace("NEED_DATA", "").strip()
        
    return full_response

# API endpoint for chatbot
@app.post("/api/chatbot")
async def chatbot(request: QueryRequest):
    try:
        # Create message with system prompt and user query
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.query}
        ]
        
        # Make LLM call with streaming enabled
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stream = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001",
                messages=messages,
                stream=True
            )
            
            # Process the stream and get the response
            response = await process_stream(stream, messages)
        
        # Create JSON response with ensure_ascii=False to properly handle non-ASCII characters
        json_response = json.dumps({"response": response}, ensure_ascii=False)
        
        # Return a custom Response with the proper content type
        return Response(
            content=json_response,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        logging.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def main():
    # Initialize an empty in-memory conversation history for this session
    conversation_history = []
    global messages  # Make messages global so stream_to_console can access it
    
    print("Chat session started. Type 'exit', 'quit', or 'bye' to end the conversation.")
    print("Type 'clear' to clear the conversation history within this session.")
    print("---------------------------------------------------------------------")
    
    # Continuous chat loop
    chat_active = True
    while chat_active:
        # Get user input
        if len(sys.argv) > 1 and sys.argv[1].lower() != "--clear-history":
            # If arguments were provided, use them for the first iteration only
            user_query = ' '.join(sys.argv[1:])
            # Clear argv after first use to prevent reusing in subsequent iterations
            sys.argv = [sys.argv[0]]
        else:
            user_query = input("\nYou: ")
        
        # Check for exit commands
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("\nEnding chat session. Goodbye!")
            chat_active = False
            continue
            
        # Check for clear history command
        if user_query.lower() == 'clear':
            conversation_history = []
            print("\nConversation history cleared for this session.")
            continue
        
        # Add user's new query to history
        conversation_history = add_to_history(conversation_history, "user", user_query)
        
        # Prepare messages with conversation history
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add relevant conversation history, but only include up to MAX_HISTORY_LENGTH recent exchanges
        if len(conversation_history) > 1:  # If there's history beyond the current query
            # Calculate start index to get at most the last MAX_HISTORY_LENGTH exchanges
            start_idx = max(0, len(conversation_history) - 1 - (MAX_HISTORY_LENGTH * 2))
            messages.extend(conversation_history[start_idx:-1])  # All except current query
        
        # Add current user query
        messages.append({"role": "user", "content": user_query})
        
        # Make LLM call with streaming enabled - let the LLM decide if it needs data
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stream = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001",
                messages=messages,
                stream=True  # Enable streaming
            )
            
            # Stream the response to console and get the full response
            # We pass None for data - it will be fetched on-demand if needed
            assistant_response = stream_to_console(stream, False, None)
        
        # Add the assistant's response to history
        conversation_history = add_to_history(conversation_history, "assistant", assistant_response)
        
        # Trim history if needed to maintain the MAX_HISTORY_LENGTH limit
        if len(conversation_history) > MAX_HISTORY_LENGTH * 2:
            # Keep only the most recent exchanges
            conversation_history = conversation_history[-(MAX_HISTORY_LENGTH * 2):]

if __name__ == "__main__":
    # Check if the user wants to run the API server
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--api":
        import uvicorn
        # Get the port from the environment (for Heroku compatibility)
        port = int(os.environ.get("PORT", 8000))
        print(f"Starting API server on http://0.0.0.0:{port}")
        print("Use the endpoint /api/chatbot for chatbot interactions")
        # Configure the uvicorn server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            log_level="info"
        )
    # Check if the user wants to clear the conversation history
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "--clear-history":
        print("No persistent history to clear - memory is now session-specific.")
    else:
        main()
