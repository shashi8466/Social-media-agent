"""
Voice Agent — Generates two outputs:
  1. OpenAI-crafted voiceover script (JSON with timecodes, tone, emphasis)
  2. OpenAI TTS audio (MP3) for the complete voiceover narration
"""

import os
import json
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class VoiceAgent:
    """
    Voice Agent — Two-step pipeline:
      1. OpenAI writes a polished voiceover script with timecodes and speaker notes
      2. OpenAI TTS (tts-1, nova voice) synthesizes the audio as MP3
    """

    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.tts_model = "tts-1"
        self.tts_voice = "nova"  # nova = energetic, professional female voice
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "output"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_prompt(self) -> str:
        with open(os.path.join(self.prompts_dir, "voiceover.txt"), "r", encoding="utf-8") as f:
            return f.read()

    def _extract_json(self, text: str) -> dict:
        """Robustly extract JSON from OpenAI's response"""
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

        return {"voiceover_text": text, "tone": "confident", "pace": "medium-fast",
                "key_emphasis_words": [], "estimated_word_count": 100,
                "estimated_duration_sec": 45, "speaker_notes": "", "scene_timecodes": []}

    def generate_voiceover_script(self, topic: str, scenes: list, target_duration: int = 45) -> dict:
        """Step 1: Use OpenAI to write a polished voiceover script sized to target_duration."""
        scene_dialogue = "\n".join(
            f"Scene {s.get('scene_number', i+1)} ({s.get('duration_sec', 7)}s): {s.get('dialogue', '')}"
            for i, s in enumerate(scenes)
        )

        # TTS at speed 1.1 narrates ~2.5 words/sec → size the script to the reel.
        target_words = max(20, int(round(target_duration * 2.5)))

        prompt = self._load_prompt()
        prompt = prompt.replace("{topic}", topic)
        prompt = prompt.replace("{scene_dialogue}", scene_dialogue)
        prompt = prompt.replace("{duration}", str(target_duration))
        prompt = prompt.replace("{word_count}", str(target_words))

        response = self.openai.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._extract_json(response.choices[0].message.content)


    def generate_audio(self, voiceover_text: str, project_id: str) -> str:
        """
        Step 2: Use OpenAI TTS to synthesize the voiceover as MP3.

        Uses the non-deprecated streaming-response API and VALIDATES the output
        file size, retrying / falling back to the legacy call if the first
        attempt produces a too-small (truncated/empty) file. This prevents the
        "silent video" symptom where only ~2s of audio was written.
        """
        audio_path = os.path.join(self.output_dir, f"voiceover_{project_id}.mp3")
        text = (voiceover_text or "").strip()
        if not text:
            print("    ⚠️  No voiceover text to synthesize")
            return None

        def _size() -> int:
            return os.path.getsize(audio_path) if os.path.exists(audio_path) else 0

        # Attempt 1 — modern streaming response API (reliable full write)
        try:
            with self.openai.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                speed=1.05,
            ) as response:
                response.stream_to_file(audio_path)
            print(f"    🎙️  Audio saved (streaming): {audio_path} ({_size():,} bytes)")
            if _size() > 3000:
                return audio_path
            print("    ⚠️  Audio file suspiciously small — retrying with legacy API")
        except Exception as e:
            print(f"    ⚠️  Streaming TTS failed: {e} — trying legacy API")

        # Attempt 2 — legacy create().stream_to_file()
        try:
            response = self.openai.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                speed=1.05,
            )
            response.stream_to_file(audio_path)
            print(f"    🎙️  Audio saved (legacy): {audio_path} ({_size():,} bytes)")
        except Exception as e:
            print(f"    ⚠️  Legacy TTS also failed: {e}")

        return audio_path if _size() > 3000 else None

    def run(self, topic: str, scenes: list, project_id: str, target_duration: int = 45) -> dict:
        """Full voice pipeline: script + audio synthesis"""
        print(f"    📝 OpenAI writing voiceover script (target {target_duration}s)...")
        script = self.generate_voiceover_script(topic, scenes, target_duration=target_duration)

        voiceover_text = (script.get("voiceover_text") or "").strip()

        # Guard against a too-short narration (the cause of ~2s silent audio):
        # if the model returned very little, stitch the scene dialogues together
        # so the voiceover fills the reel.
        min_words = max(12, int(target_duration * 1.8))
        if len(voiceover_text.split()) < min_words:
            dialogues = [s.get("dialogue", "").strip() for s in scenes if s.get("dialogue")]
            stitched = " ".join(dialogues).strip()
            if len(stitched.split()) > len(voiceover_text.split()):
                print(f"    ↪️  Voiceover too short ({len(voiceover_text.split())}w) — "
                      f"using stitched scene dialogue ({len(stitched.split())}w)")
                voiceover_text = stitched
            script["voiceover_text"] = voiceover_text

        audio_path = None
        if voiceover_text:
            print(f"    🎙️  OpenAI TTS synthesizing audio ({len(voiceover_text.split())} words)...")
            audio_path = self.generate_audio(voiceover_text, project_id)

        script["audio_path"] = audio_path
        script["audio_filename"] = os.path.basename(audio_path) if audio_path else None
        return script
