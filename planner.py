import openai
import json
import os

class Planner:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4"

    def get_next_action(self, conversation_history, screenshot_description):
        print("🤖 Deciding next action with GPT-4...")

        system_prompt = """
        You are a web agent's planner. Your role is to decide the next action to take to achieve the user's goal.
        You will be given the conversation history, the user's goal, and a description of the current web page.

        You can perform the following actions:
        - NAVIGATE(url): Go to a specific URL.
        - CLICK(element_description): Click on a specific element on the page.
        - TYPE(text, element_description): Type text into a specific input field.
        - ASK_USER(question): Ask the user for clarification.
        - FINISH(reason): The task is complete.

        Your thought process should be:
        1. What is the user's ultimate goal?
        2. Based on the description of the page, what is the most logical next step to get closer to that goal? If the description is unclear, ask the user for help.
        3. Formulate the action as a single, well-formed JSON object.

        You must respond with a single JSON object representing the action to take. For example:
        {"action": "NAVIGATE", "url": "https.google.com"}
        {"action": "CLICK", "element_description": "the 'Add to Cart' button"}
        {"action": "TYPE", "text": "laptops", "element_description": "the search bar"}
        {"action": "ASK_USER", "question": "Which brand of laptop are you looking for?"}
        {"action": "FINISH", "reason": "The user has found the laptop they were looking for."}
        """

        user_prompt = f"""
        Conversation History:
        {json.dumps(conversation_history, indent=2)}

        Current Page Description:
        {screenshot_description}

        Based on the conversation and the page description, what is the next logical action to take to progress towards the user's goal?
        """

        print("\n---PROMPT SENT TO PLANNER---\n")
        print(user_prompt)
        print("\n---------------------------\n")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
            )

            action_json = response.choices[0].message.content
            
            print("\n---RESPONSE FROM PLANNER---\n")
            print(action_json)
            print("\n---------------------------\n")

            # Extract JSON from potentially conversational response
            json_start = action_json.find('{')
            json_end = action_json.rfind('}')

            if json_start != -1 and json_end != -1:
                action_str = action_json[json_start : json_end + 1]
            else:
                # If no JSON delimiters found, try to parse the whole response.
                # This might happen if the model only returns the JSON.
                action_str = action_json

            action = json.loads(action_str)
            
            # Validate the action
            if "action" not in action or action["action"] not in ["NAVIGATE", "CLICK", "TYPE", "ASK_USER", "FINISH"]:
                raise ValueError("Invalid action specified.")

            return action

        except Exception as e:
            print(f"Error while planning: {e}")
            # If we fail to parse the action, we ask the user for help.
            return {"action": "ASK_USER", "question": "I'm having trouble deciding what to do next. The page description might be unclear. Can you please clarify your goal?"}