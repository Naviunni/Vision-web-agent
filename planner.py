import openai
import json
import os
import traceback

class Planner:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
        # Default to a cheaper capable model; allow override via env
        self.model = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4o-mini")

    def get_next_action(self, conversation_history, screenshot_description):
        print("🤖 Deciding next action with GPT-4...")

        system_prompt = """
        You are a versatile web agent's planner. Your goal is to help users accomplish tasks on any website.

        Actions & Required Arguments:
        - NAVIGATE: requires url.
        - CLICK: requires element_description.
        - TYPE: requires text and element_description.
        - CLEAR_INPUT: requires element_description.
        - SCROLL: requires direction ('up' or 'down').
        - OBSERVE: requires question.
        - SUMMARIZE_OPTIONS: requires topic and options (a list of dicts).
        - ASK_USER: requires question.
        - FINISH: requires reason.
        You MUST provide all required arguments for the action you choose.

        Specialized Skill: Personal Shopper
        - If the user's goal is shopping, adopt this workflow:
          1) Search: Navigate to the site and search for the item.
          2) Explore: On results, SCROLL once to load more items.
          3) Observe & Collect: Use OBSERVE to gather details (title, price) for 3–4 items.
          4) Summarize: Use SUMMARIZE_OPTIONS to present the collected items.
          5) Act on Choice: After the user chooses, CLICK the chosen item or its Add to Cart.

        Verify Before Repeating
        - When you intend to repeat a state-changing action (e.g., clicking Add to Cart again), first issue an OBSERVE with a pointed verification question about the intended effect.
        - Example verification questions: "Is the chosen item already in the cart? Answer yes or no and provide a brief evidence phrase from the UI." or "Did the page show any cart/added indicators? Answer yes or no with a short rationale."
        - If the OBSERVE indicates success, do not repeat the action; instead proceed (e.g., FINISH or navigate to cart if the user asked).

        Failure Handling
        - If informed that a previous action failed, re-evaluate and try a different strategy. Do not repeat the same failing action verbatim.

        General Rules
        - Be proactive.
        - For searches, navigate to the homepage first, then use the search bar.
        - A pause button on a video means it's already playing.

        Respond with a single, well-formed JSON object.
        """

        user_prompt = f"""
        Conversation History:
        {json.dumps(conversation_history, indent=2)}

        Current Page Description:
        {screenshot_description}

        Based on the user's goal and your workflow, what is the next logical action?
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                # Request strict JSON to reduce parsing failures (supported by 4o family)
                response_format={"type": "json_object"}
            )

            action_json = response.choices[0].message.content
            
            json_start = action_json.find('{')
            json_end = action_json.rfind('}')

            if json_start != -1 and json_end != -1:
                action_str = action_json[json_start : json_end + 1]
            else:
                action_str = action_json
            
            try:
                action = json.loads(action_str)
            except json.JSONDecodeError:
                print("Failed to decode JSON from model, will retry.")
                return {"action": "RETRY", "reason": "Malformed JSON response from planner."}

            if "action" not in action or action["action"] not in ["NAVIGATE", "CLICK", "TYPE", "CLEAR_INPUT", "SCROLL", "OBSERVE", "ASK_USER", "FINISH", "RETRY", "SUMMARIZE_OPTIONS"]:
                raise ValueError("Invalid action specified.")

            return action

        except Exception as e:
            print(f"Error while planning:")
            traceback.print_exc()
            return {"action": "ASK_USER", "question": "I'm having trouble deciding what to do next. Can you please clarify your goal?"}
