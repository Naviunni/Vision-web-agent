# server.py

import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

import torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

app = FastAPI()

# ---- Load model & processor once on startup ----
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"

print("Loading model on GPU...")
model = Qwen3VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    dtype="auto",
    device_map="auto",
)
processor = AutoProcessor.from_pretrained(MODEL_NAME)

# Optional: safer for batch later
processor.tokenizer.padding_side = "left"


@app.post("/infer")
async def infer(
    image: UploadFile = File(...),
    prompt: str = Form(...),
):
    try:
        # 1. Save uploaded screenshot to a temp file
        img_bytes = await image.read()
        tmp_name = f"{uuid.uuid4().hex}.png"
        tmp_path = os.path.join("/tmp", tmp_name)
        with open(tmp_path, "wb") as f:
            f.write(img_bytes)

        # 2. Build messages EXACTLY like Qwen examples expect
        #    (outer list = batch, inner list = conversation)
        messages = [
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "image": f"file://{tmp_path}",
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ]
        ]

        # 3. Get text prompt via chat template (tokenize=False)
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # 4. Use qwen-vl-utils to prepare visual inputs
        images, videos, video_kwargs = process_vision_info(
            messages,
            image_patch_size=16,           # Qwen3-VL vision patch size  [oai_citation:2‡GitHub](https://github.com/QwenLM/Qwen3-VL)
            return_video_kwargs=True,
            return_video_metadata=True,
        )

        # For Qwen3-VL, videos (if any) come as (tensor, metadata)
        if videos is not None:
            videos, video_metadatas = zip(*videos)
            videos = list(videos)
            video_metadatas = list(video_metadatas)
        else:
            video_metadatas = None

        # 5. Build model inputs via processor (cookbook style)
        inputs = processor(
            text=text,
            images=images,
            videos=videos,
            video_metadata=video_metadatas,
            return_tensors="pt",
            do_resize=False,   # qwen-vl-utils already resized  [oai_citation:3‡PyPI](https://pypi.org/project/qwen-vl-utils/)
            **video_kwargs,
        )

        # 6. Move to model device
        inputs = {k: v.to(model.device) if isinstance(v, torch.Tensor) else v
                  for k, v in inputs.items()}

        # 7. Generate + decode only the new tokens
        generated_ids = model.generate(**inputs, max_new_tokens=256)

        # For this qwen-vl-utils pipeline we didn’t pass input_ids directly,
        # so we can just decode the whole sequence; the template is short anyway.
        output_text = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

        # 8. Cleanup tmp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return JSONResponse({"raw_output": output_text})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )