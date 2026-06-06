"""
Script Agent — Generates structured short-video Reel scripts using OpenAI.
Output: JSON with 6 scenes, each containing visual direction, dialogue, duration, and on-screen text.
"""

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ScriptAgent:
    """
    Script Agent — Uses OpenAI to generate a structured 6-scene Reel script.

    Output schema:
        hook_line, call_to_action, total_duration_sec, scene_count,
        scenes: [{ scene_number, duration_sec, visual_direction,
                   dialogue, on_screen_text, visual_style }]
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )

    def _load_prompt(self) -> str:
        with open(os.path.join(self.prompts_dir, "script.txt"), "r", encoding="utf-8") as f:
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

        # Fallback structure
        return {
            "hook_line": f"Transform your business with {text[:30]}",
            "call_to_action": "Follow for more tech insights!",
            "total_duration_sec": 45,
            "scene_count": 6,
            "scenes": []
        }

    def _build_context_block(
        self,
        topic: str,
        user_content: str = "",
        website_context: dict = None,
        research_context: str = "",
    ) -> str:
        """
        Build a priority-ordered context block:
          1. USER CONTENT (highest)  2. WEBSITE CONTENT  3. RESEARCH CONTEXT
        """
        # USER CONTENT = the topic plus any article / product / custom text the user gave.
        user_parts = []
        if topic:
            user_parts.append(f"Topic / title: {topic}")
        if user_content and user_content.strip():
            user_parts.append(user_content.strip()[:3000])
        user_block = "\n".join(user_parts) if user_parts else topic

        parts = [
            "USER CONTENT (HIGHEST PRIORITY — build the script primarily from this):\n"
            f"{user_block}"
        ]

        if website_context and website_context.get("summary"):
            wc = website_context
            ws = "WEBSITE CONTENT (use only to add accurate brand/product detail):\n"
            if wc.get("brand_name"):
                ws += f"  Brand: {wc['brand_name']}\n"
            ws += f"  Summary: {wc['summary']}\n"
            if wc.get("products_services"):
                ws += f"  Products/Services: {', '.join(wc['products_services'][:5])}\n"
            if wc.get("key_messages"):
                ws += f"  Key Messages: {'; '.join(wc['key_messages'][:3])}"
            parts.append(ws)

        if research_context and research_context.strip():
            parts.append(
                "RESEARCH CONTEXT (use ONLY to optimize phrasing/hooks/trends, not as the subject):\n"
                f"{research_context.strip()[:800]}"
            )

        return "\n\n".join(parts)

    def generate_script(
        self,
        topic: str,
        research_context: str = "",
        user_content: str = "",
        website_context: dict = None,
        target_duration: int = 45,
    ) -> dict:
        """
        Generate a structured 6-scene Reel script, built STRICTLY from the
        user-provided content first, then website content, then research.
        """
        context_block = self._build_context_block(
            topic=topic,
            user_content=user_content,
            website_context=website_context,
            research_context=research_context,
        )

        prompt = self._load_prompt()
        prompt = prompt.replace("{context_block}", context_block)
        prompt = prompt.replace("{target_duration}", str(target_duration))
        # Backwards-compat in case the template still references {topic}/{research_context}
        prompt = prompt.replace("{topic}", topic)
        prompt = prompt.replace("{research_context}", research_context[:800] if research_context else "")

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )

        result = self._extract_json(response.choices[0].message.content)
        result["topic"] = topic
        return result

