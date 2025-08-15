import os
import sys

# We no longer need google.generativeai or ChatGoogleGenerativeAI for Qwen
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_openai import ChatOpenAI  # Use ChatOpenAI for Qwen's API
from dotenv import load_dotenv
sys.path.append(os.path.dirname(__file__))

# Import your custom tools
from tools import get_current_time, say_hello, transfer_table_data

# Load environment variables from the .env file
load_dotenv()

def create_gemini_conversational_agent():
    # Configure the LLM to use your local Qwen model
    # The Qwen API endpoint you provided is compatible with OpenAI's API format.
    llm = ChatOpenAI(
        model_name="Qwen/Qwen3-30B-A3B",
        openai_api_base="http://192.168.7.22:81/v1",
        # A placeholder key is required by LangChain, but may not be used by your local server
        openai_api_key="sk-your-key", 
        temperature=0.7
    )

    tools = [
        Tool(name="get_current_time", func=get_current_time, description="Returns the current time."),
        Tool(name="say_hello", func=say_hello, description="Greets a person."),
        Tool(
            name="transfer_table_data",
            func=transfer_table_data,
            description="Transfers a full table from one SQL database to another. Input should be in format: 'transfer [schema].[table] from [source_db] to [dest_db]'. Example: 'transfer dbo.DB_EVENTS from dw_production to TempObjDB'"
        ),
    ]

    # This configuration is designed to work with the conversational loop in your main.py
    # It will automatically manage the agent's internal state correctly.
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    return agent
