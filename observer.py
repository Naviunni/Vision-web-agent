from vision_processor import VisionProcessor

class Observer:
    def __init__(self, vision_processor):
        self.vision_processor = vision_processor

    def observe(self, screenshot_bytes, question=None):
        """
        Takes a screenshot and returns a description of the page.
        """
        print("👀 Observing the page with Qwen-VL...")
        return self.vision_processor.describe_image(screenshot_bytes, question)