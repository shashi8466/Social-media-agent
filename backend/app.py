"""
Social Media Content Agent — FastAPI Backend
=============================================
Multi-agent AI workflow for automated social media content generation.

Pipelines:
  Social Post Pipeline:
    Research Agent  → Gathers news context
    Content Agent   → Claude-powered post generation
    Hashtag Agent   → Platform-optimized hashtags
    Image Agent     → Claude prompt + DALL-E 3 image generation
    Database Agent  → SQLite persistence

  Video Pipeline:
    Research Agent  → Context synthesis
    Content Agent   → Social posts (LinkedIn/Instagram/Twitter)
    Hashtag Agent   → Hashtag enrichment
    Script Agent    → 6-scene Reel script (Claude)
    Image Agent     → DALL-E 3 scene images
    Voice Agent     → Voiceover script + OpenAI TTS MP3
    Video Editor    → MoviePy assembles final MP4
    Database Agent  → video_projects SQLite table
"""

import sys
import io

if sys.platform.startswith('win'):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
import uuid
import threading
from datetime import datetime
from dotenv import load_dotenv

from agents import ManagerAgent, DatabaseAgent, SegmindAgent, FlyerAgent

# ── In-memory job stores for async pipelines ──────────────────────────────────
_video_jobs: dict = {}   # job_id → {status, current_step, completed_steps, result, error, ...}
_social_jobs: dict = {}  # job_id → same shape, for the social-post pipeline

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Social Media Content Agent API",
    description="Multi-agent AI workflow for social media content + short video generation",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Serve generated video/audio files
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# CORS — Allow dynamic origins (supports preview branches & production domains automatically via regex)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    error_details = {
        "errors": exc.errors(),
        "body": None
    }
    try:
        body = await request.json()
        error_details["body"] = body
    except Exception:
        try:
            body = await request.body()
            error_details["body"] = body.decode("utf-8", errors="ignore")
        except Exception:
            pass
    
    # Write to a debug file
    log_file = os.path.join(OUTPUT_DIR, "validation_error.log")
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(error_details, default=str, indent=2))
    except Exception as log_err:
        print(f"Error writing validation log: {log_err}")
        
    print("Validation Error Details:", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# Shared database agent instance
db_agent = DatabaseAgent()


# ── Request / Response Models ─────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=50000, example="AI Automation")
    platforms: Optional[List[str]] = Field(
        default=["linkedin", "instagram", "twitter"],
        description="Target platforms",
    )
    generate_images: Optional[bool] = Field(default=True, description="Generate images")
    run_research: Optional[bool] = Field(default=True, description="Run news research agent")
    # Extended input fields
    article: Optional[str] = Field(default="", max_length=10000, description="Article or blog post text")
    product_info: Optional[str] = Field(default="", max_length=3000, description="Product/service information")
    custom_content: Optional[str] = Field(default="", max_length=3000, description="Additional custom notes")
    website_url: Optional[str] = Field(default="", max_length=500, description="Primary website URL to analyze")
    blog_url: Optional[str] = Field(default="", max_length=500, description="Blog URL")
    landing_page_url: Optional[str] = Field(default="", max_length=500, description="Landing page URL")
    company_website_url: Optional[str] = Field(default="", max_length=500, description="Company website URL")
    # Image settings
    image_ratios: Optional[List[str]] = Field(
        default=["1:1"],
        description="Image ratios to generate (1:1, 4:5, 9:16, 16:9, 3:2)"
    )
    image_count: Optional[int] = Field(default=5, ge=1, le=10, description="Number of images per ratio")


class VideoGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=50000, example="AI Automation for Startups")
    run_research: Optional[bool] = Field(default=True, description="Run research agent for richer context")
    duration_sec: Optional[int] = Field(
        default=45, ge=15, le=90,
        description="Target reel duration in seconds (15/30/45/60/90)",
    )
    aspect_ratio: Optional[str] = Field(default="9:16", description="Video aspect ratio (9:16, 16:9, 1:1, 4:5)")
    # Extended input fields
    article: Optional[str] = Field(default="", max_length=10000, description="Article or blog post text")
    product_info: Optional[str] = Field(default="", max_length=3000, description="Product/service information")
    custom_content: Optional[str] = Field(default="", max_length=3000, description="Additional custom notes")
    website_url: Optional[str] = Field(default="", max_length=500, description="Website URL to analyze")
    blog_url: Optional[str] = Field(default="", max_length=500, description="Blog URL")
    landing_page_url: Optional[str] = Field(default="", max_length=500, description="Landing page URL")
    company_website_url: Optional[str] = Field(default="", max_length=500, description="Company website URL")





