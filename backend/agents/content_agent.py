import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

VALID_PLATFORMS = [
    "linkedin", "instagram", "facebook", "twitter",
    "youtube", "tiktok", "pinterest", "threads",
]


class ContentAgent:
    """
    Content Agent — Uses OpenAI to generate platform-specific social media content.
    Supports: LinkedIn, Instagram, Facebook, Twitter/X, YouTube, TikTok, Pinterest, Threads
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )

    def _load_prompt(self, platform: str) -> str:
        prompt_file = os.path.join(self.prompts_dir, f"{platform}.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
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
        return {"content": text, "hook": "", "cta": ""}

    def _build_context_block(
        self,
        research_context: str = "",
        article: str = "",
        product_info: str = "",
        custom_content: str = "",
        website_context: dict = None,
    ) -> str:
        """Build an enriched context block injected into every prompt."""
        parts = []

        if website_context and website_context.get("summary"):
            brand = website_context.get("brand_name", "")
            summary = website_context["summary"]
            tone = website_context.get("tone_of_voice", "")
            products = website_context.get("products_services", [])
            audience = website_context.get("target_audience", "")
            messages = website_context.get("key_messages", [])
            unique_value = website_context.get("unique_value", "")

            ws = f"BRAND CONTEXT (from website):\n"
            if brand:
                ws += f"  Brand: {brand}\n"
            ws += f"  Summary: {summary}\n"
            if tone:
                ws += f"  Tone: {tone}\n"
            if audience:
                ws += f"  Target Audience: {audience}\n"
            if unique_value:
                ws += f"  Unique Value: {unique_value}\n"
            if products:
                ws += f"  Products/Services: {', '.join(products[:5])}\n"
            if messages:
                ws += f"  Key Messages: {'; '.join(messages[:3])}\n"
            parts.append(ws)

        if article:
            parts.append(f"ARTICLE / BLOG POST TO BASE CONTENT ON:\n{article[:2000]}")

        if product_info:
            parts.append(f"PRODUCT INFORMATION:\n{product_info[:1000]}")

        if custom_content:
            parts.append(f"ADDITIONAL CUSTOM CONTENT / NOTES:\n{custom_content[:1000]}")

        if research_context:
            parts.append(f"RESEARCH CONTEXT (news & trends):\n{research_context[:1500]}")

        if not parts:
            return ""

        return "\n\n".join(parts)

    def generate_platform_content(
        self,
        topic: str,
        platform: str,
        research_context: str = "",
        article: str = "",
        product_info: str = "",
        custom_content: str = "",
        website_context: dict = None,
    ) -> dict:
        """Generate content for a specific platform using OpenAI."""
        context_block = self._build_context_block(
            research_context=research_context,
            article=article,
            product_info=product_info,
            custom_content=custom_content,
            website_context=website_context,
        )

        prompt_template = self._load_prompt(platform)
        system_prompt = prompt_template.replace("{topic}", topic)
        system_prompt = system_prompt.replace("{context_block}", context_block)

        user_message = f"Generate social media content for topic: {topic}"
        if context_block:
            user_message += f"\n\n{context_block}"

        # Retry up to 3 times with backoff so a transient API hiccup doesn't
        # fail the whole platform's content.
        last_err = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=2000,
                    timeout=60,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                result = self._extract_json(response.choices[0].message.content)
                result["platform"] = platform
                result["topic"] = topic
                return result
            except Exception as e:
                last_err = e
                print(f"    ⚠️  {platform} content attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))

        # All retries failed — return a safe placeholder so the pipeline continues
        print(f"    ❌ {platform} content generation failed after retries: {last_err}")
        return {
            "platform": platform,
            "topic": topic,
            "content": f"Content generation for {platform} failed. Please regenerate.",
            "hook": "",
            "cta": "",
            "error": str(last_err),
        }

    def generate_all_platforms(
        self,
        topic: str,
        platforms: list,
        research_context: str = "",
        article: str = "",
        product_info: str = "",
        custom_content: str = "",
        website_context: dict = None,
    ) -> dict:
        """
        Generate content for all specified platforms IN PARALLEL.

        Each platform is an independent GPT-4o call, so running them concurrently
        cuts wall-clock time from N×call to roughly one call. Return shape and
        ordering are preserved for backwards compatibility.
        """
        results: dict = {}

        def _gen(platform: str):
            print(f"    📝 Generating {platform.upper()} content...")
            return platform, self.generate_platform_content(
                topic=topic,
                platform=platform,
                research_context=research_context,
                article=article,
                product_info=product_info,
                custom_content=custom_content,
                website_context=website_context,
            )

        max_workers = min(len(platforms), 8) if platforms else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_gen, p): p for p in platforms}
            for fut in as_completed(futures):
                try:
                    platform, data = fut.result()
                    results[platform] = data
                except Exception as e:
                    p = futures[fut]
                    print(f"    ❌ {p} content task error: {e}")
                    results[p] = {"platform": p, "topic": topic, "content": "", "error": str(e)}

        # Preserve original platform ordering in the returned dict
        return {p: results[p] for p in platforms if p in results}
