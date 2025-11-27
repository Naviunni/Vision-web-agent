import os
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
            if action["action"] == "NAVIGATE":
                self.web_navigator.navigate(action["url"])
                response = f"I have navigated to {action['url']}."
            elif action["action"] == "CLICK":
                self.web_navigator.click(action["element_description"])
                response = f"I have clicked on '{action['element_description']}'."
            elif action["action"] == "TYPE":
                self.web_navigator.type(action["text"], action["element_description"])
                response = f"I have typed '{action['text']}' into '{action['element_description']}'."
            elif action["action"] == "ASK_USER":
                user_input = input(f"Agent: {action['question']} You: ")
                self.conversation_history.append({"role": "user", "content": user_input})
                response = f"Understood."
            elif action["action"] == "FINISH":
                response = action["reason"]
                print(f"Agent: {response}")
                break
            else:
                response = "I'm not sure how to do that yet."

            print(f"Agent: {response}")
            self.conversation_history.append({"role": "assistant", "content": response})

        self.web_navigator.close()

if __name__ == "__main__":
    agent = Agent()
    agent.run()