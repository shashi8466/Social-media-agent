"""
WebResearchAgent — Crawls and analyzes a website URL to extract brand context,
products/services, target audience, and key messaging for content generation.
"""

import os
import re
import json
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_MAX_CHARS = 8000   # max raw text sent to the AI for analysis


class WebResearchAgent:
    """
    Crawls a URL (homepage + up to 3 sub-pages) and uses GPT-4o to produce a
    structured brand context dict used by content and image agents.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, url: str) -> dict:
        """
        Main entry-point.  Returns a brand context dict with keys:
          brand_name, tagline, products_services, target_audience,
          key_messages, tone_of_voice, industry, competitors,
          summary (plain text for injection into other prompts)
        """
        print(f"  🌐 WebResearchAgent: crawling {url}")
        raw_text = self._crawl(url)

        if not raw_text.strip():
            print("  ⚠️  No text extracted from URL — using empty context")
            return self._empty_context(url)

        print(f"  🧠 Analyzing {len(raw_text)} chars with GPT-4o...")
        context = self._analyze_with_ai(url, raw_text)
        print(f"  ✅ Website analysis complete: {context.get('brand_name', 'Unknown Brand')}")
        return context

    # ── Crawling ──────────────────────────────────────────────────────────────

    def _crawl(self, url: str) -> str:
        """Fetch the homepage and up to 3 linked sub-pages; return combined text."""
        texts: list[str] = []
        visited: set[str] = set()

        # Ensure absolute URL
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        homepage_text = self._fetch_text(url)
        if homepage_text:
            texts.append(homepage_text)
        visited.add(url)

        # Try to find important sub-pages (about, products, services)
        sub_urls = self._find_subpages(url, homepage_text or "")
        for sub_url in sub_urls[:3]:
            if sub_url not in visited:
                sub_text = self._fetch_text(sub_url)
                if sub_text:
                    texts.append(sub_text)
                visited.add(sub_url)

        combined = "\n\n---\n\n".join(texts)
        return combined[:_MAX_CHARS]

    def _fetch_text(self, url: str) -> Optional[str]:
        """Fetch a URL and extract visible text via BeautifulSoup."""
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            print(f"    ⚠️  Fetch failed for {url}: {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noisy tags
        for tag in soup(["script", "style", "noscript", "nav", "footer",
                          "header", "aside", "form", "iframe", "svg"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:3000] if text else None

    def _find_subpages(self, base_url: str, html_or_text: str) -> list[str]:
        """Extract relevant sub-page URLs (about, products, services, etc.)."""
        priority_keywords = ["about", "product", "service", "solution",
                              "feature", "pricing", "work", "blog"]
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        found: list[str] = []
        # Re-fetch to parse links properly
        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("#") or href.startswith("mailto:"):
                    continue
                full = urljoin(base, href)
                # Same domain only
                if urlparse(full).netloc != parsed.netloc:
                    continue
                path = urlparse(full).path.lower()
                if any(kw in path for kw in priority_keywords):
                    if full not in found:
                        found.append(full)
        except Exception:
            pass

        return found[:3]

    # ── AI Analysis ───────────────────────────────────────────────────────────

    def _analyze_with_ai(self, url: str, raw_text: str) -> dict:
        """Use GPT-4o to extract structured brand context from raw page text."""
        system = (
            "You are a brand analyst. Given raw website text, extract structured "
            "brand information and return ONLY valid JSON — no markdown, no explanation."
        )
        user = f"""Analyze this website content from {url} and extract brand context.

WEBSITE TEXT:
{raw_text}

Return a JSON object with these exact keys:
{{
  "brand_name": "company name",
  "tagline": "company tagline or slogan",
  "products_services": ["product/service 1", "product/service 2"],
  "target_audience": "description of ideal customer/audience",
  "key_messages": ["key message 1", "key message 2", "key message 3"],
  "tone_of_voice": "brand tone (professional/friendly/bold/etc)",
  "industry": "industry or niche",
  "unique_value": "unique selling proposition in one sentence",
  "summary": "2-3 sentence plain English summary of the brand for content generation"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            raw = response.choices[0].message.content.strip()

            # Strip any markdown code fence
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            data["source_url"] = url
            return data
        except Exception as e:
            print(f"    ⚠️  AI analysis failed: {e}")
            return self._empty_context(url)

    def _empty_context(self, url: str) -> dict:
        return {
            "brand_name": "",
            "tagline": "",
            "products_services": [],
            "target_audience": "",
            "key_messages": [],
            "tone_of_voice": "professional",
            "industry": "",
            "unique_value": "",
            "summary": "",
            "source_url": url,
        }
