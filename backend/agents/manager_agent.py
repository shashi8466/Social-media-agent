import os
import json
import time
from datetime import datetime
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from .research_agent import ResearchAgent
from .web_research_agent import WebResearchAgent
from .content_agent import ContentAgent
from .hashtag_agent import HashtagAgent
from .image_agent import ImageAgent
from .database_agent import DatabaseAgent
from .script_agent import ScriptAgent
from .voice_agent import VoiceAgent
from .video_editor_agent import VideoEditorAgent

VALID_PLATFORMS = [
    "linkedin", "instagram", "facebook", "twitter",
    "youtube", "tiktok", "pinterest", "threads",
]

PLATFORM_ICONS = {
    "linkedin":  "💼",
    "instagram": "📸",
    "facebook":  "👥",
    "twitter":   "🐦",
    "youtube":   "▶️",
    "tiktok":    "🎵",
    "pinterest": "📌",
    "threads":   "🧵",
}

SOCIAL_PLATFORMS = ["linkedin", "instagram", "twitter"]

VALID_RATIOS = ["1:1", "4:5", "9:16", "16:9", "3:2"]


class ManagerAgent:
    """
    Manager Agent — The Orchestrator.

    Two pipelines:
    ─────────────
    run()       — Social media posts (URL Research → News Research → Content →
                  Hashtag → Images → DB)
    run_video() — Full video pipeline (Research → Content → Hashtag → Script →
                  Scene Images → Voice → Video Editor → DB → MP4)
    """

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.web_research_agent = WebResearchAgent()
        self.content_agent = ContentAgent()
        self.hashtag_agent = HashtagAgent()
        self.image_agent = ImageAgent()
        self.database_agent = DatabaseAgent()
        self.script_agent = ScriptAgent()
        self.voice_agent = VoiceAgent()
        self.video_editor_agent = VideoEditorAgent()

    # ── Social Post Pipeline ──────────────────────────────────────────────────

    def run(
        self,
        topic: str,
        platforms: List[str] = None,
        generate_images: bool = True,
        run_research: bool = True,
        # New fields
        article: str = "",
        product_info: str = "",
        custom_content: str = "",
        website_url: str = "",
        blog_url: str = "",
        landing_page_url: str = "",
        company_website_url: str = "",
        image_ratios: List[str] = None,
        image_count: int = 5,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """Execute the full social post multi-agent pipeline."""

        def _notify(step: str, status: str, **kwargs):
            if progress_callback:
                try:
                    progress_callback(step, status, **kwargs)
                except Exception:
                    pass

        if not platforms:
            platforms = ["linkedin", "instagram", "twitter"]
        platforms = [p.lower() for p in platforms if p.lower() in VALID_PLATFORMS]
        if not platforms:
            raise ValueError(f"No valid platforms specified. Valid: {VALID_PLATFORMS}")

        # Resolve image ratios
        if not image_ratios:
            image_ratios = ["1:1"]
        image_ratios = [r for r in image_ratios if r in VALID_RATIOS]
        if not image_ratios:
            image_ratios = ["1:1"]

        image_count = max(1, min(image_count, 10))

        print(f"\n{'='*60}")
        print(f"🚀  SOCIAL MEDIA CONTENT AGENT")
        print(f"{'='*60}")
        print(f"📌  Topic     : {topic}")
        platforms_str = " | ".join(f"{PLATFORM_ICONS.get(p, '')} {p}" for p in platforms)
        print(f"📱  Platforms : {platforms_str}")
        print(f"🖼️   Images    : {image_count}x in ratios {image_ratios}" if generate_images else "🖼️   Images    : No")
        print(f"🌐  Website   : {website_url or company_website_url or 'None'}")
        print(f"{'='*60}\n")

        result = {
            "topic": topic,
            "platforms": platforms,
            "generated_at": datetime.now().isoformat(),
            "research": None,
            "website_context": None,
            "content": {},
            "images": [],
            "saved_post_ids": [],
            "pipeline_steps": [],
        }

        # ── Phase 1: Website Research ─────────────────────────────────────
        website_context = None
        primary_url = website_url or company_website_url or landing_page_url or blog_url
        if primary_url:
            print("🌐  Phase 1: Web Research Agent")
            _notify("web_research", "running")
            try:
                website_context = self.web_research_agent.analyze(primary_url)
                result["website_context"] = website_context
                result["pipeline_steps"].append(
                    {"step": "web_research", "status": "complete",
                     "brand": website_context.get("brand_name", "")}
                )
                _notify("web_research", "complete")
                print(f"  ✅ Website analyzed: {website_context.get('brand_name', 'Unknown')}\n")
            except Exception as e:
                print(f"  ⚠️  Website research failed: {e}\n")
                result["pipeline_steps"].append(
                    {"step": "web_research", "status": "failed", "error": str(e)}
                )
                _notify("web_research", "failed", error=str(e))
        else:
            result["pipeline_steps"].append({"step": "web_research", "status": "skipped"})
            _notify("web_research", "complete")

        # ── Phase 2: News Research ────────────────────────────────────────
        research_context = ""
        if run_research:
            print("🔍  Phase 2: Research Agent (News & Trends)")
            _notify("research", "running")
            try:
                research_result = self.research_agent.research(topic)
                result["research"] = research_result
                research_context = research_result.get("summary", "")
                result["pipeline_steps"].append(
                    {"step": "research", "status": "complete",
                     "headlines": research_result.get("headlines_found", 0)}
                )
                _notify("research", "complete")
                print(f"  ✅ Research complete ({research_result.get('headlines_found', 0)} headlines)\n")
            except Exception as e:
                print(f"  ⚠️  Research failed: {e}\n")
                result["pipeline_steps"].append(
                    {"step": "research", "status": "failed", "error": str(e)}
                )
                _notify("research", "failed", error=str(e))
        else:
            result["pipeline_steps"].append({"step": "research", "status": "skipped"})
            _notify("research", "complete")

        # ── Phases 3-5 run with IMAGES IN PARALLEL with CONTENT+HASHTAGS ───
        # Image generation only depends on the topic, so we kick it off in a
        # background thread and let the (dependent) content → hashtag chain run
        # concurrently. This significantly cuts total wall-clock time.
        image_executor = ThreadPoolExecutor(max_workers=1)
        image_future = None
        if generate_images:
            print(f"🎨  Phase 5 (parallel): Image Agent ({image_count} × {len(image_ratios)} ratio(s))")
            _notify("images", "running")

            def _generate_all_images():
                # Single parallel pool across ALL ratios; prompt crafted once.
                return self.image_agent.generate_image_set(
                    topic=topic,
                    platform=platforms[0] if platforms else "default",
                    ratios=image_ratios,
                    count=image_count,
                    fast_mode=False,
                    max_workers=8,
                )

            image_future = image_executor.submit(_generate_all_images)

        # ── Phase 3: Content Agent (parallel across platforms) ────────────
        print("✍️   Phase 3: Content Agent")
        _notify("content", "running")
        content = self.content_agent.generate_all_platforms(
            topic=topic,
            platforms=platforms,
            research_context=research_context,
            article=article,
            product_info=product_info,
            custom_content=custom_content,
            website_context=website_context,
        )
        result["pipeline_steps"].append(
            {"step": "content", "status": "complete", "platforms": list(content.keys())}
        )
        _notify("content", "complete")
        print(f"  ✅ Content generated for {len(content)} platform(s)\n")

        # ── Phase 4: Hashtag Agent (parallel across platforms) ────────────
        print("#️⃣   Phase 4: Hashtag Agent")
        _notify("hashtags", "running")
        enriched_content = self.hashtag_agent.enrich_all_content(topic, content)
        result["content"] = enriched_content
        result["pipeline_steps"].append({"step": "hashtags", "status": "complete"})
        _notify("hashtags", "complete")
        print(f"  ✅ Hashtags enriched\n")

        # ── Join image generation ─────────────────────────────────────────
        if generate_images and image_future is not None:
            try:
                all_images = image_future.result(timeout=300)
            except Exception as e:
                print(f"  ⚠️  Image generation failed: {e}\n")
                all_images = []
            result["images"] = all_images
            generated = sum(1 for img in all_images if img.get("image_url"))
            result["pipeline_steps"].append(
                {"step": "images", "status": "complete",
                 "generated": generated, "total": len(all_images)}
            )
            _notify("images", "complete")
            print(f"  ✅ {generated}/{len(all_images)} images generated\n")
        image_executor.shutdown(wait=False)

        # ── Phase 6: Database Agent ───────────────────────────────────────
        print("💾  Phase 6: Database Agent")
        _notify("database", "running")
        for platform in platforms:
            platform_content = enriched_content.get(platform, {})
            post_id = self.database_agent.save_post(
                topic=topic,
                platform=platform,
                content=platform_content.get("content", ""),
                hashtags=platform_content.get("hashtags", []),
                hashtag_strategy=platform_content.get("hashtag_strategy", ""),
                image_prompt="",
                image_url="",
                research_context=research_context,
                hook=platform_content.get("hook", ""),
                cta=platform_content.get("cta", ""),
            )
            result["saved_post_ids"].append(post_id)
            print(f"    💾 {platform.upper()} saved → Post ID: {post_id}")

        # Save the complete package so the Post Library is a full repository
        try:
            first_img = next((img.get("image_url") for img in result["images"] if img.get("image_url")), None)
            pkg_id = self.database_agent.save_content_package(
                package_type="social",
                topic=topic,
                platforms=platforms,
                data=result,
                thumbnail_url=first_img,
                image_count=sum(1 for img in result["images"] if img.get("image_url")),
                has_video=False,
            )
            result["package_id"] = pkg_id
            print(f"    📦 Content package saved → ID: {pkg_id}")
        except Exception as e:
            print(f"    ⚠️  Package save failed: {e}")

        result["pipeline_steps"].append(
            {"step": "database", "status": "complete", "saved_ids": result["saved_post_ids"]}
        )
        _notify("database", "complete")

        print(f"\n{'='*60}")
        print(f"✨  PIPELINE COMPLETE! Posts: {len(platforms)} | Images: {len(result['images'])}")
        print(f"{'='*60}\n")
        return result

    # ── Video Pipeline ────────────────────────────────────────────────────────

    @staticmethod
    def _fit_duration(reel_script: dict, target_duration: int) -> dict:
        scenes = reel_script.get("scenes", []) or []
        if not scenes or not target_duration:
            reel_script["total_duration_sec"] = target_duration
            return reel_script

        current_total = sum(float(s.get("duration_sec", 7)) for s in scenes)
        if current_total <= 0:
            per = target_duration / len(scenes)
            for s in scenes:
                s["duration_sec"] = round(per, 1)
        else:
            factor = target_duration / current_total
            for s in scenes:
                scaled = round(float(s.get("duration_sec", 7)) * factor, 1)
                s["duration_sec"] = max(1.5, scaled)

        reel_script["total_duration_sec"] = round(
            sum(float(s.get("duration_sec", 0)) for s in scenes), 1
        )
        reel_script["target_duration_sec"] = target_duration
        return reel_script

    def run_video(
        self,
        topic: str,
        run_research: bool = True,
        progress_callback: Optional[Callable] = None,
        target_duration: int = 45,
        aspect_ratio: str = "9:16",
        # New extended fields
        article: str = "",
        product_info: str = "",
        custom_content: str = "",
        website_url: str = "",
        blog_url: str = "",
        landing_page_url: str = "",
        company_website_url: str = "",
    ) -> dict:
        """Execute the full short-video content pipeline."""
        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        def _notify(step: str, status: str, **kwargs):
            if progress_callback:
                try:
                    progress_callback(step, status, **kwargs)
                except Exception:
                    pass

        print(f"\n{'='*60}")
        print(f"🎬  SHORT VIDEO CONTENT AGENT")
        print(f"{'='*60}")
        print(f"📌  Topic      : {topic}")
        print(f"🆔  Project ID : {project_id}")
        print(f"⏱   Duration   : {target_duration}s")
        print(f"📐  Aspect     : {aspect_ratio}")
        print(f"{'='*60}\n")

        result = {
            "project_id": project_id,
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "research": None,
            "website_context": None,
            "social_posts": {},
            "hashtags": {},
            "reel_script": {},
            "scene_images": {},
            "voiceover_script": {},
            "audio_path": None,
            "audio_filename": None,
            "video_path": None,
            "video_filename": None,
            "thumbnail_url": None,
            "pipeline_steps": [],
        }

        # ── Phase 1: Website Research ─────────────────────────────────────
        website_context = None
        primary_url = website_url or company_website_url or landing_page_url or blog_url
        if primary_url:
            print("🌐  Phase 1: Web Research Agent")
            _notify("web_research", "running")
            try:
                website_context = self.web_research_agent.analyze(primary_url)
                result["website_context"] = website_context
                result["pipeline_steps"].append(
                    {"step": "web_research", "status": "complete",
                     "brand": website_context.get("brand_name", "")}
                )
                _notify("web_research", "complete")
                print(f"  ✅ Website analyzed: {website_context.get('brand_name', '')}\n")
            except Exception as e:
                print(f"  ⚠️  Website research failed: {e}\n")
                result["pipeline_steps"].append(
                    {"step": "web_research", "status": "failed", "error": str(e)}
                )
                _notify("web_research", "failed", error=str(e))
        else:
            result["pipeline_steps"].append({"step": "web_research", "status": "skipped"})
            _notify("web_research", "complete")

        # ── Phase 2: News Research ────────────────────────────────────────
        research_context = ""
        if run_research:
            print("🔍  Phase 2: Research Agent")
            _notify("research", "running")
            try:
                research_result = self.research_agent.research(topic)
                result["research"] = research_result
                research_context = research_result.get("summary", "")
                result["pipeline_steps"].append(
                    {"step": "research", "status": "complete",
                     "headlines": research_result.get("headlines_found", 0)}
                )
                _notify("research", "complete")
                print(f"  ✅ Research complete\n")
            except Exception as e:
                print(f"  ⚠️  Research failed: {e}\n")
                result["pipeline_steps"].append(
                    {"step": "research", "status": "failed", "error": str(e)}
                )
                _notify("research", "failed", error=str(e))
        else:
            result["pipeline_steps"].append({"step": "research", "status": "skipped"})
            _notify("research", "complete")

        # ── Phase 3: Content Agent ────────────────────────────────────────
        print("✍️   Phase 3: Content Agent")
        _notify("content", "running")
        try:
            content = self.content_agent.generate_all_platforms(
                topic=topic,
                platforms=SOCIAL_PLATFORMS,
                research_context=research_context,
                article=article,
                product_info=product_info,
                custom_content=custom_content,
                website_context=website_context,
            )
            result["pipeline_steps"].append(
                {"step": "content", "status": "complete", "platforms": list(content.keys())}
            )
            _notify("content", "complete")
            print(f"  ✅ Social posts generated\n")
        except Exception as e:
            content = {}
            print(f"  ⚠️  Content generation failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "content", "status": "failed", "error": str(e)}
            )
            _notify("content", "failed", error=str(e))

        # ── Phase 4: Hashtag Agent ────────────────────────────────────────
        print("#️⃣   Phase 4: Hashtag Agent")
        _notify("hashtags", "running")
        try:
            enriched_content = self.hashtag_agent.enrich_all_content(topic, content)
            result["social_posts"] = enriched_content
            result["hashtags"] = {
                p: data.get("hashtags", []) for p, data in enriched_content.items()
            }
            result["pipeline_steps"].append({"step": "hashtags", "status": "complete"})
            _notify("hashtags", "complete")
            print(f"  ✅ Hashtags enriched\n")
        except Exception as e:
            result["social_posts"] = content
            print(f"  ⚠️  Hashtag enrichment failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "hashtags", "status": "failed", "error": str(e)}
            )
            _notify("hashtags", "failed", error=str(e))

        # ── Phase 5: Script Agent ─────────────────────────────────────────
        print("📝  Phase 5: Script Agent")
        _notify("script", "running")
        try:
            # USER CONTENT (highest priority): article + product info + custom notes
            user_content = "\n\n".join(
                p for p in [
                    (f"Article:\n{article}" if article else ""),
                    (f"Product Information:\n{product_info}" if product_info else ""),
                    (f"Additional Notes:\n{custom_content}" if custom_content else ""),
                ] if p
            )
            reel_script = self.script_agent.generate_script(
                topic=topic,
                research_context=research_context,
                user_content=user_content,
                website_context=website_context,
                target_duration=target_duration,
            )
            reel_script = self._fit_duration(reel_script, target_duration)
            result["reel_script"] = reel_script
            result["pipeline_steps"].append(
                {"step": "script", "status": "complete",
                 "scenes": reel_script.get("scene_count", 0)}
            )
            _notify("script", "complete")
            print(f"  ✅ Script generated ({reel_script.get('scene_count', 0)} scenes)\n")
        except Exception as e:
            reel_script = {"scenes": [], "hook_line": "", "call_to_action": "",
                           "total_duration_sec": target_duration}
            print(f"  ⚠️  Script generation failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "script", "status": "failed", "error": str(e)}
            )
            _notify("script", "failed", error=str(e))

        # ── Phase 6: Scene Images (parallelized) ──────────────────────────
        scenes = reel_script.get("scenes", [])
        scene_images = {}
        print(f"🎨  Phase 6: Image Agent ({len(scenes)} scenes, ratio {aspect_ratio})")
        _notify("scene_images", "running")

        def _gen_scene(scene):
            scene_num = scene.get("scene_number", 1)
            visual = scene.get("visual_direction", topic)
            dalle_topic = f"{topic}: {visual}"
            t0 = time.time()
            try:
                img_result = self.image_agent.generate_image(
                    topic=dalle_topic,
                    platform="reels",
                    fast_mode=True,
                    ratio=aspect_ratio,
                    image_index=scene_num,
                )
                elapsed = time.time() - t0
                status = "✅" if img_result.get("image_url") else "⚠️ "
                print(f"    {status} Scene {scene_num} done in {elapsed:.1f}s")
                return scene_num, img_result
            except Exception as ex:
                print(f"    ❌ Scene {scene_num} error: {ex}")
                return scene_num, {"image_url": None, "local_path": None, "error": str(ex)}

        SCENE_TIMEOUT = 180
        try:
            max_workers = min(len(scenes), 6) if scenes else 1
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {executor.submit(_gen_scene, s): s.get("scene_number", i + 1)
                              for i, s in enumerate(scenes)}
                try:
                    for fut in as_completed(future_map, timeout=SCENE_TIMEOUT):
                        sn, img = fut.result()
                        scene_images[sn] = img
                except TimeoutError:
                    print(f"    ⏱  Timeout — continuing with {len(scene_images)}/{len(scenes)} images")
                    for fut, sn in future_map.items():
                        if sn not in scene_images:
                            scene_images[sn] = {"image_url": None, "local_path": None, "error": "timeout"}

            result["scene_images"] = scene_images

            # Use the first scene image as thumbnail
            first_img = scene_images.get(1, {})
            if first_img.get("image_url"):
                result["thumbnail_url"] = first_img["image_url"]

            generated = sum(1 for v in scene_images.values() if v.get("image_url"))
            result["pipeline_steps"].append(
                {"step": "scene_images", "status": "complete", "generated": generated}
            )
            _notify("scene_images", "complete")
            print(f"  ✅ {generated}/{len(scenes)} scene images generated\n")
        except Exception as e:
            print(f"  ⚠️  Scene image generation failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "scene_images", "status": "failed", "error": str(e)}
            )
            _notify("scene_images", "failed", error=str(e))

        # ── Phase 7: Voice Agent ──────────────────────────────────────────
        print("🎙️   Phase 7: Voice Agent")
        _notify("voice", "running")
        try:
            voice_result = self.voice_agent.run(topic, scenes, project_id, target_duration=target_duration)
            result["voiceover_script"] = voice_result
            result["audio_path"] = voice_result.get("audio_path")
            result["audio_filename"] = voice_result.get("audio_filename")
            result["pipeline_steps"].append(
                {"step": "voice", "status": "complete",
                 "has_audio": bool(voice_result.get("audio_path"))}
            )
            _notify("voice", "complete")
            print(f"  ✅ Voiceover ready\n")
        except Exception as e:
            print(f"  ⚠️  Voice generation failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "voice", "status": "failed", "error": str(e)}
            )
            _notify("voice", "failed", error=str(e))

        # ── Sync scene timing to the ACTUAL voiceover length ──────────────
        # The final video must match the voiceover (no silent tail). Measure the
        # real audio duration and re-fit the scene durations to it, so:
        #   scene_total == voiceover == final MP4 length.
        voiceover_dur = self.video_editor_agent.measure_duration(result.get("audio_path"))
        final_duration = reel_script.get("total_duration_sec", target_duration)
        if voiceover_dur and voiceover_dur > 1.0:
            # Fit scenes to slightly MORE than the voiceover so the video track
            # always fully covers it, then cut the final MP4 to exactly the
            # voiceover length (-t in the editor) → final == voiceover, no silence.
            reel_script = self._fit_duration(reel_script, voiceover_dur + 0.6)
            result["reel_script"] = reel_script
            scenes = reel_script.get("scenes", scenes)
            final_duration = round(voiceover_dur, 2)
            print(f"  🔁 Synced scenes to voiceover: {voiceover_dur:.1f}s "
                  f"(selected {target_duration}s) → final MP4 {final_duration:.1f}s")
        else:
            print(f"  ⚠️  No measurable voiceover — using selected {target_duration}s")

        scene_total = round(sum(float(s.get("duration_sec", 0)) for s in scenes), 2)

        # ── Phase 8: Video Editor ─────────────────────────────────────────
        print("🎬  Phase 8: Video Editor Agent")
        _notify("video_editor", "running")
        try:
            video_path = self.video_editor_agent.assemble_video(
                scenes=scenes,
                scene_images=scene_images,
                audio_path=result.get("audio_path"),
                hook_line=reel_script.get("hook_line", ""),
                cta=reel_script.get("call_to_action", ""),
                project_id=project_id,
                total_duration=final_duration,
                aspect_ratio=aspect_ratio,
            )
            if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 50_000:
                # ── Duration validation before "export" ──────────────────
                final_video_dur = self.video_editor_agent.measure_duration(video_path)
                synced = True
                if voiceover_dur and final_video_dur:
                    synced = abs(final_video_dur - voiceover_dur) <= 1.5
                result["durations"] = {
                    "selected_sec":  target_duration,
                    "voiceover_sec": round(voiceover_dur, 2) if voiceover_dur else None,
                    "scene_total_sec": scene_total,
                    "final_video_sec": round(final_video_dur, 2) if final_video_dur else None,
                }
                result["duration_synced"] = synced
                if not synced:
                    print(f"  ⚠️  Duration mismatch — voiceover {voiceover_dur}s vs "
                          f"video {final_video_dur}s")

                result["video_path"] = video_path
                result["video_filename"] = os.path.basename(video_path)
                result["pipeline_steps"].append({
                    "step": "video_editor", "status": "complete",
                    "video_filename": result["video_filename"],
                    "file_size_bytes": os.path.getsize(video_path),
                    "durations": result["durations"],
                    "duration_synced": synced,
                })
                _notify("video_editor", "complete")
                print(f"  ✅ MP4 assembled: {result['video_filename']} "
                      f"(video {final_video_dur}s · voiceover {voiceover_dur}s · synced={synced})\n")
            else:
                reason = "file not created or too small"
                result["pipeline_steps"].append(
                    {"step": "video_editor", "status": "failed", "error": reason}
                )
                _notify("video_editor", "failed", error=reason)
        except Exception as e:
            result["pipeline_steps"].append(
                {"step": "video_editor", "status": "failed", "error": str(e)}
            )
            result["video_editor_error"] = str(e)
            _notify("video_editor", "failed", error=str(e))
            print(f"  ❌ Video editor error: {e}\n")

        # ── Phase 9: Database Agent ───────────────────────────────────────
        print("💾  Phase 9: Database Agent")
        _notify("database", "running")
        try:
            project_db_id = self.database_agent.save_video_project(
                topic=topic,
                reel_script=result["reel_script"],
                voiceover_script=result["voiceover_script"],
                social_posts=result["social_posts"],
                hashtags=result["hashtags"],
                scene_images={str(k): v for k, v in scene_images.items()},
                research_context=research_context,
                audio_path=result.get("audio_path"),
                video_path=result.get("video_path"),
            )
            result["db_project_id"] = project_db_id
            result["pipeline_steps"].append(
                {"step": "database", "status": "complete", "project_id": project_db_id}
            )
            _notify("database", "complete")
            print(f"  ✅ Project saved → DB ID: {project_db_id}\n")
        except Exception as e:
            print(f"  ⚠️  Database save failed: {e}\n")
            result["pipeline_steps"].append(
                {"step": "database", "status": "failed", "error": str(e)}
            )
            _notify("database", "failed", error=str(e))

        # Save the complete video package to the Post Library repository
        try:
            scene_img_urls = [v.get("image_url") for v in scene_images.values() if v.get("image_url")]
            pkg_id = self.database_agent.save_content_package(
                package_type="video",
                topic=topic,
                platforms=list(result.get("social_posts", {}).keys()),
                data=result,
                thumbnail_url=result.get("thumbnail_url") or (scene_img_urls[0] if scene_img_urls else None),
                image_count=len(scene_img_urls),
                has_video=bool(result.get("video_filename")),
            )
            result["package_id"] = pkg_id
            print(f"    📦 Video package saved → ID: {pkg_id}")
        except Exception as e:
            print(f"    ⚠️  Video package save failed: {e}")

        print(f"{'='*60}")
        print(f"✨  VIDEO PIPELINE COMPLETE! Topic: {topic}")
        print(f"    Scenes: {len(scenes)} | Audio: {'✅' if result.get('audio_filename') else '❌'} | Video: {'✅' if result.get('video_filename') else '❌'}")
        print(f"{'='*60}\n")
        return result
