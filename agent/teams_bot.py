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

# Import your agent (now in the same directory)
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

            # Send typing indicator to show bot is working
            typing_activity = MessageFactory.text("🔄 Processing your request...")
            typing_activity.type = "typing"
            await turn_context.send_activity(typing_activity)

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

Just type your request in natural language and I'll help you out! 🚀

**Example database transfer command:**
```
transfer dbo.DB_EVENTS from dw_production to TempObjDB
```"""

        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def on_turn(self, turn_context: TurnContext):
        """Called on every turn of the conversation"""
        await super().on_turn(turn_context)

        # Save conversation state
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)


# Create the bot adapter and web app
async def create_app():
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
                MessageFactory.text("❌ Sorry, an error occurred while processing your request."))
        except:
            pass  # If we can't send the error message, just log it

    adapter.on_turn_error = on_error

    # Define the main messaging endpoint
    async def messages(req: Request) -> Response:
        """Handle incoming messages from Teams"""
        # Verify content type
        content_type = req.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return Response(status=415, text="Unsupported Media Type - Expected application/json")

        try:
            # Parse the request body
            body = await req.json()
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
            return Response(status=400, text="Invalid JSON in request body")

        # Deserialize the activity
        try:
            activity = Activity().deserialize(body)
        except Exception as e:
            print(f"❌ Error deserializing activity: {e}")
            return Response(status=400, text="Invalid activity format")

        # Get authorization header
        auth_header = req.headers.get("Authorization", "")

        try:
            # Process the activity
            response = await adapter.process_activity(activity, auth_header, bot.on_turn)

            if response:
                return json_response(data=response.body, status=response.status)
            return Response(status=201)

        except Exception as e:
            print(f"❌ Error processing activity: {e}")
            return Response(status=500, text=f"Error processing activity: {str(e)}")

    # Health check endpoint
    async def health_check(req: Request) -> Response:
        """Health check endpoint to verify bot is running"""
        return json_response({
            "status": "healthy",
            "message": "DB Agent Bot is running!",
            "endpoints": {
                "messages": "/api/messages",
                "health": "/health"
            }
        })

    # Root endpoint with bot info
    async def root_info(req: Request) -> Response:
        """Root endpoint with bot information"""
        return json_response({
            "name": "Database Agent Bot",
            "description": "AI-powered bot for database operations",
            "version": "1.0.0",
            "capabilities": [
                "Database table transfers",
                "Time queries",
                "Greeting functionality"
            ],
            "endpoints": {
                "messages": "/api/messages",
                "health": "/health"
            }
        })

    # Create web application
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    app.router.add_get("/", root_info)

    return app


def main():
    """Main function to start the bot"""
    print("🤖 Starting Database Agent Bot for Microsoft Teams...")
    print("=" * 60)
    print(f"🌐 Bot will be available at: http://localhost:3978")
    print(f"📋 Endpoints:")
    print(f"   • Messages: http://localhost:3978/api/messages")
    print(f"   • Health:   http://localhost:3978/health")
    print("=" * 60)
    print("🔧 For external access, use localtunnel:")
    print("   lt --port 3978")
    print("=" * 60)

    try:
        app = create_app()
        web.run_app(app, host="localhost", port=3978)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()