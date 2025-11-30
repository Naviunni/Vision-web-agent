from playwright.sync_api import sync_playwright
from vision_processor import VisionProcessor

class WebNavigator:
    def __init__(self, vision_processor):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1
        )
        self.vision_processor = vision_processor

    def navigate(self, url):
        print(f"➡️ Navigating to {url}")
        self.page.goto(url, wait_until="networkidle")
        self.page.wait_for_timeout(1000)

    def take_screenshot(self):
        print("📸 Taking screenshot")
        screenshot_bytes = self.page.screenshot()
        return screenshot_bytes

    def scroll(self, direction):
        print(f"↕️ Scrolling {direction}")
        if direction == "down":
            self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        elif direction == "up":
            self.page.evaluate("window.scrollBy(0, -window.innerHeight)")
        self.page.wait_for_timeout(1000)


    def click(self, element_description):
        screenshot_bytes = self.take_screenshot()
        bbox = self.vision_processor.get_element_bbox(screenshot_bytes, element_description)
        
        x1, y1, x2, y2 = bbox
        
        viewport_size = self.page.viewport_size
        px1 = int(x1 / 1000 * viewport_size['width'])
        py1 = int(y1 / 1000 * viewport_size['height'])
        px2 = int(x2 / 1000 * viewport_size['width'])
        py2 = int(y2 / 1000 * viewport_size['height'])

        cx = (px1 + px2) // 2
        cy = (py1 + py2) // 2

        print(f"Clicking on '{element_description}' at: ({cx}, {cy})")
        self.page.mouse.click(cx, cy)
        self.page.wait_for_timeout(1000)

    def type(self, text, element_description):
        self.click(element_description)
        print(f"Typing '{text}' into '{element_description}'")
        self.page.keyboard.type(text)
        self.page.wait_for_timeout(500)

    def close(self):
        self.browser.close()
        self.playwright.stop()
