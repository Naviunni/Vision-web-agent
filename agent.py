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
            # 1. Take a screenshot and observe the page
            screenshot_bytes = self.web_navigator.take_screenshot()
            screenshot_description = self.observer.observe(screenshot_bytes)
            print(f"👀 Page observation: {screenshot_description}")

            # 2. Decide on the next action
            action = self.planner.get_next_action(self.conversation_history, screenshot_description)

            # 3. Execute the action and generate a factual response
            response_to_user = ""
            if action["action"] == "ASK_USER":
                response_to_user = action["question"]
                print(f"Agent: {response_to_user}")
                user_input = input(f"You: ")
                self.conversation_history.append({"role": "assistant", "content": response_to_user})
                self.conversation_history.append({"role": "user", "content": user_input})
                continue 

            elif action["action"] == "FINISH":
                response_to_user = action["reason"]
                print(f"Agent: {response_to_user}")
                break

            elif action["action"] == "NAVIGATE":
                self.web_navigator.navigate(action["url"])
                response_to_user = f"I have navigated to {action['url']}."

            elif action["action"] == "CLICK":
                self.web_navigator.click(action["element_description"])
                response_to_user = f"I have clicked on '{action['element_description']}'."

            elif action["action"] == "TYPE":
                self.web_navigator.type(action["text"], action["element_description"])
                response_to_user = f"I have typed '{action['text']}' into '{action['element_description']}'."
            
            else:
                response_to_user = "I am not sure what to do next. I will ask the user for help."
                print(f"Agent: {response_to_user}")
                self.conversation_history.append({"role": "assistant", "content": response_to_user})
                continue

            # 4. Add the factual response to the history and print it
            self.conversation_history.append({"role": "assistant", "content": response_to_user})
            print(f"Agent: {response_to_user}")


        self.web_navigator.close()

if __name__ == "__main__":
    agent = Agent()
    agent.run()
