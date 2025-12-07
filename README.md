# Vision-Model Web Navigator (Accessibility-Focused)

An agentic web navigator that combines a vision model (Qwen-VL) for screen understanding with a language planner (OpenAI GPT) for deciding actions. It drives a real browser (Playwright) to complete multi-step tasks while keeping interactions accessible and transparent.

- Vision (Qwen-VL): Describes screens and localizes elements for clicks.
- Planner (GPT): Chooses next actions (navigate, click, type, scroll, etc.).
- Browser (Playwright): Executes deterministic interactions.
- UI (Flask + Socket.IO): Simple chat for goals, observations, and responses.

## Features
- Vision-first routing for all “what’s on screen?” tasks.
- Action set: NAVIGATE, CLICK, TYPE, CLEAR_INPUT, SCROLL, WAIT, OBSERVE, SUMMARIZE_OPTIONS, ASK_USER, FINISH.
- Robust patterns: verify-after-act, avoid loops, region-scoped element targets.
- Media reliability: OBSERVE -> WAIT -> OBSERVE to confirm playback state.
- Input clearing: focus + double-click + multiple Backspace/Delete.
- Screenshot hinting: centers mouse before screenshots to reveal hidden controls.

## Project Structure
- `app.py` — Flask + Socket.IO server and background agent runner
- `agent.py` — Orchestrates Observe → Plan → Act → Verify loop
- `planner.py` — GPT planner (configurable model; strict JSON responses)
- `vision_processor.py` — Qwen-VL HTTP client (describe + bbox)
- `web_navigator.py` — Playwright controller (threaded); browser actions
- `observer.py` — Thin wrapper over vision describe
- `utils.py` — BBox parsing + simple annotations
- `templates/`, `static/` — Minimal chat UI
- `requirements.txt` — Python deps
- `report.md` — Technical report (details, methodology, architecture)

## Prerequisites
- Python 3.11+ recommended (Playwright support evolves; 3.14 also works in this repo)
- Chromium via Playwright: `python -m playwright install`
- OpenAI API key for planner
- Qwen-VL server reachable locally (e.g., via SSH tunnel)

## Installation
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install
```

## Configuration
Set environment variables (or create a `.env` if you prefer and export them in your shell):

- `OPENAI_API_KEY`: OpenAI key for planner
- `OPENAI_PLANNER_MODEL` (optional): default `gpt-4o-mini`. Examples: `gpt-4o`, `gpt-4o-mini`.
- `VISION_MODEL_URL` (optional): Qwen-VL HTTP endpoint, default `http://localhost:8000/infer`

Example:
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_PLANNER_MODEL=gpt-4o-mini
export VISION_MODEL_URL=http://localhost:8000/infer
```

## Qwen-VL Server (SSH Tunnel)
Expose the remote vision server locally with port forwarding:
```bash
ssh -L 8000:127.0.0.1:<remote_qwen_port> user@grace.cluster.edu
```

## Run
```bash
python app.py
```
Open the UI at `http://127.0.0.1:5001/`.

Workflow:
1) Enter a goal in the input box.
2) The agent iterates: observe (Qwen) → plan (GPT) → act (Playwright).
3) The UI shows observations and actions; it may ask you follow-up questions.

## How It Works
- The agent takes a screenshot; `Observer` asks Qwen to describe the current page or answer a targeted question.
- `Planner` receives the observation + current URL + conversation history and returns a JSON action.
- `WebNavigator` executes the action in a real browser and the loop continues.
- Element clicks use Qwen bboxes (normalized 0..1000) → converted to page pixels.

Common actions returned by the planner:
- `{"action":"NAVIGATE","url":"https://..."}`
- `{"action":"CLICK","element_description":"Search button next to the input labeled '...'"}`
- `{"action":"TYPE","text":"query","element_description":"search bar"}`
- `{"action":"OBSERVE","question":"List the first 3 options with titles and prices"}`
- `{"action":"WAIT","seconds":1}`
- `{"action":"FINISH","reason":"Task complete"}`


## Development Notes
- BBox convention: Qwen returns normalized `[x1,y1,x2,y2]` in 0..1000; navigator converts to pixels.
