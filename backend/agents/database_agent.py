import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "posts.db")


class DatabaseAgent:
    def __init__(self):
        self.db_path = DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    content TEXT NOT NULL,
                    hashtags TEXT DEFAULT '[]',
                    hashtag_strategy TEXT,
                    image_prompt TEXT,
                    image_url TEXT,
                    research_context TEXT,
                    hook TEXT,
                    cta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'draft'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    reel_script TEXT DEFAULT '{}',
                    voiceover_script TEXT DEFAULT '{}',
                    social_posts TEXT DEFAULT '{}',
                    hashtags TEXT DEFAULT '{}',
                    scene_images TEXT DEFAULT '{}',
                    research_context TEXT,
                    audio_path TEXT,
                    video_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'complete'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            # ── Content Packages — complete generation results (additive) ──────
            # Stores the full result of a generation run (social or video) so the
            # Post Library can act as a complete content repository. This is purely
            # additive and does not alter the existing posts / video_projects tables.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_type TEXT NOT NULL DEFAULT 'social',
                    topic TEXT NOT NULL,
                    platforms TEXT DEFAULT '[]',
                    data TEXT NOT NULL DEFAULT '{}',
                    thumbnail_url TEXT,
                    image_count INTEGER DEFAULT 0,
                    has_video INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'complete'
                )
            """)
            conn.commit()

    # ── Posts ─────────────────────────────────────────────────────────────────

    def save_post(
        self,
        topic: str,
        platform: str,
        content: str,
        hashtags: List[str] = None,
        hashtag_strategy: str = None,
        image_prompt: str = None,
        image_url: str = None,
        research_context: str = None,
        hook: str = None,
        cta: str = None,
    ) -> int:
        """Save a generated post to the database and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO posts
                   (topic, platform, content, hashtags, hashtag_strategy, image_prompt, image_url, research_context, hook, cta)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    topic,
                    platform,
                    content,
                    json.dumps(hashtags or []),
                    hashtag_strategy,
                    image_prompt,
                    image_url,
                    research_context,
                    hook,
                    cta,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_posts(self) -> List[Dict]:
        """Retrieve all posts ordered by newest first"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM posts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["hashtags"] = json.loads(d.get("hashtags") or "[]")
                result.append(d)
            return result

    def get_post(self, post_id: int) -> Optional[Dict]:
        """Retrieve a single post by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["hashtags"] = json.loads(d.get("hashtags") or "[]")
                return d
            return None

    def delete_post(self, post_id: int) -> bool:
        """Delete a post by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── Video Projects ────────────────────────────────────────────────────────

    def save_video_project(
        self,
        topic: str,
        reel_script: dict,
        voiceover_script: dict,
        social_posts: dict,
        hashtags: dict,
        scene_images: dict,
        research_context: str = None,
        audio_path: str = None,
        video_path: str = None,
    ) -> int:
        """Save a complete video project and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO video_projects
                   (topic, reel_script, voiceover_script, social_posts, hashtags, scene_images,
                    research_context, audio_path, video_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    topic,
                    json.dumps(reel_script),
                    json.dumps(voiceover_script),
                    json.dumps(social_posts),
                    json.dumps(hashtags),
                    json.dumps(scene_images),
                    research_context,
                    audio_path,
                    video_path,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_video_projects(self, limit: int = 50) -> List[Dict]:
        """Retrieve all video projects ordered by newest first"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM video_projects ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for field in ["reel_script", "voiceover_script", "social_posts", "hashtags", "scene_images"]:
                    try:
                        d[field] = json.loads(d.get(field) or "{}")
                    except Exception:
                        d[field] = {}
                result.append(d)
            return result

    def get_video_project(self, project_id: int) -> Optional[Dict]:
        """Retrieve a single video project by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM video_projects WHERE id = ?", (project_id,)
            )
            row = cursor.fetchone()
            if row:
                d = dict(row)
                for field in ["reel_script", "voiceover_script", "social_posts", "hashtags", "scene_images"]:
                    try:
                        d[field] = json.loads(d.get(field) or "{}")
                    except Exception:
                        d[field] = {}
                return d
            return None

    # ── Content Packages (complete repository) ──────────────────────────────────

    def save_content_package(
        self,
        package_type: str,
        topic: str,
        platforms: List[str],
        data: dict,
        thumbnail_url: str = None,
        image_count: int = 0,
        has_video: bool = False,
    ) -> int:
        """Save a complete generation result (social or video) and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO content_packages
                   (package_type, topic, platforms, data, thumbnail_url, image_count, has_video)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    package_type,
                    topic,
                    json.dumps(platforms or []),
                    json.dumps(data, default=str),
                    thumbnail_url,
                    int(image_count or 0),
                    1 if has_video else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def _hydrate_package(self, row) -> Dict:
        d = dict(row)
        try:
            d["platforms"] = json.loads(d.get("platforms") or "[]")
        except Exception:
            d["platforms"] = []
        try:
            d["data"] = json.loads(d.get("data") or "{}")
        except Exception:
            d["data"] = {}
        d["has_video"] = bool(d.get("has_video"))
        return d

    def get_content_packages(self, limit: int = 100) -> List[Dict]:
        """Retrieve all content packages, newest first."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM content_packages ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            return [self._hydrate_package(r) for r in cursor.fetchall()]

    def get_content_package(self, package_id: int) -> Optional[Dict]:
        """Retrieve a single content package by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM content_packages WHERE id = ?", (package_id,)
            )
            row = cursor.fetchone()
            return self._hydrate_package(row) if row else None

    def delete_content_package(self, package_id: int) -> bool:
        """Delete a content package by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM content_packages WHERE id = ?", (package_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings(self) -> Dict[str, str]:
        """Get all application settings"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT setting_key, setting_value FROM settings")
            rows = cursor.fetchall()
            # Default settings if empty
            settings = {
                "app_name": "GigaTech Social Media Agent",
                "company_name": "GigaTech Services",
                "footer_text": "",
                "contact_info": "contact@gigatech.com",
                "theme_color_primary": "#FF385C",
                "theme_color_secondary": "#FFB800",
                "logo_url": "",
                "favicon_url": ""
            }
            for row in rows:
                settings[row[0]] = row[1]
            return settings

    def update_settings(self, new_settings: Dict[str, str]) -> None:
        """Update multiple application settings"""
        with sqlite3.connect(self.db_path) as conn:
            for k, v in new_settings.items():
                conn.execute(
                    "INSERT INTO settings (setting_key, setting_value) VALUES (?, ?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                    (k, str(v) if v is not None else "")
                )
            conn.commit()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Get content generation statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            by_platform = conn.execute(
                "SELECT platform, COUNT(*) as count FROM posts GROUP BY platform"
            ).fetchall()
            recent = conn.execute(
                "SELECT topic, platform, created_at FROM posts ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            video_total = conn.execute("SELECT COUNT(*) FROM video_projects").fetchone()[0]
            return {
                "total": total,
                "by_platform": {row[0]: row[1] for row in by_platform},
                "video_projects": video_total,
                "recent_topics": [
                    {"topic": r[0], "platform": r[1], "created_at": r[2]}
                    for r in recent
                ],
            }
