import os
import sys
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# The following import assumes you're running the script from the project root.
# It uses the absolute path to ensure the import works correctly.
sys.path.append(os.path.abspath('src'))
from agent.qwen_agent import create_gemini_conversational_agent


def main():
    print("Welcome to the Agent Console! Type 'exit' to quit.")
    print("======================================")

    agent = create_gemini_conversational_agent()
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break

        try:
            # Pass both the user input and the chat history
            response = agent.invoke({"input": user_input, "chat_history": chat_history})

            # Update the chat history for the next turn
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=response['output']))

            print(f"Agent: {response['output']}")

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
