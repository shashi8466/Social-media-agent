import os
import json
import re
import uuid
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
from .segmind_agent import SegmindAgent

load_dotenv()

# Image ratio → (width, height)
RATIO_SIZES = {
    "1:1":    (1024, 1024),
    "4:5":    (1024, 1280),
    "9:16":   (1024, 1820),
    "16:9":   (1820, 1024),
    "3:2":    (1536, 1024),
    "default": (1024, 1024),
}

# Platform default ratios
PLATFORM_RATIOS = {
    "linkedin":  "16:9",
    "instagram": "1:1",
    "facebook":  "16:9",
    "twitter":   "16:9",
    "youtube":   "16:9",
    "tiktok":    "9:16",
    "pinterest": "2:3",
    "threads":   "1:1",
    "reels":     "9:16",
    "default":   "1:1",
}


class ImageAgent:
    """
    Image Agent — Two-step pipeline:
      1. OpenAI GPT-4o generates a rich, detailed image prompt
      2. Segmind (with DALL-E 3 fallback) generates the actual image

    Supports:
      - Single image generation
      - Batch generation (5+ images) with configurable ratio
    """

    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.segmind = SegmindAgent()
        self.model = "gpt-4o"
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_prompt(self) -> str:
        with open(os.path.join(self.prompts_dir, "image.txt"), "r", encoding="utf-8") as f:
            return f.read()

    def _extract_json(self, text: str) -> dict:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "prompt": f"Professional marketing image about {text[:50]}",
            "style": "photorealistic",
            "mood": "professional",
            "negative_prompt": "text, watermarks, blurry, cartoon",
        }

    def _resolve_dimensions(self, ratio: str, platform: str = "") -> tuple[int, int]:
        """Resolve final (width, height) from a ratio string or platform default."""
        if ratio and ratio in RATIO_SIZES:
            return RATIO_SIZES[ratio]
        if platform:
            default_ratio = PLATFORM_RATIOS.get(platform.lower(), "default")
            return RATIO_SIZES.get(default_ratio, RATIO_SIZES["default"])
        return RATIO_SIZES["default"]

    def generate_image_prompt(self, topic: str, platform: str) -> dict:
        """Use GPT-4o to craft a detailed Segmind/DALL-E image prompt."""
        prompt_template = self._load_prompt()
        prompt_template = prompt_template.replace("{topic}", topic)
        prompt_template = prompt_template.replace("{platform}", platform)
        response = self.openai.chat.completions.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt_template}],
        )
        return self._extract_json(response.choices[0].message.content)

    def generate_image(
        self,
        topic: str,
        platform: str,
        fast_mode: bool = False,
        ratio: str = "",
        image_index: int = 1,
        base_prompt: str = None,
    ) -> dict:
        """
        Generate a single image.

        fast_mode=True  — use topic directly as prompt (skip GPT-4o)
        base_prompt     — a pre-crafted rich prompt to reuse (skips the per-image
                          GPT-4o call). Used for fast batch generation.
        ratio           — override ratio ("1:1", "4:5", "9:16", "16:9", "3:2")
        image_index     — used to vary prompt style for batch generation
        """
        style_variations = [
            "cinematic photography, golden hour lighting",
            "minimal clean design, white background, product showcase",
            "vibrant lifestyle photography, natural light",
            "dark dramatic lighting, high contrast, moody atmosphere",
            "flat lay aerial perspective, colourful props",
            "close-up macro shot, shallow depth of field",
        ]
        variation = style_variations[(image_index - 1) % len(style_variations)]

        if fast_mode:
            prompt_data = {
                "prompt": (
                    f"{topic}. {variation}. Photorealistic, professional, 4K, "
                    "no text, no watermarks, social media ready"
                ),
                "style": "photorealistic",
                "mood": "professional",
                "negative_prompt": "blurry, low quality, text, watermark, cartoon, distorted",
            }
        elif base_prompt:
            # Reuse a prompt crafted once for the whole batch — no extra GPT-4o call
            prompt_data = {
                "prompt": f"{base_prompt}. Style: {variation}",
                "style": "photorealistic",
                "mood": "professional",
                "negative_prompt": "blurry, low quality, text, watermark, cartoon, distorted",
            }
        else:
            prompt_data = self.generate_image_prompt(topic, platform)
            # Inject variation into prompt for diversity
            prompt_data["prompt"] = (
                prompt_data.get("prompt", topic) + f". Style: {variation}"
            )

        image_prompt = prompt_data.get(
            "prompt",
            f"Professional marketing image about {topic}, {variation}",
        )

        w, h = self._resolve_dimensions(ratio, platform)
        # Segmind max 1536
        w = min(w, 1536)
        h = min(h, 1536)

        print(f"    🖼️  Segmind [{platform.upper()}] {w}×{h} (ratio {ratio or 'default'}) img#{image_index}...")
        try:
            result = self.segmind.generate_image(
                prompt=image_prompt,
                negative_prompt=prompt_data.get(
                    "negative_prompt",
                    "blurry, low quality, text, watermark, cartoon, distorted"
                ),
                width=w,
                height=h,
                filename=f"segmind_{platform}_{uuid.uuid4().hex[:8]}.png",
            )

            if result.get("status") == "success":
                local_path = result.get("local_path")
                image_url = result.get("image_url")
                if local_path:
                    filename = os.path.basename(local_path)
                    image_url = f"http://localhost:8000/output/{filename}"
                return {
                    "platform": platform,
                    "topic": topic,
                    "image_prompt": image_prompt,
                    "image_url": image_url,
                    "local_path": local_path,
                    "ratio": ratio or PLATFORM_RATIOS.get(platform, "1:1"),
                    "dimensions": f"{w}x{h}",
                    "style": prompt_data.get("style", "photorealistic"),
                    "mood": prompt_data.get("mood", "professional"),
                    "index": image_index,
                }
            else:
                raise Exception(result.get("error", "Unknown Segmind error"))

        except Exception as e:
            print(f"    ⚠️  Segmind failed: {e} — falling back to DALL-E...")
            return self._dalle_fallback(topic, platform, image_prompt, prompt_data, w, h, ratio, image_index)

    def _dalle_fallback(
        self, topic, platform, image_prompt, prompt_data, w, h, ratio, image_index
    ) -> dict:
        """DALL-E gpt-image-2 fallback when Segmind fails."""
        try:
            response = self.openai.images.generate(
                model="gpt-image-2",
                prompt=image_prompt,
                size="1024x1024",
                n=1,
            )
            filename = f"dalle_{platform}_{uuid.uuid4().hex[:8]}.png"
            local_path = os.path.join(self.output_dir, filename)

            b64_json = getattr(response.data[0], "b64_json", None)
            image_url = getattr(response.data[0], "url", None)

            if b64_json:
                img_bytes = base64.b64decode(b64_json)
                with open(local_path, "wb") as f:
                    f.write(img_bytes)
            elif image_url:
                import requests as req
                resp = req.get(image_url, timeout=30)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
            else:
                raise Exception("No image data in DALL-E response")

            local_url = f"http://localhost:8000/output/{filename}"
            return {
                "platform": platform,
                "topic": topic,
                "image_prompt": image_prompt,
                "image_url": local_url,
                "local_path": local_path,
                "ratio": ratio or PLATFORM_RATIOS.get(platform, "1:1"),
                "dimensions": f"{w}x{h}",
                "style": prompt_data.get("style", "photorealistic"),
                "mood": prompt_data.get("mood", "professional"),
                "index": image_index,
                "provider": "dalle",
            }
        except Exception as dalle_err:
            print(f"    ❌ DALL-E fallback also failed: {dalle_err}")
            return {
                "platform": platform,
                "topic": topic,
                "image_prompt": image_prompt,
                "image_url": None,
                "local_path": None,
                "ratio": ratio,
                "index": image_index,
                "error": str(dalle_err),
            }

    def generate_multiple_images(
        self,
        topic: str,
        platform: str = "default",
        count: int = 5,
        ratio: str = "",
        fast_mode: bool = False,
        max_workers: int = 4,
    ) -> list[dict]:
        """
        Generate `count` images in parallel with style variations.
        Returns a list of image result dicts sorted by index.
        """
        results: dict[int, dict] = {}

        def _gen(idx: int):
            return idx, self.generate_image(
                topic=topic,
                platform=platform,
                fast_mode=fast_mode,
                ratio=ratio,
                image_index=idx,
            )

        with ThreadPoolExecutor(max_workers=min(count, max_workers)) as executor:
            futures = {executor.submit(_gen, i + 1): i + 1 for i in range(count)}
            for fut in as_completed(futures):
                try:
                    idx, result = fut.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[fut]
                    results[idx] = {"index": idx, "image_url": None, "error": str(e)}

        return [results[i] for i in sorted(results.keys())]

    def generate_image_set(
        self,
        topic: str,
        platform: str = "default",
        ratios: list = None,
        count: int = 5,
        fast_mode: bool = False,
        max_workers: int = 6,
    ) -> list[dict]:
        """
        Generate `count` images for EACH ratio, all in a SINGLE parallel pool.

        Optimizations vs. the old per-ratio loop:
          - Crafts the rich image prompt ONCE (one GPT-4o call) and reuses it for
            every image with local style variations — instead of one GPT-4o call
            per image (which was count × ratios redundant calls).
          - Runs every (ratio, index) job concurrently rather than finishing one
            ratio's batch before starting the next.

        Returns a flat list of image dicts, each tagged with its ratio.
        """
        ratios = [r for r in (ratios or ["1:1"])] or ["1:1"]

        # ── Craft ONE base prompt for the whole set ──────────────────────
        base_prompt = None
        if not fast_mode:
            try:
                pd = self.generate_image_prompt(topic, platform)
                base_prompt = pd.get("prompt")
                print(f"    🧠 Base image prompt crafted once for {len(ratios)} ratio(s) × {count}")
            except Exception as e:
                print(f"    ⚠️  Base prompt crafting failed ({e}) — using fast prompts")
                base_prompt = None

        # ── Build every (ratio, index) job and run them all at once ──────
        jobs = [(ratio, i + 1) for ratio in ratios for i in range(count)]
        results: dict = {}

        def _gen(job):
            ratio, idx = job
            img = self.generate_image(
                topic=topic,
                platform=platform,
                fast_mode=fast_mode,
                ratio=ratio,
                image_index=idx,
                base_prompt=base_prompt,
            )
            img["ratio"] = ratio
            return job, img

        with ThreadPoolExecutor(max_workers=min(len(jobs), max_workers)) as executor:
            futures = {executor.submit(_gen, j): j for j in jobs}
            for fut in as_completed(futures):
                try:
                    job, img = fut.result()
                    results[job] = img
                except Exception as e:
                    job = futures[fut]
                    results[job] = {"index": job[1], "ratio": job[0], "image_url": None, "error": str(e)}

        return [results[j] for j in jobs if j in results]

    def generate_images_for_all(self, topic: str, platforms: list) -> dict:
        """Generate one image per platform using platform default ratios."""
        images = {}
        for platform in platforms:
            images[platform] = self.generate_image(topic, platform)
        return images