class FlyerRequest(BaseModel):
    content: Optional[str] = Field(default="", max_length=50000, description="Primary content the flyer is generated from")
    topic: Optional[str] = Field(default="", max_length=2000, description="Legacy/short title (optional)")
    style: Optional[str] = Field(default="auto", description="auto|corporate|educational|modern|premium|technology|startup|marketing|event|professional")
    website_url: Optional[str] = Field(default="", max_length=500)
    custom_content: Optional[str] = Field(default="", max_length=3000)
    ratio: Optional[str] = Field(default="a4_portrait", description="a4_portrait|a4_landscape|1:1|4:5|9:16|16:9|facebook|linkedin|custom")
    custom_width: Optional[int] = Field(default=None, ge=320, le=4096)
    custom_height: Optional[int] = Field(default=None, ge=320, le=4096)
    formats: Optional[List[str]] = Field(default=["png", "pdf"], description="png|jpg|pdf")
    brand_name: Optional[str] = Field(default="", max_length=120)
    partner_name: Optional[str] = Field(default="", max_length=120)
    brand_logo_url: Optional[str] = Field(default="", max_length=500)
    partner_logo_url: Optional[str] = Field(default="", max_length=500)
    contact_info: Optional[str] = Field(default="", max_length=300)
    display_url: Optional[str] = Field(default="", max_length=300)
    accent_color: Optional[str] = Field(default="", max_length=9, description="Optional override; blank = theme/brand colors")
    secondary_color: Optional[str] = Field(default="", max_length=9, description="Optional override; blank = theme/brand colors")
    creative: Optional[bool] = Field(default=True, description="AI Creative mode (LLM-authored unique HTML design). Falls back to layout engine.")
    brand_logo_b64: Optional[str] = Field(default="", description="Base64-encoded brand logo (PNG/JPG) uploaded from browser")
    partner_logo_b64: Optional[str] = Field(default="", description="Base64-encoded partner logo")
    run_research: Optional[bool] = Field(default=True)


class FlyerEditRequest(BaseModel):
    html: str = Field(..., description="Current flyer HTML to be edited")
    instruction: str = Field(..., min_length=1, max_length=2000, description="Edit instruction from the user")
    width: int = Field(default=1240, ge=320, le=4096)
    height: int = Field(default=1754, ge=320, le=4096)
    formats: Optional[List[str]] = Field(default=["png"], description="Export formats")


class SegmindImageRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=500, example="Futuristic AI data center, teal lighting")
    negative_prompt: Optional[str] = Field(default="blurry, low quality, text, watermark")
    width: Optional[int] = Field(default=1024, ge=512, le=1536)
    height: Optional[int] = Field(default=1024, ge=512, le=1536)
    model: Optional[str] = Field(default="sdxl1.0-txt2img", description="Segmind model slug")


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Social Media Content Agent",
        "version": "2.0.0",
        "pipelines": {
            "social_posts": ["Research", "Content", "Hashtag", "Image", "Database"],
            "video": ["Research", "Content", "Hashtag", "Script", "Scene Images", "Voice", "Video Editor", "Database"],
        },
        "ai_providers": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "segmind": bool(os.getenv("STITCH_API_KEY")),
        },
    }


@app.get("/api/ai-health", tags=["System"])
async def ai_provider_health():
    """Check health of all AI provider integrations"""
    results = {}

    # OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.models.list()
        results["openai"] = {"status": "healthy", "models_available": True}
    except Exception as e:
        results["openai"] = {"status": "error", "error": str(e)[:100]}

    # Segmind (Stitch)
    try:
        segmind = SegmindAgent()
        results["segmind"] = {"status": "healthy", "api": "Segmind", "key_set": True}
    except Exception as e:
        results["segmind"] = {"status": "error", "error": str(e)[:100]}

    overall = "healthy" if all(v.get("status") == "healthy" for v in results.values()) else "partial"
    return {"overall": overall, "providers": results}



