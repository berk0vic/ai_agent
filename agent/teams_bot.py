# teams_bot.py
import os
import sys
import traceback
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.core.conversation_state import ConversationState
from botbuilder.core.memory_storage import MemoryStorage
from botbuilder.core.user_state import UserState
from botbuilder.core.bot_framework_adapter import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Add the agent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

from qwen_agent import create_gemini_conversational_agent

load_dotenv()

print(f"MicrosoftAppId from .env: {os.environ.get('MicrosoftAppId')}")
print(f"MicrosoftAppPassword from .env: {os.environ.get('MicrosoftAppPassword')}")

class TeamsBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.agent = None  # Lazy load
        self.conversation_references = {}
        self.chat_histories = {}

    async def on_message_activity(self, turn_context: TurnContext):
        try:
            if self.agent is None:
                print("🚀 Initializing agent for the first time...")
                self.agent = create_gemini_conversational_agent()

            user_input = (turn_context.activity.text or "").strip()
            conversation_id = turn_context.activity.conversation.id
            user_name = getattr(turn_context.activity.from_property, "name", "User")

            print(f"📨 [{user_name}]: {user_input}")

            if conversation_id not in self.chat_histories:
                self.chat_histories[conversation_id] = []

            await turn_context.send_activity(
                MessageFactory.text("🔄 Processing your request...")
            )

            response = self.agent.invoke({
                "input": user_input,
                "chat_history": self.chat_histories[conversation_id]
            })

            self.chat_histories[conversation_id].append(HumanMessage(content=user_input))
            self.chat_histories[conversation_id].append(AIMessage(content=response['output']))

            bot_response = f"✅ {response['output']}"
            await turn_context.send_activity(MessageFactory.text(bot_response))

            print(f"🤖 [Bot]: {response['output']}")

        except Exception as e:
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"❌ Sorry, an error occurred: {e}"))

    async def on_members_added_activity(self, members_added: list, turn_context: TurnContext):
        try:
            welcome_text = """👋 **Hello! I'm your Database Assistant Bot!**"""

            for member in members_added:
                if member.id != turn_context.activity.recipient.id:
                    name = getattr(member, "name", "User")
                    print(f"✅ Sending welcome message to new member: {name}")
                    await turn_context.send_activity(MessageFactory.text(welcome_text))

        except Exception as e:
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"❌ Welcome error: {e}"))

    async def on_conversation_update_activity(self, turn_context: TurnContext):
        try:
            print("ℹ️ Conversation update event received")
            await super().on_conversation_update_activity(turn_context)
        except Exception as e:
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"❌ conversationUpdate error: {e}"))

    async def on_installation_update_activity(self, turn_context: TurnContext):
        try:
            print("ℹ️ Installation update event received")
            await turn_context.send_activity("📦 Installation update received.")
        except Exception as e:
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"❌ installationUpdate error: {e}"))


def create_app():
    settings = BotFrameworkAdapterSettings("", "")


    print(f"App ID: {settings.app_id}, App Password loaded: {bool(settings.app_password)}")

    adapter = BotFrameworkAdapter(settings)

    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)

    bot = TeamsBot(conversation_state, user_state)

    async def on_error(context: TurnContext, error: Exception):
        traceback.print_exc()
        print(f"❌ Error: {error}")
        try:
            await context.send_activity(
                MessageFactory.text("❌ Sorry, an error occurred while processing your request.")
            )
        except:
            pass

    adapter.on_turn_error = on_error

    async def messages(req: Request) -> Response:
        # DEBUG: Gelen header ve body
        print("📥 Headers:", dict(req.headers))
        raw_body = await req.text()
        print("📥 Body raw:", raw_body)
        req._read_bytes = raw_body.encode()  # Body'yi yeniden okunabilir yap

        if "application/json" not in req.headers.get("Content-Type", ""):
            return Response(status=415)
        try:
            body = await req.json()
            activity = Activity().deserialize(body)
            auth_header = req.headers.get("Authorization", "")

            if auth_header:
                print("✅ Authorization header geldi!")
            else:
                print("❌ Authorization header GELMEDİ!")

            response = await adapter.process_activity(activity, auth_header, bot.on_turn)
            if response:
                return json_response(data=response.body, status=response.status)
            return Response(status=201)

        except Exception as e:
            traceback.print_exc()
            print(f"❌ Error processing activity: {e}")
            return Response(status=500)

    async def health_check(req: Request) -> Response:
        return json_response({"status": "healthy", "message": "Bot is running!"})

    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    return app



def main():
    print("🤖 Starting Database Agent Bot for Microsoft Teams...")
    print("=" * 60)
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
        traceback.print_exc()
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    main()
