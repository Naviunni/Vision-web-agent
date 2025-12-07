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
        You are a versatile web agent's planner. Your goal is to help users accomplish tasks on any website in a reliable, general way.

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

        Core Pattern (General Purpose)
        - Observe → Plan → Act → Verify.
        - After every state‑changing action (e.g., click, type, navigation), VERIFY success by issuing a targeted OBSERVE question rather than assuming.
        - If verification fails or the page did not change meaningfully, choose a different strategy; do not repeat the same failing action.

        Disambiguating Targets (General)
        - When multiple similar controls exist, make element_description specific by anchoring with:
          • Nearby text (title/label/alt),
          • Container context ("within the same card/row as ..."),
          • Spatial relation ("the first item", "the button next to ...").
        - Region scoping: constrain targets to a page region when helpful (e.g., "within the profile card/main content, not the top header/footer/navigation").
        - When a list page is ambiguous, prefer opening the item's detail page via its title/link, then act there.

        Link Selection Heuristics (General)
        - Prefer links that directly satisfy the user's intent (e.g., a "Personal website"/"Homepage"/"Lab" link near a profile) over broad site navigation (e.g., global "PEOPLE" in the top bar).
        - If multiple plausible links exist (e.g., several "People"/"Team" links), choose the one within the local context of the entity/profile, or on the entity's own site, instead of global navigation.
        - If unsure, first OBSERVE to enumerate up to 5 candidate links with: link text, approximate region (header/main/footer/sidebar), and a brief reason; then select one and CLICK with a region-scoped element_description.

        Handling Transient UI (Modals/Popovers/Toasts)
        - Before clicking modal/popover controls, OBSERVE to confirm it is visible and list the primary buttons.
        - After clicking a modal control (e.g., Close/Cancel/Continue), OBSERVE to confirm the modal is dismissed before proceeding.
        - If the modal is not present, do NOT click its controls; continue with the main page flow instead.

        Avoiding Unproductive Loops
        - Do not issue multiple OBSERVE actions that restate the same view without a viewport/site change. If you need more items, SCROLL once or twice, then summarize.
        - Limit scroll attempts (e.g., ≤2) before summarizing and/or asking the user.
        - Do not repeatedly NAVIGATE to the same URL you are already on. If already on the intended site, proceed with the next logical action.

        Authority‑First Navigation (Entities/Profiles)
        - When the goal involves a person, organization, or a catalog of works (e.g., publications, projects), prefer opening the authoritative/official page shown in results (e.g., a profile page) rather than sampling scattered results.
        - Disambiguate entities using affiliation, verified email, location, or biography when available; if ambiguous, ASK_USER which one.
        - Once on an authoritative page, use on‑page sort/filter controls (e.g., sort by date) to gather the requested items (e.g., latest N) and VERIFY via OBSERVE that the items are correctly ordered/recent.

        Media Controls (Generic)
        - Do not infer play state solely from an icon. Verify by reading the control state and timestamp, WAIT 1s, then re‑read and compare; only then declare playing/paused and act accordingly.

        Options and Choices (Generic)
        - When many options are present (products, links, settings), collect 3–4 distinct options via OBSERVE, then use SUMMARIZE_OPTIONS and ASK_USER which to follow.

        Navigation Defaults (Generic)
        - If the user did not specify a site and you need to search, use a general‑purpose search engine first.
        - Avoid placeholder/documentation domains for real tasks.

        Respond with a single, well‑formed JSON object.
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
