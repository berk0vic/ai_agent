import os
import google.generativeai as genai
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Import your custom tools
from tools import get_current_time, say_hello, transfer_table_data

# Load environment variables from the .env file
load_dotenv()
def create_gemini_conversational_agent():
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

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
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # Better for structured inputs
        verbose=True
    )
    return agent
