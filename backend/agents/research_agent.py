import os
import requests
from bs4 import BeautifulSoup
import feedparser
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

# GigaTech company context (used when website is unavailable)
COMPANY_CONTEXT = """
GigaTech Services is a premier technology solutions company specializing in:
- AI Development & Automation: Building intelligent systems, chatbots, ML pipelines, and RPA solutions
- Web Development: Modern full-stack applications using React, Next.js, Node.js, and cloud-native tech
- Mobile App Development: Cross-platform iOS and Android apps with Flutter and React Native
- Cloud Solutions: AWS, Azure, and GCP infrastructure, DevOps, and cloud migration services

Our mission: Empowering businesses through cutting-edge technology to automate workflows,
scale operations, and drive digital transformation.
"""

# Tech news RSS feeds
NEWS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "https://venturebeat.com/feed/",
]


class ResearchAgent:
    """
    Research Agent — Gathers contextual intelligence before content generation.
    Pipeline: News Fetch → Website Scrape → OpenAI Synthesis → Research Summary
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_news_headlines(self, topic: str, limit: int = 6) -> List[Dict]:
        """Fetch latest tech/AI news from RSS feeds"""
        headlines = []
        topic_keywords = topic.lower().split() + ["ai", "tech", "automation", "digital"]

        for feed_url in NEWS_FEEDS[:2]:  # Limit to 2 feeds for speed
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")[:300]
                    link = entry.get("link", "")
                    # Filter by topic relevance
                    if any(kw in title.lower() for kw in topic_keywords):
                        headlines.append(
                            {
                                "title": title,
                                "summary": summary[:200],
                                "source": feed.feed.get("title", "Tech News"),
                                "link": link,
                            }
                        )
            except Exception as e:
                print(f"    ⚠️  Feed fetch failed ({feed_url[:40]}...): {e}")

        return headlines[:limit]

    def scrape_website(self, url: str) -> str:
        """Scrape and clean text from a website"""
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            soup = BeautifulSoup(resp.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            # Normalize whitespace
            text = " ".join(text.split())
            return text[:2500]
        except Exception as e:
            print(f"    ⚠️  Website scrape failed ({url}): {e}")
            return ""

    def synthesize_research(
        self, topic: str, headlines: List[Dict], company_context: str
    ) -> str:
        """Use OpenAI to synthesize research into actionable content insights"""
        research_block = f"Topic: {topic}\n\n"
        research_block += f"Company Context:\n{company_context}\n\n"

        if headlines:
            research_block += "Latest Industry News:\n"
            for h in headlines:
                research_block += f"• {h['title']} [{h['source']}]\n"
                if h.get("summary"):
                    research_block += f"  {h['summary'][:150]}\n"
            research_block += "\n"

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a research analyst for a social media team at GigaTech Services (a tech company).

Synthesize the following research into 4-6 actionable bullet points that will help create 
looking social media content about "{topic}". Focus on:
- Current trends and opportunities
- Key statistics or facts to mention
- Unique angles for GigaTech to take
- What the audience cares about right now

Research Data:
{research_block}

Output: 4-6 concise bullet points only. No headers or extra text.""",
                }
            ],
        )

        return response.choices[0].message.content


    def research(self, topic: str) -> dict:
        """Main research pipeline"""
        print(f"    🔎 Fetching latest news on '{topic}'...")
        headlines = self.fetch_news_headlines(topic)
        found = len(headlines)
        print(f"    📰 Found {found} relevant headline(s)")

        print(f"    🧠 OpenAI synthesizing research context...")
        summary = self.synthesize_research(topic, headlines, COMPANY_CONTEXT)

        return {
            "topic": topic,
            "headlines_found": found,
            "headlines": headlines,
            "summary": summary,
            "company_context": COMPANY_CONTEXT.strip(),
        }
