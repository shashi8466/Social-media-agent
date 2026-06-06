"""
Segmind Agent — Segmind AI Platform integration.

Uses Segmind's unified API to:
  - Generate images via Kling / SDXL / Stable Diffusion models
  - Stitch scene images + audio into a final video (Video Stitch model)
  - Optionally generate video clips (Kling, Wan, Veo) per scene

API: https://api.segmind.com/v1/
Auth: x-api-key header
Key: STITCH_API_KEY from .env
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SEGMIND_BASE_URL = "https://api.segmind.com/v1"

# Available image generation models on Segmind
IMAGE_MODELS = {
    "sdxl": "sdxl1.0-txt2img",
    "sd3": "sd3-txt2img",
    "flux": "flux-schnell",
    "portrait": "portrait-diffusion",
    "realistic": "realistic-vision-v6",
}

# Default: fast, high-quality
DEFAULT_IMAGE_MODEL = "sdxl1.0-txt2img"

# Video stitch endpoint
VIDEO_STITCH_MODEL = "video-stitch"


class SegmindAgent:
    """
    Segmind Agent — Segmind AI Platform (formerly Stitch).

    Capabilities:
      1. generate_image()    — Generate images via SDXL/Flux/Kling on Segmind
      2. stitch_video()      — Use Video Stitch model to assemble MP4 from clips
      3. check_health()      — Verify API key and connectivity

    Authentication: STITCH_API_KEY environment variable
    """

    def __init__(self):
        self.api_key = os.getenv("STITCH_API_KEY")
        if not self.api_key:
            raise RuntimeError("STITCH_API_KEY not set in environment")

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, text, watermark, cartoon, distorted",
        width: int = 1024,
        height: int = 1024,
        model: str = DEFAULT_IMAGE_MODEL,
        filename: str = None,
    ) -> dict:
        """
        Generate an image using Segmind's API.

        Args:
            prompt: Text description of the image
            negative_prompt: What to avoid in the image
            width/height: Image dimensions (default 1024x1024)
            model: Segmind model slug (default: sdxl1.0-txt2img)
            filename: Save filename (optional)

        Returns:
            dict with image_url or local_path
        """
        url = f"{SEGMIND_BASE_URL}/{model}"
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "samples": 1,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "img_width": width,
            "img_height": height,
        }

        try:
            print(f"    🎨 Segmind [{model}] generating image...")
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()

            # Segmind returns image bytes directly
            if response.headers.get("content-type", "").startswith("image/"):
                if filename:
                    img_path = os.path.join(self.output_dir, filename)
                else:
                    import uuid
                    img_path = os.path.join(self.output_dir, f"segmind_{uuid.uuid4().hex[:8]}.png")

                with open(img_path, "wb") as f:
                    f.write(response.content)

                print(f"    ✅ Segmind image saved: {img_path}")
                return {
                    "local_path": img_path,
                    "image_url": None,
                    "model": model,
                    "prompt": prompt,
                    "status": "success",
                }

            # Some models return JSON with URL
            try:
                data = response.json()
                return {
                    "image_url": data.get("image") or data.get("url") or data.get("output"),
                    "local_path": None,
                    "model": model,
                    "prompt": prompt,
                    "status": "success",
                    "raw": data,
                }
            except Exception:
                pass

            return {"status": "error", "error": "Unexpected response format", "model": model}

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            print(f"    ⚠️  Segmind image failed: {error_msg}")
            return {"status": "error", "error": error_msg, "model": model}
        except Exception as e:
            print(f"    ⚠️  Segmind image failed: {e}")
            return {"status": "error", "error": str(e), "model": model}

    def stitch_video(
        self,
        video_urls: list,
        audio_url: str = None,
        output_filename: str = None,
    ) -> dict:
        """
        Stitch multiple video/image clips into a single MP4 using Segmind's Video Stitch API.

        Args:
            video_urls: List of video or image URLs to stitch
            audio_url: Optional audio track URL to overlay
            output_filename: Local filename to save the result

        Returns:
            dict with video_path or video_url
        """
        url = f"{SEGMIND_BASE_URL}/{VIDEO_STITCH_MODEL}"
        payload = {
            "input_videos": video_urls,
        }
        if audio_url:
            payload["audio_url"] = audio_url

        try:
            print(f"    🎬 Segmind Video Stitch: stitching {len(video_urls)} clips...")
            response = requests.post(url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()

            # Save MP4 if returned as bytes
            if "video" in response.headers.get("content-type", ""):
                fname = output_filename or "segmind_video.mp4"
                video_path = os.path.join(self.output_dir, fname)
                with open(video_path, "wb") as f:
                    f.write(response.content)
                print(f"    ✅ Segmind video saved: {video_path}")
                return {"video_path": video_path, "status": "success"}

            data = response.json()
            return {
                "video_url": data.get("video") or data.get("url") or data.get("output"),
                "status": "success",
                "raw": data,
            }

        except Exception as e:
            print(f"    ⚠️  Segmind Video Stitch failed: {e}")
            return {"status": "error", "error": str(e)}

    def generate_scene_images(self, scenes: list, topic: str) -> dict:
        """
        Generate one image per scene using Segmind.

        Returns dict keyed by scene_number → image result
        """
        results = {}
        for scene in scenes:
            scene_num = scene.get("scene_number", 1)
            visual_direction = scene.get("visual_direction", topic)

            # Build a rich Segmind prompt from visual direction
            prompt = (
                f"{visual_direction}, "
                f"cinematic lighting, ultra detailed, 4K, professional photography, "
                f"deep navy and teal color palette, tech company brand aesthetic, "
                f"no text, no watermarks"
            )

            print(f"    🖼️  Segmind: scene {scene_num}...")
            result = self.generate_image(
                prompt=prompt,
                filename=f"segmind_scene_{scene_num}.png",
                width=1024,
                height=1024,
            )
            results[scene_num] = {**result, "visual_direction": visual_direction}

        return results

    def check_health(self) -> dict:
        """Test Segmind API connectivity with a minimal request"""
        try:
            # Use a fast model for the health check
            result = self.generate_image(
                prompt="test image blue gradient abstract",
                filename="segmind_health_check.png",
                model=DEFAULT_IMAGE_MODEL,
            )
            return {
                "status": "healthy" if result.get("status") == "success" else "error",
                "api": "Segmind",
                "detail": result,
            }
        except Exception as e:
            return {"status": "error", "api": "Segmind", "error": str(e)}
