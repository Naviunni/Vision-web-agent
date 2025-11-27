import requests
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
import json
import io
from PIL import Image, ImageDraw, ImageColor
import re
import json

def extract_bbox(raw_text):
    """
    Extracts the last [x1,y1,x2,y2] array from model output.
    Handles whitespace, multi-line text, and extra content.
    Returns a list of 4 ints.
    """

    # Find the last bracketed list like [582,237,865,293]
    matches = re.findall(r"\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\]", raw_text)
    if not matches:
        raise ValueError(f"No bounding box found in output: {raw_text}")

    bbox_str = matches[-1]  # take the last one
    
    try:
        bbox = json.loads(bbox_str)
        if len(bbox) != 4:
            raise ValueError
        return bbox
    except Exception:
        raise ValueError(f"Could not parse bbox: {bbox_str}")

def draw_point(image, point, radius=10, color='red'):
    """Draw a semi-transparent point using Qwen's visualization style."""
    overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    x, y = point
    
    overlay_draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=ImageColor.getrgb(color) + (200,)
    )
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')


def draw_box(image, box, color='green', width=4):
    """Draw a semi-transparent bounding box using Qwen style."""
    overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    overlay_draw.rectangle(
        box,
        outline=ImageColor.getrgb(color) + (200,),
        width=width
    )
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')


MODEL_URL = "http://localhost:8000/infer"

def query_model(image_bytes, prompt):
    """Send screenshot + prompt to the Qwen-VL server running on Grace."""
    response = requests.post(
        MODEL_URL,
        data={"prompt": prompt},
        files={"image": ("screenshot.png", image_bytes, "image/png")},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1
        )

        # 1. Navigate to the website
        # url = "https://www.facebook.com"
        url = "https://www.dominos.com/"
        print(f"➡️ Navigating to {url}")
        page.goto(url)
        page.wait_for_timeout(2000)

        # 2. Take screenshot
        print("📸 Taking screenshot")
        screenshot_bytes = page.screenshot()
        img = Image.open(io.BytesIO(screenshot_bytes))
        print("Screenshot size:", img.size)
        print(page.viewport_size)

        # 3. Ask the model
        prompt = "Give the exact bounding box of the button to order delivery with absolute pixel coordinates in the format [x1,y1,x2,y2]."
        # prompt = "Give the x and y pixel coordinates of the center of the login button where x is the pixels from the top edge and y is the pixels from the left edge"
        print("🤖 Sending screenshot to Qwen-VL...")
        model_output = query_model(screenshot_bytes, prompt)

        print("\n================ MODEL RESPONSE ================\n")
        print(model_output)
        print("\n=================================================\n")

        # Extract raw output text
        raw = model_output["raw_output"].strip()
        bbox = extract_bbox(raw)
        print("Parsed bbox:", bbox)

        x1, y1, x2, y2 = bbox   # EX: [582,237,865,293]

        # Load screenshot
        img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")
        sx, sy = img.size   # e.g., (1280, 900)

        # Convert normalized bbox → pixel space
        px1 = int(x1 / 1000 * sx)
        py1 = int(y1 / 1000 * sy)
        px2 = int(x2 / 1000 * sx)
        py2 = int(y2 / 1000 * sy)

        bbox_pixels = (px1, py1, px2, py2)

        # Draw Qwen-style box and center point
        cx = (px1 + px2) // 2
        cy = (py1 + py2) // 2

        img_annotated = draw_box(img, bbox_pixels, color='green')
        img_annotated = draw_point(img_annotated, (cx, cy), radius=12, color='red')

        # Save
        img_annotated.save("annotated_scaled.png")
        print("Saved annotated image as annotated_scaled.png")

        # --- Compute center for clicking ---
        cx = (px1 + px2) // 2
        cy = (py1 + py2) // 2

        print(f"Clicking at: ({cx}, {cy})")

        # --- Perform the actual click ---
        page.mouse.click(cx, cy)
        page.wait_for_timeout(1000)  # let UI update

        # browser.close()

if __name__ == "__main__":
    main()