# ── Social Post Pipeline ──────────────────────────────────────────────────────
@app.post("/api/generate", tags=["Social Posts"])
async def generate_content(request: GenerateRequest):
    """
    Run the full social post multi-agent pipeline.
    Returns all generated content, images, and database IDs.
    """
    try:
        manager = ManagerAgent()
        result = manager.run(
            topic=request.topic,
            platforms=request.platforms,
            generate_images=request.generate_images,
            run_research=request.run_research,
            article=request.article or "",
            product_info=request.product_info or "",
            custom_content=request.custom_content or "",
            website_url=request.website_url or "",
            blog_url=request.blog_url or "",
            landing_page_url=request.landing_page_url or "",
            company_website_url=request.company_website_url or "",
            image_ratios=request.image_ratios or ["1:1"],
            image_count=request.image_count or 5,
        )
        return {
            "success": True,
            "data": result,
            "message": f"Successfully generated content for {len(request.platforms)} platform(s)",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# ── Async Social Pipeline (with progress polling) ─────────────────────────────

def _run_social_pipeline_bg(job_id: str, request_data: dict):
    """Background thread: run the social pipeline with progress updates."""
    def progress(step: str, status: str, **kwargs):
        job = _social_jobs.get(job_id)
        if not job:
            return
        if status == "running":
            job["current_step"] = step
        elif status == "complete":
            job["current_step"] = step
            if step not in job["completed_steps"]:
                job["completed_steps"].append(step)
        elif status == "failed":
            job.setdefault("step_errors", {})[step] = kwargs.get("error", "Unknown error")

    try:
        manager = ManagerAgent()
        result = manager.run(
            topic=request_data["topic"],
            platforms=request_data.get("platforms"),
            generate_images=request_data.get("generate_images", True),
            run_research=request_data.get("run_research", True),
            article=request_data.get("article", ""),
            product_info=request_data.get("product_info", ""),
            custom_content=request_data.get("custom_content", ""),
            website_url=request_data.get("website_url", ""),
            blog_url=request_data.get("blog_url", ""),
            landing_page_url=request_data.get("landing_page_url", ""),
            company_website_url=request_data.get("company_website_url", ""),
            image_ratios=request_data.get("image_ratios") or ["1:1"],
            image_count=request_data.get("image_count", 5),
            progress_callback=progress,
        )
        _social_jobs[job_id]["result"]       = result
        _social_jobs[job_id]["status"]       = "complete"
        _social_jobs[job_id]["current_step"] = None
        _social_jobs[job_id]["completed_at"] = datetime.now().isoformat()
    except Exception as exc:
        _social_jobs[job_id]["status"]       = "failed"
        _social_jobs[job_id]["error"]        = str(exc)
        _social_jobs[job_id]["current_step"] = None


@app.post("/api/generate/start", tags=["Social Posts"])
async def start_social_generation(request: GenerateRequest):
    """Start the social pipeline in a background thread; poll /api/generate-status/{job_id}."""
    job_id = uuid.uuid4().hex
    _social_jobs[job_id] = {
        "status":          "running",
        "current_step":    "research",
        "completed_steps": [],
        "step_errors":     {},
        "result":          None,
        "error":           None,
        "topic":           request.topic,
        "created_at":      datetime.now().isoformat(),
        "completed_at":    None,
    }
    thread = threading.Thread(
        target=_run_social_pipeline_bg,
        args=(job_id, request.model_dump()),
        daemon=True,
    )
    thread.start()
    return {"success": True, "job_id": job_id}


@app.get("/api/generate-status/{job_id}", tags=["Social Posts"])
async def get_social_status(job_id: str):
    """Poll for social pipeline progress. Returns status + result when done."""
    job = _social_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "success":         True,
        "job_id":          job_id,
        "status":          job["status"],
        "current_step":    job.get("current_step"),
        "completed_steps": job.get("completed_steps", []),
        "step_errors":     job.get("step_errors", {}),
        "result":          job.get("result"),
        "error":           job.get("error"),
        "topic":           job.get("topic"),
        "created_at":      job.get("created_at"),
        "completed_at":    job.get("completed_at"),
    }


