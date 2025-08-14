# teams_bot.py
import os
import sys
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.core.conversation_state import ConversationState
from botbuilder.core.memory_storage import MemoryStorage
from botbuilder.core.user_state import UserState
from botbuilder.core.bot_framework_adapter import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import ChannelAccount, Activity
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Add the agent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

# Import your agent from the agent folder
from qwen_agent import create_gemini_conversational_agent

load_dotenv()


class TeamsBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state

        # Initialize your agent
        self.agent = create_gemini_conversational_agent()

        # Store for chat history per conversation
        self.conversation_references = {}
        self.chat_histories = {}

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages from Teams"""
        try:
            user_input = turn_context.activity.text.strip()
            conversation_id = turn_context.activity.conversation.id
            user_name = turn_context.activity.from_property.name or "User"

            print(f"📨 [{user_name}]: {user_input}")

            # Initialize chat history for this conversation if not exists
            if conversation_id not in self.chat_histories:
                self.chat_histories[conversation_id] = []

            # Send typing indicator
            await turn_context.send_activity(
                MessageFactory.text("🔄 Processing your request...")
            )

            # Process with your agent
            response = self.agent.invoke({
                "input": user_input,
                "chat_history": self.chat_histories[conversation_id]
            })

            # Update chat history
            self.chat_histories[conversation_id].append(HumanMessage(content=user_input))
            self.chat_histories[conversation_id].append(AIMessage(content=response['output']))

            # Format response for Teams
            bot_response = f"✅ {response['output']}"

            # Send response back to Teams
            await turn_context.send_activity(MessageFactory.text(bot_response))

            print(f"🤖 [Bot]: {response['output']}")

        except Exception as e:
            error_message = f"❌ Sorry, an error occurred: {str(e)}"
            await turn_context.send_activity(MessageFactory.text(error_message))
            print(f"❌ [Error]: {str(e)}")

    async def on_members_added_activity(self, members_added: list, turn_context: TurnContext):
        """Greet new members when they join the conversation"""
        welcome_text = """👋 **Hello! I'm your Database Assistant Bot!**

I can help you with database operations. Here are some things you can ask me:

• **Transfer tables**: `transfer dbo.DB_EVENTS from dw_production to TempObjDB`
• **Get current time**: `what time is it?`
• **Say hello**: `say hello to John`

Just type your request in natural language and I'll help you out! 🚀"""

        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))


def create_app():
    # Bot Framework settings
    settings = BotFrameworkAdapterSettings(
        app_id=os.environ.get("MicrosoftAppId", ""),
        app_password=os.environ.get("MicrosoftAppPassword", "")
    )

    # Create adapter
    adapter = BotFrameworkAdapter(settings)

    # Create conversation and user state with memory storage
    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)

    # Create bot instance
    bot = TeamsBot(conversation_state, user_state)

    # Error handler
    async def on_error(context: TurnContext, error: Exception):
        print(f"❌ Error: {error}")
        try:
            await context.send_activity(
                MessageFactory.text("❌ Sorry, an error occurred while processing your request.")
            )
        except:
            pass

    adapter.on_turn_error = on_error

    # Define the main messaging endpoint
    async def messages(req: Request) -> Response:
        """Handle incoming messages from Teams"""
        if "application/json" not in req.headers.get("Content-Type", ""):
            return Response(status=415)

        try:
            body = await req.json()
            activity = Activity().deserialize(body)
            auth_header = req.headers.get("Authorization", "")

            response = await adapter.process_activity(activity, auth_header, bot.on_turn)

            if response:
                return json_response(data=response.body, status=response.status)
            return Response(status=201)

        except Exception as e:
            print(f"❌ Error processing activity: {e}")
            return Response(status=500)

    # Health check endpoint
    async def health_check(req: Request) -> Response:
        return json_response({"status": "healthy", "message": "Bot is running!"})

    # Create web application
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)

    return app


def main():
    """Main function to start the bot - NO async here"""
    print("🤖 Starting Database Agent Bot for Microsoft Teams...")
    print("=" * 60)

    # Get port from environment variable or default
    port = int(os.environ.get("PORT", 3978))
    host = "0.0.0.0"

    print(f"🌐 Bot available at: http://{host}:{port}")
    print(f"📋 Endpoints:")
    print(f"   • Messages: http://{host}:{port}/api/messages")
    print(f"   • Health:   http://{host}:{port}/health")
    print("=" * 60)

    try:
        app = create_app()
        web.run_app(app, host=host, port=port)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    main()  # Call main() directly, not asyncio.run(main())