from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain import hub
from langchain_openai import ChatOpenAI
from composio_langchain import ComposioToolSet, Action, App
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.environ.get("api_key")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

llm = ChatOpenAI()
prompt = hub.pull("hwchase17/openai-functions-agent")

composio_toolset = ComposioToolSet(api_key)
tools = composio_toolset.get_tools(actions=['GOOGLESHEETS_BATCH_GET'])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
task = "get all content ranging from 'Plan1'!A1:D6 from spreadsheet 1FS9Doruc2cIiQD7sFKNPHpx41JZJFp_dUAuc5LlyaGs"
result = agent_executor.invoke({"input": task})
print(result)