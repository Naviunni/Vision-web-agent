import os
from observer import Observer
from planner import Planner
from web_navigator import WebNavigator
from vision_processor import VisionProcessor

class Agent:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            if os.path.exists(".openai_api_key"):
                with open(".openai_api_key", "r") as f:
                    self.openai_api_key = f.read().strip()
                os.environ["OPENAI_API_KEY"] = self.openai_api_key
            else:
                 print("Warning: OPENAI_API_KEY not set.")

        self.vision_processor = VisionProcessor()
        self.web_navigator = WebNavigator(self.vision_processor)
        self.observer = Observer(self.vision_processor)
        self.planner = Planner(self.openai_api_key)
        self.conversation_history = []

    def run(self, user_goal, socketio, user_input_event):
        self.conversation_history.append({"role": "user", "content": user_goal})
        
        screenshot_description = ""

        while True:
            screenshot_bytes = self.web_navigator.take_screenshot()
            
            if not screenshot_description:
                 screenshot_description = self.observer.observe(screenshot_bytes)

            socketio.emit('agent_observation', {'data': screenshot_description})

            action = self.planner.get_next_action(self.conversation_history, screenshot_description)

            screenshot_description = ""

            if action["action"] == "RETRY":
                print(f"🤖 Planner returned malformed JSON, retrying...")
                continue
            
            elif action["action"] == "OBSERVE":
                screenshot_description = self.observer.observe(screenshot_bytes, action["question"])
                continue

            elif action["action"] == "ASK_USER":
                question = action["question"]
                socketio.emit('request_user_input', {'question': question})
                
                user_input_event.wait()
                user_input_event.clear()
                
                from app import user_response
                
                self.conversation_history.append({"role": "assistant", "content": question})
                self.conversation_history.append({"role": "user", "content": user_response})
                continue 

            elif action["action"] == "FINISH":
                response_to_user = action["reason"]
                socketio.emit('agent_response', {'data': f"Task Complete: {response_to_user}"})
                print("✅ Task finished. Terminating agent thread.")
                return # Exit the run method to terminate the thread

            elif action["action"] == "NAVIGATE":
                self.web_navigator.navigate(action["url"])
                response_to_user = f"I have navigated to {action['url']}."

            elif action["action"] == "CLICK":
                self.web_navigator.click(action["element_description"])
                response_to_user = f"I have clicked on '{action['element_description']}'."

            elif action["action"] == "TYPE":
                self.web_navigator.type(action["text"], action["element_description"])
                response_to_user = f"I have typed '{action['text']}' into '{action['element_description']}'."
            
            elif action["action"] == "SCROLL":
                self.web_navigator.scroll(action["direction"])
                response_to_user = f"I have scrolled {action['direction']}."

            elif action["action"] == "CLEAR_INPUT":
                self.web_navigator.clear_input(action["element_description"])
                response_to_user = f"I have cleared the input field '{action['element_description']}'."

            else:
                response_to_user = "I am not sure what to do next. I will ask the user for help."
                socketio.emit('agent_response', {'data': response_to_user})
                self.conversation_history.append({"role": "assistant", "content": response_to_user})
                continue

            self.conversation_history.append({"role": "assistant", "content": response_to_user})
            socketio.emit('agent_response', {'data': response_to_user})

        # Do not close the browser so the user can see the final page
        # self.web_navigator.close()