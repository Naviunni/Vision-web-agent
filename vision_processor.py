import requests
import io
from PIL import Image
import json
from utils import extract_bbox, draw_box, draw_point

class VisionProcessor:
    def __init__(self, model_url="http://localhost:8000/infer"):
        self.model_url = model_url

    def query_model(self, image_bytes, prompt):
        """Send screenshot + prompt to the Qwen-VL server."""
        response = requests.post(
            self.model_url,
            data={"prompt": prompt},
            files={"image": ("screenshot.png", image_bytes, "image/png")},
            timeout=120,
        )
        response.raise_for_status()
        
        try:
            return response.json()
        except json.JSONDecodeError:
            # If the response is not valid JSON, return the raw text.
            # This can happen if the Qwen server's output is truncated.
            return {"raw_output": response.text}


    def describe_image(self, image_bytes):
        """
        Takes an image and returns a concise description of the actionable elements on the page.
        """
        prompt = "Describe the main elements on this webpage. Include buttons, input fields, and links. Be concise and use bullet points."
        model_output = self.query_model(image_bytes, prompt)
        
        # The Qwen model seems to return the prompt as part of the raw_output.
        # We need to extract only the assistant's response.
        raw_output = model_output["raw_output"]
        
        # Find the start of the assistant's response after the prompt.
        prompt_text_start = "Describe the main elements on this webpage."
        if "assistant\n" in raw_output:
            # Find the last occurrence of assistant\n, which should be the start of the response.
            actual_response = raw_output.split("assistant\n")[-1].strip()
        else:
            # If "assistant\n" is not found, assume the entire raw_output is the response.
            actual_response = raw_output.strip()

        return actual_response

    def get_element_bbox(self, image_bytes, element_description):
        """
        Takes an image and a natural language description of an element,
        and returns the bounding box of that element.
        """
        prompt = f"Give the exact bounding box of the {element_description} with absolute pixel coordinates in the format [x1,y1,x2,y2]."
        model_output = self.query_model(image_bytes, prompt)
        raw = model_output["raw_output"].strip()
        bbox = extract_bbox(raw)
        return bbox

    def annotate_image(self, image_bytes, bbox):
        """
        Draws the bounding box and center point on the image for visualization.
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        sx, sy = img.size

        x1, y1, x2, y2 = bbox
        px1 = int(x1 / 1000 * sx)
        py1 = int(y1 / 1000 * sy)
        px2 = int(x2 / 1000 * sx)
        py2 = int(y2 / 1000 * sy)
        bbox_pixels = (px1, py1, px2, py2)

        cx = (px1 + px2) // 2
        cy = (py1 + py2) // 2

        img_annotated = draw_box(img, bbox_pixels, color='green')
        img_annotated = draw_point(img_annotated, (cx, cy), radius=12, color='red')
        
        return img_annotated
