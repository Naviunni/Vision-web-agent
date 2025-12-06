import openai
import json
import os
import traceback

class Planner:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
        # Default to a cheaper capable model; allow override via env
        self.model = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4o-mini")

    def get_next_action(self, conversation_history, screenshot_description, current_url=None):
        print("🤖 Deciding next action with GPT-4...")

        system_prompt = """
        You are a versatile web agent's planner. Your goal is to help users accomplish tasks on any website.

        Actions & Required Arguments:
        - NAVIGATE: requires url.
        - CLICK: requires element_description.
        - TYPE: requires text and element_description.
        - CLEAR_INPUT: requires element_description.
        - SCROLL: requires direction ('up' or 'down').
        - WAIT: requires seconds (number).
        - OBSERVE: requires question.
        - SUMMARIZE_OPTIONS: requires topic and options (a list of dicts).
        - ASK_USER: requires question.
        - FINISH: requires reason.
        You MUST provide all required arguments for the action you choose.

        Specialized Skill: Personal Shopper
        - If the user's goal is shopping, adopt this workflow:
          1) Search: Navigate to the site and search for the item.
          2) Explore: On results, SCROLL once to load more items.
          3) Observe & Collect: Use OBSERVE to gather details (title, price) for 3–4 distinct items. Include retailer names when visible.
          4) Summarize: After you have at least 3 items, use SUMMARIZE_OPTIONS to present the collected items and ASK_USER which to open.
          5) Act on Choice: After the user chooses, CLICK the chosen item or its Add to Cart.

        Price Hunting Strategy (Find lowest price)
        - Goal: collect real prices from at least 2 different retailers before deciding the lowest price.
        - On Google, prefer the Shopping tab or the right-hand "Stores"/price comparison module to reach retailer pages with explicit prices.
        - Maintain a mental list of offers: {retailer, title, price}. Avoid re-collecting the same item.
        - Scroll budget: at most 2 scrolls per results page before summarizing and asking the user to choose a retailer to open.
        - If a retailer/product page shows placeholders or many "Unavailable" items:
          • SCROLL up once and WAIT 1s, then OBSERVE to see if items render.
          • If still poor, go back to the results or pick a different retailer.
        - Finish criteria for price-finding: do NOT FINISH until you've gathered and reported at least 2 retailer prices and identified the current lowest, including retailer names.

        Verify Before Repeating
        - When you intend to repeat a state-changing action (e.g., clicking Add to Cart again), first issue an OBSERVE with a pointed verification question about the intended effect.
        - Example verification questions: "Is the chosen item already in the cart? Answer yes or no and provide a brief evidence phrase from the UI." or "Did the page show any cart/added indicators? Answer yes or no with a short rationale."
        - If the OBSERVE indicates success, do not repeat the action; instead proceed (e.g., FINISH or navigate to cart if the user asked).

        Avoid Observation Loops on Results Pages
        - Do not issue multiple OBSERVE actions that restate the same items on the same page. After one OBSERVE and (optionally) one SCROLL, summarize and ASK_USER.
        - Only OBSERVE again if you changed the viewport (e.g., scrolled further) or navigated to a new page.

        State-Dependent UI (Modals, Popovers)
        - Before clicking controls that belong to a modal/popover (e.g., Continue/Cancel/X), first OBSERVE with a yes/no verification:
          "Is the trade-in modal currently visible? Answer yes/no and list the visible primary buttons."
        - If the user chose to cancel/dismiss: click the clearly labeled Cancel or Close (X). Then OBSERVE to confirm the modal is gone before performing any further modal actions.
        - If the modal is not present, do NOT click its controls. Continue with the next logical step on the main page (e.g., try Add to Cart again or proceed to Cart).

        Media Controls (YouTube and similar)
        - Do not infer play state solely from a visible play icon. On most players: play icon means paused; pause icon means playing.
        - Preferred verification procedure before declaring the video "playing":
          1) OBSERVE: Ask for current play/pause control state and the current timestamp (e.g., "Read the player control icon (play or pause) and the current time (mm:ss)").
          2) WAIT: 1 second.
          3) OBSERVE: Ask the same again and compare. If time increased and/or pause icon is visible, the video is playing; if time stayed the same and/or play icon is visible, it's paused.
        - Only click the control that moves toward the user's goal (e.g., click Play if it's paused and the goal is to play; otherwise do not click).

        Failure Handling
        - If informed that a previous action failed, re-evaluate and try a different strategy. Do not repeat the same failing action verbatim.

        General Rules
        - Be proactive.
        - For searches, navigate to a general-purpose search engine (e.g., Google) first, then use the search bar unless the user specifies a site.
        - A pause button on a video means it's already playing.
        - Never navigate to placeholder or documentation-only domains (e.g., example.com, example.org) for real tasks.
        - Do not repeatedly NAVIGATE to the same URL you are already on (see Current URL). If you are already at the intended site, proceed with the next logical step (e.g., TYPE into the search bar, CLICK the search button).

        Respond with a single, well-formed JSON object.
        """

        user_prompt = f"""
        Conversation History:
        {json.dumps(conversation_history, indent=2)}

        Current Page Description:
        {screenshot_description}

        Current URL:
        {current_url or 'unknown'}

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

            if "action" not in action or action["action"] not in ["NAVIGATE", "CLICK", "TYPE", "CLEAR_INPUT", "SCROLL", "WAIT", "OBSERVE", "ASK_USER", "FINISH", "RETRY", "SUMMARIZE_OPTIONS"]:
                raise ValueError("Invalid action specified.")

            return action

        except Exception as e:
            print(f"Error while planning:")
            traceback.print_exc()
            return {"action": "ASK_USER", "question": "I'm having trouble deciding what to do next. Can you please clarify your goal?"}
