import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class HashtagAgent:
    """
    Hashtag Agent — Uses OpenAI to generate platform-optimized hashtag strategies.
    Enriches existing content with targeted, tiered hashtag sets.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )

    def _load_prompt(self) -> str:
        prompt_file = os.path.join(self.prompts_dir, "hashtags.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
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

        return {"hashtags": [], "strategy_note": ""}

    @staticmethod
    def _normalize_tags(tags) -> list:
        """Normalize to a clean list of '#Tag' strings, de-duplicated."""
        out, seen = [], set()
        for t in tags or []:
            if not isinstance(t, str):
                continue
            t = t.strip().lstrip("#").strip()
            t = re.sub(r"\s+", "", t)
            if not t:
                continue
            tag = "#" + t
            key = tag.lower()
            if key not in seen:
                seen.add(key)
                out.append(tag)
        return out

    @staticmethod
    def _extract_from_text(text: str) -> list:
        """Pull inline #hashtags out of post content as a fallback."""
        return re.findall(r"#(\w+)", text or "")

    def _topic_fallback_tags(self, topic: str) -> list:
        """Last-resort hashtags derived from the topic words."""
        words = re.findall(r"[A-Za-z0-9]+", topic or "")
        tags = ["".join(w.capitalize() for w in words)] if words else []
        tags += [w.capitalize() for w in words if len(w) > 2][:4]
        return tags

    def generate_hashtags(self, topic: str, platform: str, content: str) -> dict:
        """Generate optimized hashtags for a specific platform and content."""
        prompt = self._load_prompt()
        prompt = prompt.replace("{topic}", topic)
        prompt = prompt.replace("{platform}", platform)
        prompt = prompt.replace("{content}", content[:500])

        data = {}
        try:
            response = self.client.chat.completions.create(
                model=self.model, max_tokens=600, timeout=45,
                messages=[{"role": "user", "content": prompt}],
            )
            data = self._extract_json(response.choices[0].message.content)
        except Exception as e:
            print(f"    ⚠️  Hashtag API failed for {platform}: {e}")

        # Accept several possible shapes the model might return
        raw = data.get("hashtags") or data.get("tags") or data.get("hashtag_list") or []
        if isinstance(raw, dict):  # tiered object → flatten
            flat = []
            for v in raw.values():
                if isinstance(v, list):
                    flat.extend(v)
            raw = flat
        tags = self._normalize_tags(raw)

        # Fallback 1: extract inline hashtags already present in the post content
        if not tags:
            tags = self._normalize_tags(self._extract_from_text(content))

        # Fallback 2: derive from the topic so a section is never empty
        if not tags:
            tags = self._normalize_tags(self._topic_fallback_tags(topic))

        return {"hashtags": tags, "strategy_note": data.get("strategy_note", "")}


    def enrich_all_content(self, topic: str, content_by_platform: dict) -> dict:
        """Enrich all platform content with hashtags IN PARALLEL."""
        platforms = list(content_by_platform.keys())
        enriched: dict = {}

        def _enrich(platform: str):
            content_data = content_by_platform[platform]
            print(f"    #️⃣  Enriching {platform.upper()} hashtags...")
            try:
                hashtag_data = self.generate_hashtags(
                    topic, platform, content_data.get("content", "")
                )
            except Exception as e:
                print(f"    ⚠️  {platform} hashtag enrichment failed: {e}")
                hashtag_data = {"hashtags": [], "strategy_note": ""}
            return platform, {
                **content_data,
                "hashtags": hashtag_data.get("hashtags", []),
                "hashtag_strategy": hashtag_data.get("strategy_note", ""),
            }

        max_workers = min(len(platforms), 8) if platforms else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_enrich, p): p for p in platforms}
            for fut in as_completed(futures):
                try:
                    platform, data = fut.result()
                    enriched[platform] = data
                except Exception as e:
                    p = futures[fut]
                    enriched[p] = {**content_by_platform[p], "hashtags": [], "hashtag_strategy": ""}

        return {p: enriched[p] for p in platforms if p in enriched}
