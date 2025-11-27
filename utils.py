import re
import json
from PIL import Image, ImageDraw, ImageColor

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
