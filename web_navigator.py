from playwright.sync_api import sync_playwright
from vision_processor import VisionProcessor
from threading import Thread, Event
from queue import Queue, Empty
import traceback

class WebNavigator:
    def __init__(self, vision_processor):
        self.vision_processor = vision_processor
        self.command_queue = Queue()
        self.result_queue = Queue()
        self._stop_event = Event()

        self.thread = Thread(target=self._run_playwright)
        self.thread.start()

    def _run_playwright(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=1
            )
            self.page = self.context.new_page()
            
            self.context.on("page", self._on_new_page_internal)

            while not self._stop_event.is_set():
                try:
                    command = self.command_queue.get(timeout=1)
                    action = command.get("action")
                    data = command.get("data")
                    
                    result = None
                    if action == "navigate":
                        self._navigate(data)
                        result = True
                    elif action == "take_screenshot":
                        result = self._take_screenshot()
                    elif action == "scroll":
                        self._scroll(data)
                        result = True
                    elif action == "click":
                        result = self._click(data)
                    elif action == "type":
                        result = self._type(data)
                    elif action == "clear_input":
                        result = self._clear_input(data)
                    elif action == "wait":
                        result = self._wait(data)
                    
                    self.result_queue.put(result)
                
                except Empty:
                    continue 
                except Exception as e:
                    print(f"Error in Playwright thread for action '{action}':")
                    traceback.print_exc()
                    self.result_queue.put(False) # Put False on error

            self.browser.close()

    def _on_new_page_internal(self, new_page):
        print("🤖 New tab or window opened. Switching context.")
        self.page = new_page
        self.page.bring_to_front()

    def _execute_command(self, command):
        self.command_queue.put(command)
        return self.result_queue.get()

    def navigate(self, url):
        return self._execute_command({"action": "navigate", "data": url})

    def take_screenshot(self):
        return self._execute_command({"action": "take_screenshot"})

    def scroll(self, direction):
        return self._execute_command({"action": "scroll", "data": direction})

    def click(self, element_description):
        return self._execute_command({"action": "click", "data": element_description})

    def type(self, text, element_description):
        return self._execute_command({"action": "type", "data": {"text": text, "element_description": element_description}})
    
    def clear_input(self, element_description):
        return self._execute_command({"action": "clear_input", "data": element_description})

    def wait(self, seconds):
        return self._execute_command({"action": "wait", "data": seconds})

    def close(self):
        self._stop_event.set()
        self.thread.join()

    def _navigate(self, url):
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1000)

    def _take_screenshot(self):
        self.page.bring_to_front()
        return self.page.screenshot()

    def _scroll(self, direction):
        if direction == "down":
            self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        elif direction == "up":
            self.page.evaluate("window.scrollBy(0, -window.innerHeight)")
        self.page.wait_for_timeout(1000)

    def _click(self, element_description):
        self.page.bring_to_front()
        viewport_size = self.page.viewport_size
        self.page.mouse.move(viewport_size['width'] / 2, viewport_size['height'] / 2)
        self.page.wait_for_timeout(500) 

        screenshot_bytes = self._take_screenshot()
        bbox = self.vision_processor.get_element_bbox(screenshot_bytes, element_description)
        
        if bbox is None:
            return False # Signal failure

        x1, y1, x2, y2 = bbox
        px1, py1 = int(x1 / 1000 * viewport_size['width']), int(y1 / 1000 * viewport_size['height'])
        px2, py2 = int(x2 / 1000 * viewport_size['width']), int(y2 / 1000 * viewport_size['height'])
        cx, cy = (px1 + px2) // 2, (py1 + py2) // 2
        print(f"Clicking on '{element_description}' at: ({cx}, {cy})")
        self.page.mouse.click(cx, cy)
        self.page.wait_for_timeout(1000)
        return True # Signal success

    def _type(self, data):
        text, element_description = data["text"], data["element_description"]
        if not self._clear_input(element_description):
            return False
        
        print(f"Typing '{text}' into '{element_description}'")
        self.page.keyboard.type(text)
        print("Pressing Enter to submit.")
        self.page.keyboard.press("Enter")
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(1000)
        return True

    def _clear_input(self, element_description):
        print(f"Attempting to clear input field: '{element_description}'")
        if not self._click(element_description):
            return False
        
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(500)
        print(f"Input field '{element_description}' cleared.")
        return True

    def _wait(self, seconds):
        try:
            ms = int(float(seconds) * 1000)
        except Exception:
            ms = 1000
        self.page.wait_for_timeout(ms)
        return True