@app.get("/api/posts", tags=["Social Posts"])
async def get_all_posts(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, le=200, description="Max results"),
):
    """Get all saved posts, optionally filtered by platform"""
    try:
        posts = db_agent.get_all_posts()
        if platform:
            posts = [p for p in posts if p["platform"].lower() == platform.lower()]
        return {"success": True, "data": posts[:limit], "total": len(posts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/posts/{post_id}", tags=["Social Posts"])
async def get_post(post_id: int):
    """Get a specific post by ID"""
    post = db_agent.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return {"success": True, "data": post}


@app.delete("/api/posts/{post_id}", tags=["Social Posts"])
async def delete_post(post_id: int):
    """Delete a post by ID"""
    success = db_agent.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return {"success": True, "message": f"Post {post_id} deleted successfully"}


# ── Flyer Creator ─────────────────────────────────────────────────────────────
@app.get("/api/flyer-sizes", tags=["Flyer Creator"])
async def get_flyer_sizes():
    """List supported flyer sizes/aspect ratios."""
    from agents.flyer_agent import FLYER_SIZES, FLYER_SIZE_LABELS
    sizes = []
    for key, label in FLYER_SIZE_LABELS.items():
        dims = FLYER_SIZES.get(key)
        sizes.append({
            "id": key,
            "label": label,
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
        })
    return {"success": True, "sizes": sizes, "formats": ["png", "jpg", "pdf"]}


@app.post("/api/flyer/generate", tags=["Flyer Creator"])
async def generate_flyer(request: FlyerRequest):
    """Generate a marketing flyer and export it to the requested formats."""
    if not (request.content or request.topic):
        raise HTTPException(status_code=400, detail="Provide flyer content (or a topic).")
    import base64
    brand_logo_bytes = base64.b64decode(request.brand_logo_b64) if request.brand_logo_b64 else None
    partner_logo_bytes = base64.b64decode(request.partner_logo_b64) if request.partner_logo_b64 else None
    try:
        agent = FlyerAgent()
        result = agent.run(
            content=request.content or "",
            topic=request.topic or "",
            style=request.style or "auto",
            website_url=request.website_url or "",
            custom_content=request.custom_content or "",
            ratio=request.ratio or "a4_portrait",
            custom_width=request.custom_width,
            custom_height=request.custom_height,
            formats=request.formats or ["png", "pdf"],
            brand_name=request.brand_name or "",
            contact_info=request.contact_info or "",
            display_url=request.display_url or "",
            accent_color=request.accent_color or "",
            secondary_color=request.secondary_color or "",
            partner_name=request.partner_name or "",
            brand_logo_url=request.brand_logo_url or "",
            partner_logo_url=request.partner_logo_url or "",
            brand_logo_bytes=brand_logo_bytes,
            partner_logo_bytes=partner_logo_bytes,
            creative=request.creative if request.creative is not None else True,
            run_research=request.run_research if request.run_research is not None else True,
        )
        # Save to the content library (additive, non-breaking)
        try:
            db_agent.save_content_package(
                package_type="flyer",
                topic=result.get("topic") or (request.topic or "Flyer"),
                platforms=[result.get("style", "flyer"), request.ratio or "a4_portrait"],
                data=result,
                thumbnail_url=result.get("preview_url"),
                image_count=len(result.get("files", {})),
                has_video=False,
            )
        except Exception as e:
            print(f"Flyer package save failed: {e}")
        # Ensure the HTML is included so the frontend can do incremental edits
        if "html" not in result:
            result["html"] = ""
        return {"success": True, "data": result, "message": "Flyer generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flyer generation error: {str(e)}")


@app.post("/api/flyer/edit", tags=["Flyer Creator"])
async def edit_flyer(request: FlyerEditRequest):
    """Apply a targeted edit to an existing flyer (ChatGPT-style incremental editing)."""
    try:
        agent = FlyerAgent()
        img, updated_html = agent.edit_html(
            current_html=request.html,
            instruction=request.instruction,
            w=request.width,
            h=request.height,
        )
        if img is None:
            raise RuntimeError("Chrome render returned no image after edit")
        # Export as PNG (and optionally other formats)
        base = f"flyer_edit_{uuid.uuid4().hex[:8]}"
        files = agent.export(img, base, request.formats or ["png"])
        file_urls = {k: f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/output/{os.path.basename(v)}"
                     for k, v in files.items()}
        return {
            "success": True,
            "data": {
                "html": updated_html,
                "files": file_urls,
                "preview_url": file_urls.get("png") or next(iter(file_urls.values()), None),
                "engine": "ai_html_edit",
            },
            "message": "Flyer edit applied",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flyer edit error: {str(e)}")


# ── Content Packages (complete repository) ────────────────────────────────────
@app.get("/api/packages", tags=["Content Packages"])
async def get_content_packages(limit: int = Query(100, le=300)):
    """Get all complete content packages (social + video), newest first."""
    try:
        packages = db_agent.get_content_packages(limit=limit)
        return {"success": True, "data": packages, "total": len(packages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/packages/{package_id}", tags=["Content Packages"])
async def get_content_package(package_id: int):
    """Get a single complete content package by ID."""
    pkg = db_agent.get_content_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return {"success": True, "data": pkg}


@app.delete("/api/packages/{package_id}", tags=["Content Packages"])
async def delete_content_package(package_id: int):
    """Delete a content package by ID."""
    success = db_agent.delete_content_package(package_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Package {package_id} not found")
    return {"success": True, "message": f"Package {package_id} deleted"}


# ── Video Pipeline ────────────────────────────────────────────────────────────

def _run_video_pipeline_bg(job_id: str, request_data: dict):
    """Background thread: run the video pipeline and update _video_jobs[job_id]."""
    def progress(step: str, status: str, **kwargs):
        job = _video_jobs.get(job_id)
        if not job:
            return
        if status == "running":
            job["current_step"] = step
        elif status == "complete":
            job["current_step"] = step
            if step not in job["completed_steps"]:
                job["completed_steps"].append(step)
        elif status == "failed":
            job["step_errors"] = job.get("step_errors", {})
            job["step_errors"][step] = kwargs.get("error", "Unknown error")

    try:
        manager = ManagerAgent()
        result = manager.run_video(
            topic=request_data["topic"],
            run_research=request_data.get("run_research", True),
            progress_callback=progress,
            target_duration=request_data.get("duration_sec", 45),
            aspect_ratio=request_data.get("aspect_ratio", "9:16"),
            article=request_data.get("article", ""),
            product_info=request_data.get("product_info", ""),
            custom_content=request_data.get("custom_content", ""),
            website_url=request_data.get("website_url", ""),
            blog_url=request_data.get("blog_url", ""),
            landing_page_url=request_data.get("landing_page_url", ""),
            company_website_url=request_data.get("company_website_url", ""),
        )
        _video_jobs[job_id]["result"]       = result
        _video_jobs[job_id]["status"]       = "complete"
        _video_jobs[job_id]["current_step"] = None
        _video_jobs[job_id]["completed_at"] = datetime.now().isoformat()
    except Exception as exc:
        _video_jobs[job_id]["status"]       = "failed"
        _video_jobs[job_id]["error"]        = str(exc)
        _video_jobs[job_id]["current_step"] = None


@app.post("/api/video-generate/start", tags=["Video"])
async def start_video_generation(request: VideoGenerateRequest):
    """
    Start the video pipeline in a background thread.
    Returns {job_id} immediately — poll /api/video-status/{job_id} for progress.
    """
    job_id = uuid.uuid4().hex
    _video_jobs[job_id] = {
        "status":          "running",
        "current_step":    "research",
        "completed_steps": [],
        "step_errors":     {},
        "result":          None,
        "error":           None,
        "topic":           request.topic,
        "created_at":      datetime.now().isoformat(),
        "completed_at":    None,
    }
    thread = threading.Thread(
        target=_run_video_pipeline_bg,
        args=(job_id, request.model_dump()),
        daemon=True,
    )
    thread.start()
    return {"success": True, "job_id": job_id}


@app.get("/api/video-status/{job_id}", tags=["Video"])
async def get_video_status(job_id: str):
    """Poll for video pipeline progress. Returns status + partial data as steps complete."""
    job = _video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "success":         True,
        "job_id":          job_id,
        "status":          job["status"],          # running | complete | failed
        "current_step":    job.get("current_step"),
        "completed_steps": job.get("completed_steps", []),
        "step_errors":     job.get("step_errors", {}),
        "result":          job.get("result"),
        "error":           job.get("error"),
        "topic":           job.get("topic"),
        "created_at":      job.get("created_at"),
        "completed_at":    job.get("completed_at"),
    }


@app.post("/api/video-generate", tags=["Video"])
async def generate_video(request: VideoGenerateRequest):
    """
    Run the full short-video content pipeline.

    Pipeline:
        1. Research Agent  — context synthesis
        2. Content Agent   — LinkedIn/Instagram/Twitter posts
        3. Hashtag Agent   — hashtag enrichment
        4. Script Agent    — 6-scene Reel script (Claude)
        5. Image Agent     — DALL-E 3 scene images
        6. Voice Agent     — voiceover script + OpenAI TTS MP3
        7. Video Editor    — MoviePy assembles final MP4
        8. Database Agent  — saves to video_projects

    Returns all content, audio filename, video filename, and DB project ID.
    """
    try:
        manager = ManagerAgent()
        result = manager.run_video(
            topic=request.topic,
            run_research=request.run_research,
            target_duration=request.duration_sec or 45,
            aspect_ratio=request.aspect_ratio or "9:16",
            article=request.article or "",
            product_info=request.product_info or "",
            custom_content=request.custom_content or "",
            website_url=request.website_url or "",
            blog_url=request.blog_url or "",
            landing_page_url=request.landing_page_url or "",
            company_website_url=request.company_website_url or "",
        )
        return {
            "success": True,
            "data": result,
            "message": f"Video pipeline complete for topic: {request.topic}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video pipeline error: {str(e)}")


@app.get("/api/video-projects", tags=["Video"])
async def get_video_projects(limit: int = Query(20, le=100)):
    """Get all saved video projects"""
    try:
        projects = db_agent.get_video_projects(limit=limit)
        return {"success": True, "data": projects, "total": len(projects)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video-projects/{project_id}", tags=["Video"])
async def get_video_project(project_id: int):
    """Get a specific video project by DB ID"""
    project = db_agent.get_video_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Video project {project_id} not found")
    return {"success": True, "data": project}


@app.get("/api/video-file/{filename}", tags=["Video"])
async def serve_video_file(filename: str, download: bool = Query(False, description="Force download")):
    """
    Serve a generated MP4 or MP3 file.

    By default serves INLINE (Content-Disposition: inline) so HTML5 <video>/<audio>
    can play it directly. Starlette's FileResponse already honours HTTP Range
    requests, which browsers need for seeking. Pass ?download=true to force a
    download (used by the Download buttons).
    """
    # Basic path-traversal guard
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {safe_name} not found")

    media_type = "video/mp4" if safe_name.endswith(".mp4") else "audio/mpeg"
    disposition = "attachment" if download else "inline"
    # content_disposition_type keeps Starlette's built-in HTTP Range handling
    # intact (needed for <video>/<audio> seeking) while controlling inline vs
    # attachment behaviour.
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=safe_name,
        content_disposition_type=disposition,
    )


# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/api/stats", tags=["Analytics"])
async def get_stats():
    """Get content generation statistics and recent activity"""
    try:
        stats = db_agent.get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# ── Settings ──────────────────────────────────────────────────────────────────
@app.get("/api/settings", tags=["Settings"])
async def get_settings():
    """Get global application settings"""
    try:
        settings = db_agent.get_settings()
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings", tags=["Settings"])
async def update_settings(settings: dict):
    """Update global application settings"""
    try:
        db_agent.update_settings(settings)
        return {"success": True, "data": db_agent.get_settings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/upload", tags=["Settings"])
async def upload_setting_image(file: UploadFile = File(...)):
    """Upload logo or favicon and return URL"""
    try:
        file_ext = file.filename.split(".")[-1]
        new_filename = f"branding_{uuid.uuid4().hex[:8]}.{file_ext}"
        file_path = os.path.join(OUTPUT_DIR, new_filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        url = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/output/{new_filename}"
        return {"success": True, "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Segmind Endpoints ─────────────────────────────────────────────────────────
@app.post("/api/segmind-image", tags=["Segmind (Stitch)"])
async def segmind_generate_image(request: SegmindImageRequest):
    """
    Generate an image using Segmind's AI platform (SDXL, Flux, etc.).
    Returns local file path or image URL.
    """
    try:
        segmind = SegmindAgent()
        result = segmind.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "blurry, low quality, text, watermark",
            width=request.width or 1024,
            height=request.height or 1024,
            model=request.model or "sdxl1.0-txt2img",
        )
        return {"success": result.get("status") == "success", "provider": "segmind", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmind error: {str(e)}")


@app.get("/api/segmind-models", tags=["Segmind (Stitch)"])
async def get_segmind_models():
    """List available Segmind image generation models"""
    return {
        "success": True,
        "provider": "segmind",
        "models": {
            "sdxl1.0-txt2img": "Stable Diffusion XL — high quality, versatile",
            "flux-schnell": "Flux Schnell — fast, great for concepts",
            "realistic-vision-v6": "Realistic Vision v6 — photorealistic",
            "portrait-diffusion": "Portrait Diffusion — professional portraits",
            "video-stitch": "Video Stitch — combine clips into MP4",
        }
    }


# ── Dev Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
