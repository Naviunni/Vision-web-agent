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

    def reset(self):
        self.conversation_history = []

    def run(self, user_goal, socketio, shared_state):
        self.conversation_history.append({"role": "user", "content": user_goal})
        
        screenshot_description = ""
        user_input_event = shared_state["user_input_event"]
        retry_count = 0
        max_retries = 3

        while True:
            screenshot_bytes = self.web_navigator.take_screenshot()
            
            if not screenshot_description:
                 screenshot_description = self.observer.observe(screenshot_bytes)

            socketio.emit('agent_observation', {'data': screenshot_description})

            action = self.planner.get_next_action(self.conversation_history, screenshot_description)

            screenshot_description = ""
            action_failed = False
            failure_reason = ""
            response_to_user = ""

            if action["action"] == "RETRY":
                retry_count += 1
                if retry_count >= max_retries:
                    question = "I'm having trouble. Can you please guide me?"
                    socketio.emit('request_user_input', {'question': question})
                    user_input_event.wait()
                    user_input_event.clear()
                    user_response = shared_state["user_response"]
                    self.conversation_history.append({"role": "assistant", "content": question})
                    self.conversation_history.append({"role": "user", "content": user_response})
                    retry_count = 0 
                else:
                    print(f"🤖 Planner returned malformed JSON, retrying ({retry_count}/{max_retries})...")
                continue
            
            retry_count = 0 

            if action["action"] == "OBSERVE":
                screenshot_description = self.observer.observe(screenshot_bytes, action.get("question"))
                continue

            elif action["action"] == "SUMMARIZE_OPTIONS":
                summary_message = f"I found a few options for {action.get('topic', 'your item')}:\n"
                for i, option in enumerate(action.get('options', [])):
                    title = option.get('title', 'N/A')
                    price = option.get('price', 'N/A')
                    summary_message += f"{i+1}. {title} - {price}\n"
                summary_message += "\nPlease let me know which one you'd like, or if you want me to keep looking."
                
                question = summary_message
                socketio.emit('request_user_input', {'question': question})
                user_input_event.wait()
                user_input_event.clear()
                user_response = shared_state["user_response"]
                self.conversation_history.append({"role": "assistant", "content": question})
                self.conversation_history.append({"role": "user", "content": user_response})
                continue

            elif action["action"] == "ASK_USER":
                question = action.get("question", "What should I do next?")
                socketio.emit('request_user_input', {'question': question})
                user_input_event.wait()
                user_input_event.clear()
                user_response = shared_state["user_response"]
                self.conversation_history.append({"role": "assistant", "content": question})
                self.conversation_history.append({"role": "user", "content": user_response})
                continue 

            elif action["action"] == "FINISH":
                response_to_user = action.get("reason", "Task is complete.")
                socketio.emit('agent_response', {'data': f"Task Complete: {response_to_user}"})
                socketio.emit('task_finished')
                print("✅ Task finished.")
                return 

            # Construct response first, then execute action
            elif action["action"] == "NAVIGATE":
                url = action.get("url")
                response_to_user = f"I will navigate to {url}."
                if not url:
                    action_failed = True
                    failure_reason = "Missing 'url' for NAVIGATE action."
                else:
                    if not self.web_navigator.navigate(url): action_failed = True

            elif action["action"] == "CLICK":
                element = action.get("element_description")
                response_to_user = f"I will click on '{element}'."
                if not element:
                    action_failed = True
                    failure_reason = "Missing 'element_description' for CLICK action."
                else:
                    if not self.web_navigator.click(element): action_failed = True

            elif action["action"] == "TYPE":
                text = action.get("text")
                element = action.get("element_description")
                response_to_user = f"I will type '{text}' into '{element}'."
                if not text or not element:
                    action_failed = True
                    failure_reason = "Missing 'text' or 'element_description' for TYPE action."
                else:
                    if not self.web_navigator.type(text, element): action_failed = True
            
            elif action["action"] == "SCROLL":
                direction = action.get("direction")
                response_to_user = f"I will scroll {direction}."
                if not direction:
                    action_failed = True
                    failure_reason = "Missing 'direction' for SCROLL action."
                else:
                    if not self.web_navigator.scroll(direction): action_failed = True

            elif action["action"] == "CLEAR_INPUT":
                element = action.get("element_description")
                response_to_user = f"I will clear the input field '{element}'."
                if not element:
                    action_failed = True
                    failure_reason = "Missing 'element_description' for CLEAR_INPUT action."
                else:
                    if not self.web_navigator.clear_input(element): action_failed = True

            else:
                response_to_user = "I am not sure what to do next. I will ask the user for help."
                socketio.emit('agent_response', {'data': response_to_user})
                self.conversation_history.append({"role": "assistant", "content": response_to_user})
                continue

            if action_failed:
                if not failure_reason:
                    failure_reason = f"I could not find the element '{action.get('element_description', 'N/A')}'."
                response_to_user += f" (But I failed: {failure_reason})."
                screenshot_description = f"Previous action failed: {failure_reason}\n\n" + self.observer.observe(screenshot_bytes)

            self.conversation_history.append({"role": "assistant", "content": response_to_user})
            socketio.emit('agent_response', {'data': response_to_user})
