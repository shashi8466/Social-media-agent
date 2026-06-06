"""
Video Editor Agent — Assembles scene images + voiceover audio into a final MP4.

Produces MOTION-RICH, cinematic clips (not a static slideshow):
  - Per-scene Ken Burns motion (zoom in/out, pan left/right/up/down) via FFmpeg
    zoompan, cycled so consecutive scenes feel different.
  - Smooth fade-in / fade-out transitions between scenes.
  - Branded animated text overlays that fade in with each scene.
  - Dynamic output dimensions for 9:16, 16:9, 1:1 and 4:5 aspect ratios.

Pipeline:
  1. Verify / download scene images (local_path preferred, then image_url)
  2. Add PIL text overlays to each image (hook / scene text / CTA + progress dots)
  3. Encode each overlaid PNG → H.264 clip with Ken Burns motion + fades
  4. Concatenate clips with FFmpeg concat demuxer
  5. Mux voiceover MP3 as AAC audio track (padded/trimmed to exact reel duration)
  6. Validate output (existence + minimum file size)
  7. Clean up per-scene temp files

If AI text-to-video is enabled and available it can replace step 3 per scene;
otherwise these advanced motion effects are the reliable fallback.

No MoviePy dependency — uses FFmpeg directly so API version differences
cannot cause silent black-frame failures.
"""

import os
import re
import math
import shutil
import subprocess
import textwrap
import requests
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
FPS = 24

# Aspect-ratio → (width, height). Even numbers (required by H.264 yuv420p).
RATIO_DIMENSIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1":  (1080, 1080),
    "4:5":  (1080, 1350),
}
DEFAULT_RATIO = "9:16"

# Ken Burns motion patterns, cycled across scenes for variety
MOTION_EFFECTS = ["zoom_in", "pan_right", "zoom_out", "pan_left", "pan_up", "pan_down"]

FADE_DUR = 0.35  # seconds for scene fade in/out


def _even(n: int) -> int:
    """Round to the nearest even integer (H.264 yuv420p requires even dims)."""
    n = int(round(n))
    return n if n % 2 == 0 else n + 1


# ── FFmpeg discovery ──────────────────────────────────────────────────────────

