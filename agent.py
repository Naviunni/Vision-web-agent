import os
from conversational_engine import ConversationalEngine
from observer import Observer
from planner import Planner
from web_navigator import WebNavigator
from vision_processor import VisionProcessor

class Agent:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            self.openai_api_key = input("Please enter your OpenAI API key: ")
            os.environ["OPENAI_API_KEY"] = self.openai_api_key

        self.vision_processor = VisionProcessor()
        self.web_navigator = WebNavigator(self.vision_processor)
        self.observer = Observer(self.vision_processor)
        self.planner = Planner(self.openai_api_key)
        self.conversational_engine = ConversationalEngine(self.openai_api_key) # Uncommented
        self.conversation_history = []

    def run(self):
        print("Hello! I am your web agent. How can I help you today?")
        
        user_goal = input("You: ")
        self.conversation_history.append({"role": "user", "content": user_goal})

        if user_goal.lower() in ["exit", "quit"]:
            print("Goodbye!")
            self.web_navigator.close()
            return

        while True:
            # 1. Take a screenshot
            screenshot_bytes = self.web_navigator.take_screenshot()

            # 2. Observe the page
            screenshot_description = self.observer.observe(screenshot_bytes)
            print(f"👀 Page observation: {screenshot_description}")

            # 3. Decide on the next action
            action = self.planner.get_next_action(self.conversation_history, screenshot_description)

            # 4. Execute the action
            response_to_user = ""
            if action["action"] == "NAVIGATE":
                self.web_navigator.navigate(action["url"])
                agent_message = f"I have navigated to {action['url']}."
                self.conversation_history.append({"role": "assistant", "content": agent_message})
                response_to_user = self.conversational_engine.get_response(self.conversation_history)

            elif action["action"] == "CLICK":
                self.web_navigator.click(action["element_description"])
                agent_message = f"I have clicked on '{action['element_description']}'."
                self.conversation_history.append({"role": "assistant", "content": agent_message})
                response_to_user = self.conversational_engine.get_response(self.conversation_history)

            elif action["action"] == "TYPE":
                self.web_navigator.type(action["text"], action["element_description"])
                agent_message = f"I have typed '{action['text']}' into '{action['element_description']}'."
                self.conversation_history.append({"role": "assistant", "content": agent_message})
                response_to_user = self.conversational_engine.get_response(self.conversation_history)

            elif action["action"] == "ASK_USER":
                # The planner explicitly asked a question, so we use it directly.
                response_to_user = action["question"]
                user_input = input(f"Agent: {response_to_user} You: ")
                self.conversation_history.append({"role": "user", "content": user_input})
                # No need for the conversational engine here, as we're directly asking.
                response_to_user = f"Understood." 

            elif action["action"] == "FINISH":
                agent_message = action["reason"]
                self.conversation_history.append({"role": "assistant", "content": agent_message})
                response_to_user = self.conversational_engine.get_response(self.conversation_history)
                print(f"Agent: {response_to_user}")
                break
            else:
                agent_message = "I'm not sure how to do that yet."
                self.conversation_history.append({"role": "assistant", "content": agent_message})
                response_to_user = self.conversational_engine.get_response(self.conversation_history)

            print(f"Agent: {response_to_user}")
            # If the response was an ASK_USER, the user's input is already added.
            if action["action"] != "ASK_USER":
                self.conversation_history.append({"role": "assistant", "content": response_to_user})

        self.web_navigator.close()

if __name__ == "__main__":
    agent = Agent()
    agent.run()