def _find_ffmpeg() -> str | None:
    """Return the path to the ffmpeg binary, or None if not found."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    try:
        from moviepy.config import get_setting
        exe = get_setting("FFMPEG_BINARY")
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    for candidate in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None


# ── Agent class ───────────────────────────────────────────────────────────────

class VideoEditorAgent:
    """
    Stitches Segmind/DALL-E scene images + TTS audio into a motion-rich MP4 Reel
    using FFmpeg subprocess calls (no MoviePy) to avoid API-version issues.
    """

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.fps = FPS
        # Default dimensions (overridden per-call by aspect_ratio)
        self.vw, self.vh = RATIO_DIMENSIONS[DEFAULT_RATIO]
        self.ffmpeg = _find_ffmpeg()
        if self.ffmpeg:
            print(f"    ✅ FFmpeg found: {self.ffmpeg}")
        else:
            print("    ❌ FFmpeg not found — video assembly will be skipped")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _set_dimensions(self, aspect_ratio: str):
        """Resolve output dimensions from the selected aspect ratio."""
        self.vw, self.vh = RATIO_DIMENSIONS.get(aspect_ratio or DEFAULT_RATIO,
                                                 RATIO_DIMENSIONS[DEFAULT_RATIO])

    def measure_duration(self, path: str) -> float | None:
        """Return media duration in seconds (via ffmpeg), or None."""
        if not path or not os.path.exists(path) or not self.ffmpeg:
            return None
        try:
            proc = subprocess.run([self.ffmpeg, "-i", path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            err = proc.stderr.decode("utf-8", errors="replace")
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", err)
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception as e:
            print(f"    ⚠️  Duration probe failed for {os.path.basename(path)}: {e}")
        return None

    def _run_ffmpeg(self, args: list, label: str = "") -> tuple:
        """Run ``ffmpeg <args>``; return (success, stderr)."""
        cmd = [self.ffmpeg] + args
        print(f"    🔧 FFmpeg [{label}]: {' '.join(str(a) for a in cmd)}")
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            stderr = proc.stderr.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                print(f"    ❌ FFmpeg [{label}] FAILED (rc={proc.returncode})")
                for line in stderr.splitlines()[-20:]:
                    print(f"       {line}")
                return False, stderr
            print(f"    ✅ FFmpeg [{label}] OK")
            return True, stderr
        except subprocess.TimeoutExpired:
            msg = f"FFmpeg [{label}] timed out after 300s"
            print(f"    ❌ {msg}")
            return False, msg
        except Exception as exc:
            msg = str(exc)
            print(f"    ❌ FFmpeg [{label}] exception: {msg}")
            return False, msg

    def _download_image(self, url: str, filename: str) -> str | None:
        path = os.path.join(self.output_dir, filename)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"    ♻️  Cached: {filename}")
            return path
        print(f"    📥 Downloading: {url[:80]}")
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(path, "wb") as fh:
                fh.write(resp.content)
            print(f"    ✅ Saved {filename} ({os.path.getsize(path):,} bytes)")
            return path
        except Exception as exc:
            print(f"    ⚠️  Download failed ({url[:60]}): {exc}")
            return None

    def _find_bg_music(self) -> str | None:
        """
        Locate an optional background-music track. Enable by either:
          - setting env BG_MUSIC_PATH to an audio file, or
          - dropping a file at backend/assets/bgmusic.mp3 (or background.mp3 / music.mp3)
        Returns the path, or None (music is skipped if absent).
        """
        env = os.getenv("BG_MUSIC_PATH")
        if env and os.path.exists(env):
            return env
        assets_dir = os.path.join(os.path.dirname(self.output_dir), "assets")
        for name in ("bgmusic.mp3", "background.mp3", "music.mp3"):
            p = os.path.join(assets_dir, name)
            if os.path.exists(p):
                return p
        return None

    def _create_fallback_image(self, scene_number: int, color: tuple = (10, 22, 40)) -> str:
        path = os.path.join(self.output_dir, f"scene_{scene_number}_fallback.png")
        Image.new("RGB", (self.vw, self.vh), color=color).save(path)
        print(f"    🎨 Fallback image created for scene {scene_number}")
        return path

    def _add_text_overlay(
        self,
        image_path: str,
        caption: str,
        scene_number: int,
        total_scenes: int,
    ) -> str:
        """
        Composite a SUBTITLE caption (the scene's spoken narration) + branding
        onto a scene image. The caption is wrapped, drawn in a semi-transparent
        rounded box with outlined white text at the bottom — i.e. a real, legible
        subtitle synchronized to this scene's time window.
        """
        out_path = os.path.join(self.output_dir, f"scene_{scene_number}_overlay.png")
        w, h = self.vw, self.vh
        vsize = (w, h)

        try:
            img = Image.open(image_path).convert("RGB")
            orig = img.size
            img = self._cover_resize(img, w, h)
            print(f"    🖼️  Scene {scene_number}: {orig} → {vsize}")
        except Exception as exc:
            print(f"    ⚠️  Cannot open {image_path}: {exc} — blank frame")
            img = Image.new("RGB", vsize, (10, 22, 40))

        # Subtle bottom gradient for extra legibility
        grad_h = int(h * 0.30)
        overlay = Image.new("RGBA", vsize, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i in range(grad_h):
            alpha = int(150 * (i / grad_h))
            od.rectangle([(0, h - grad_h + i), (w, h - grad_h + i + 1)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        scale = w / 1080.0
        fs_cap = max(28, int(44 * scale))
        fs_tiny = max(16, int(24 * scale))
        try:
            bold = "C:/Windows/Fonts/arialbd.ttf"
            font_cap = ImageFont.truetype(bold, fs_cap)
            font_tiny = ImageFont.truetype(bold, fs_tiny)
        except Exception:
            font_cap = font_tiny = ImageFont.load_default()

        # Progress dots (top centre)
        dot_y = int(h * 0.03)
        dot_d = max(8, int(12 * scale))
        spacing = max(16, int(24 * scale))
        dot_x = (w - total_scenes * spacing) // 2
        for i in range(total_scenes):
            x = dot_x + i * spacing
            col = (0, 212, 255) if i < scene_number else (100, 130, 160)
            draw.ellipse([x, dot_y, x + dot_d, dot_y + dot_d], fill=col)

        # ── Subtitle caption ─────────────────────────────────────────────
        text = (caption or "").strip()
        if text:
            wrap_w = max(16, int(26 / scale)) if scale < 1 else 26
            lines = textwrap.wrap(text, width=wrap_w)[:3]  # cap at 3 lines
            lh = fs_cap + int(14 * scale)
            block_h = len(lines) * lh
            # Position caption block in the lower third, above the watermark
            ty0 = h - block_h - int(h * 0.08)

            # Measure widest line for the background box
            max_lw = 0
            for line in lines:
                bb = draw.textbbox((0, 0), line, font=font_cap)
                max_lw = max(max_lw, bb[2] - bb[0])
            pad_x, pad_y = int(28 * scale), int(18 * scale)
            box_x0 = (w - max_lw) // 2 - pad_x
            box_x1 = (w + max_lw) // 2 + pad_x
            box_y0 = ty0 - pad_y
            box_y1 = ty0 + block_h + pad_y - int(4 * scale)

            # Semi-transparent rounded caption box
            box_layer = Image.new("RGBA", vsize, (0, 0, 0, 0))
            bd = ImageDraw.Draw(box_layer)
            radius = int(18 * scale)
            bd.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=radius, fill=(0, 0, 0, 150))
            img = Image.alpha_composite(img.convert("RGBA"), box_layer).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Outlined white caption text
            outline = max(2, int(3 * scale))
            ty = ty0
            for line in lines:
                bb = draw.textbbox((0, 0), line, font=font_cap)
                lw = bb[2] - bb[0]
                lx = (w - lw) // 2
                draw.text((lx, ty), line, font=font_cap, fill=(255, 255, 255),
                          stroke_width=outline, stroke_fill=(0, 0, 0))
                ty += lh

        # Watermark
        draw.text((int(40 * scale), h - int(58 * scale)), "GigaTech AI", font=font_tiny, fill=(0, 212, 255))

        img.save(out_path, "PNG")
        print(f"    ✅ Overlay saved: scene_{scene_number}_overlay.png ({os.path.getsize(out_path):,} bytes)")
        return out_path

    @staticmethod
    def _cover_resize(img: "Image.Image", w: int, h: int) -> "Image.Image":
        """Resize+centre-crop so the image fully covers w×h (no letterboxing)."""
        src_w, src_h = img.size
        scale = max(w / src_w, h / src_h)
        new_w, new_h = int(math.ceil(src_w * scale)), int(math.ceil(src_h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        return img.crop((left, top, left + w, top + h))

    def _motion_vf(self, effect: str, frames: int, duration: float) -> str:
        """
        Build the FFmpeg -vf chain for a Ken Burns motion clip.

        The overlaid image (already w×h) is pre-scaled larger so the zoompan
        crop window can move/zoom smoothly without jitter, then rendered back
        to exact output dimensions, with fade-in/out for scene transitions.
        """
        w, h, fps = self.vw, self.vh, self.fps
        frames = max(2, frames)
        pw, ph = _even(w * 1.3), _even(h * 1.3)   # pre-scale canvas (same aspect)
        d = frames

        cx = "iw/2-(iw/zoom/2)"   # centre crop horizontally
        cy = "ih/2-(ih/zoom/2)"   # centre crop vertically

        if effect == "zoom_in":
            z, x, y = "min(1+0.0016*on,1.25)", cx, cy
        elif effect == "zoom_out":
            z, x, y = "max(1.25-0.0016*on,1.0)", cx, cy
        elif effect == "pan_right":
            z, x, y = "1.18", f"(iw-iw/zoom)*on/{d-1}", cy
        elif effect == "pan_left":
            z, x, y = "1.18", f"(iw-iw/zoom)*(1-on/{d-1})", cy
        elif effect == "pan_up":
            z, x, y = "1.18", cx, f"(ih-ih/zoom)*(1-on/{d-1})"
        elif effect == "pan_down":
            z, x, y = "1.18", cx, f"(ih-ih/zoom)*on/{d-1}"
        else:
            z, x, y = "min(1+0.0014*on,1.2)", cx, cy

        fout = max(0.0, duration - FADE_DUR)
        return (
            f"scale={pw}:{ph},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={d}:s={w}x{h}:fps={fps},"
            f"fade=t=in:st=0:d={FADE_DUR},"
            f"fade=t=out:st={fout:.2f}:d={FADE_DUR},"
            f"format=yuv420p,setsar=1"
        )

    def _static_vf(self) -> str:
        """Fallback static (no-motion) chain if zoompan is unavailable."""
        w, h = self.vw, self.vh
        return (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
        )

    def _encode_scene_clip(
        self, image_path: str, duration: float, clip_path: str, scene_num: int, effect: str
    ) -> bool:
        """Encode a still image as a motion (Ken Burns) H.264 clip."""
        frames = max(2, int(round(duration * self.fps)))

        # Attempt motion encode; fall back to static on failure (old FFmpeg, etc.)
        for vf, kind in ((self._motion_vf(effect, frames, duration), f"motion:{effect}"),
                         (self._static_vf(), "static")):
            ok, _ = self._run_ffmpeg([
                "-y",
                "-loop", "1",
                "-i", image_path,
                "-t", str(duration),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                clip_path,
            ], label=f"scene_{scene_num}_{kind}")
            if ok and os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000:
                print(f"    ✅ Scene {scene_num} clip ({kind}): {os.path.getsize(clip_path):,} bytes")
                return True
            print(f"    ⚠️  Scene {scene_num} {kind} encode failed — trying fallback")
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def assemble_video(
        self,
        scenes: list,
        scene_images: dict,
        audio_path: str,
        hook_line: str,
        cta: str,
        project_id: str,
        total_duration: float = None,
        aspect_ratio: str = "9:16",
    ) -> str | None:
        """
        Assemble all scene clips + voiceover into a motion-rich final MP4.

        Each scene becomes a Ken Burns motion clip (zoom/pan) with fade
        transitions. Output dimensions follow `aspect_ratio`. The final length is
        determined by the scene clips (which sum to the selected reel duration);
        the voiceover is padded/trimmed to match so the video is never truncated.

        Returns the absolute path to the finished MP4, or None on failure.
        Any exception is re-raised so the caller can record it in pipeline_steps.
        """
        if not self.ffmpeg:
            raise RuntimeError(
                "FFmpeg not found. Install FFmpeg and ensure it is on PATH "
                "(or install imageio-ffmpeg: pip install imageio-ffmpeg)."
            )

        self._set_dimensions(aspect_ratio)

        print(f"\n    {'='*50}")
        print(f"    🎬 VIDEO EDITOR — project {project_id}")
        print(f"    🔧 FFmpeg  : {self.ffmpeg}")
        print(f"    📐 Output  : {self.vw}x{self.vh} ({aspect_ratio})")
        print(f"    🎞  Motion  : Ken Burns zoom/pan + fade transitions")
        print(f"    🎵 Audio   : {audio_path}")
        print(f"    📊 Scenes  : {len(scenes)}")
        print(f"    {'='*50}\n")

        output_path   = os.path.join(self.output_dir, f"video_{project_id}.mp4")
        temp_vid_path = os.path.join(self.output_dir, f"temp_video_{project_id}.mp4")
        concat_path   = os.path.join(self.output_dir, f"concat_{project_id}.txt")
        total_scenes  = len(scenes)
        clip_paths    = []

        # ── Phase A: Build per-scene motion clips ─────────────────────────
        print("    --- Phase A: Scene clips (motion) ---")
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            duration  = float(scene.get("duration_sec", 7))
            is_first  = idx == 0
            is_last   = idx == total_scenes - 1
            effect    = MOTION_EFFECTS[idx % len(MOTION_EFFECTS)]

            # Subtitle caption = the spoken narration for this scene (synced to
            # its time window). Fall back to on-screen text, then hook/CTA.
            caption = (scene.get("dialogue") or scene.get("on_screen_text") or "").strip()
            if not caption:
                caption = hook_line if is_first else (cta if is_last else "")

            print(f"\n    Scene {scene_num}/{total_scenes}  duration={duration}s  motion={effect}")

            img_data   = scene_images.get(scene_num, scene_images.get(str(scene_num), {}))
            image_path = None
            local = img_data.get("local_path")
            url   = img_data.get("image_url")

            if local and os.path.exists(local):
                image_path = local
                print(f"    ✅ Using local image: {local} ({os.path.getsize(local):,} bytes)")
            elif url:
                image_path = self._download_image(url, f"scene_{scene_num}_raw.png")

            if not image_path or not os.path.exists(image_path):
                print(f"    🎨 No valid image — using fallback for scene {scene_num}")
                fallback_colors = [
                    (10, 22, 40), (8, 16, 32), (15, 30, 50),
                    (12, 25, 45), (6, 18, 35), (10, 22, 40),
                ]
                image_path = self._create_fallback_image(
                    scene_num, fallback_colors[idx % len(fallback_colors)]
                )

            overlaid = self._add_text_overlay(image_path, caption, scene_num, total_scenes)

            clip_path = os.path.join(self.output_dir, f"clip_{project_id}_scene{scene_num}.mp4")
            if self._encode_scene_clip(overlaid, duration, clip_path, scene_num, effect):
                clip_paths.append(clip_path)
            else:
                print(f"    ⚠️  Scene {scene_num} encoding failed — skipping")

        if not clip_paths:
            raise RuntimeError("No scene clips were created — cannot assemble video.")

        # ── Phase B: Concatenate clips ────────────────────────────────────
        print(f"\n    --- Phase B: Concat {len(clip_paths)} clips ---")
        with open(concat_path, "w", encoding="utf-8") as fh:
            for cp in clip_paths:
                fh.write(f"file '{cp}'\n")

        ok, err = self._run_ffmpeg([
            "-y", "-f", "concat", "-safe", "0",
            "-i", concat_path, "-c", "copy", temp_vid_path,
        ], label="concat")
        if not ok or not os.path.exists(temp_vid_path):
            raise RuntimeError(f"Concatenation failed: {err}")
        print(f"    ✅ Concatenated: {os.path.getsize(temp_vid_path):,} bytes")

        # ── Phase C: Mux audio (pad/trim to exact reel length) ────────────
        # DO NOT use -shortest (it would cut the video to a short voiceover).
        # Pad audio with silence (apad) and force exact length with -t.
        video_duration = sum(float(s.get("duration_sec", 7)) for s in scenes)
        if total_duration and total_duration > 0:
            video_duration = float(total_duration)
        bg_music = self._find_bg_music()
        dur = f"{video_duration:.3f}"
        print(f"\n    --- Phase C: Audio mux (faststart, target {video_duration:.1f}s, "
              f"music={'yes' if bg_music else 'no'}) ---")

        muxed = False

        if audio_path and os.path.exists(audio_path):
            print(f"    🎵 Voiceover: {audio_path} ({os.path.getsize(audio_path):,} bytes)")

            # Voiceover + background music (music looped & ducked under the VO)
            if bg_music:
                print(f"    🎶 Background music: {bg_music}")
                ok, _ = self._run_ffmpeg([
                    "-y",
                    "-i", temp_vid_path,
                    "-stream_loop", "-1", "-i", bg_music,
                    "-i", audio_path,
                    "-filter_complex",
                    "[2:a]apad[vo];[1:a]volume=0.12[bg];"
                    "[vo][bg]amix=inputs=2:duration=first,volume=1.8[a]",
                    "-map", "0:v:0", "-map", "[a]",
                    "-t", dur,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    output_path,
                ], label="mux_voice_music")
                muxed = ok and os.path.exists(output_path)

            # Voiceover only (pad with silence, force exact length — NO -shortest)
            if not muxed:
                ok, _ = self._run_ffmpeg([
                    "-y",
                    "-i", temp_vid_path,
                    "-i", audio_path,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-af", "apad",
                    "-t", dur,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    output_path,
                ], label="mux_voice")
                muxed = ok and os.path.exists(output_path)

        elif bg_music:
            # No voiceover but we do have music — use the music bed
            print(f"    🎶 Background music only: {bg_music}")
            ok, _ = self._run_ffmpeg([
                "-y",
                "-i", temp_vid_path,
                "-stream_loop", "-1", "-i", bg_music,
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", dur,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                output_path,
            ], label="mux_music_only")
            muxed = ok and os.path.exists(output_path)

        # Final fallback — video only
        if not muxed:
            print("    ⚠️  No audio muxed — writing video-only output (faststart)")
            ok, _ = self._run_ffmpeg([
                "-y", "-i", temp_vid_path,
                "-c", "copy", "-movflags", "+faststart", output_path,
            ], label="faststart_videoonly")
            if not ok or not os.path.exists(output_path):
                shutil.copy2(temp_vid_path, output_path)

        # ── Phase D: Validate output ──────────────────────────────────────
        print(f"\n    --- Phase D: Validation ---")
        if not os.path.exists(output_path):
            raise RuntimeError(f"Output file was not created: {output_path}")

        final_size = os.path.getsize(output_path)
        print(f"    📁 Path : {output_path}")
        print(f"    📊 Size : {final_size:,} bytes ({final_size / 1024 / 1024:.2f} MB)")
        if final_size < 50_000:
            raise RuntimeError(
                f"Output MP4 is only {final_size} bytes — likely corrupt or empty. "
                "Check FFmpeg logs above for encoding errors."
            )

        probe, _ = self._run_ffmpeg(["-v", "error", "-i", output_path, "-f", "null", "-"], label="probe")
        print("    ✅ MP4 stream probe passed" if probe else "    ⚠️  Stream probe reported issues")

        # ── Cleanup ───────────────────────────────────────────────────────
        for path in [temp_vid_path, concat_path] + clip_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        print(f"\n    🎉 Final MP4: {output_path}")
        return output_path
