"""
Flyer Agent — Generates PROFESSIONAL, design-varied marketing flyers from CONTENT.

Content-first: copy (headline, sub-headline, features, benefits, stats,
testimonial, CTA) is derived from the supplied content. A theming + layout
engine produces visibly different flyers each run — 9 styles (corporate,
educational, modern, premium, technology, startup, marketing, event,
professional) × randomized layout knobs (header / hero / banner / icon / CTA
shapes + section order). Brand-aware: when a website URL is given it pulls the
company name, a logo, and brand colors automatically.

Exports PNG / JPG / PDF. Hero photo via Segmind (gradient fallback); all text,
cards, icons and the QR code are composed with PIL so copy is always crisp.
"""

import os
import re
import json
import math
import uuid
import random
from io import BytesIO
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
from dotenv import load_dotenv

from .image_agent import ImageAgent
from .web_research_agent import WebResearchAgent

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

FLYER_SIZES = {
    "a4_portrait":  (1240, 1754),
    "a4_landscape": (1754, 1240),
    "1:1":          (1080, 1080),
    "4:5":          (1080, 1350),
    "9:16":         (1080, 1920),
    "16:9":         (1920, 1080),
    "facebook":     (1200, 630),
    "linkedin":     (1200, 627),
}
FLYER_SIZE_LABELS = {
    "a4_portrait":  "A4 Portrait (Print)",
    "a4_landscape": "A4 Landscape (Print)",
    "1:1":          "1:1 (Instagram Post)",
    "4:5":          "4:5 (Instagram Portrait)",
    "9:16":         "9:16 (Stories/Reels)",
    "16:9":         "16:9 (Presentation/Banner)",
    "facebook":     "Facebook Post",
    "linkedin":     "LinkedIn Post",
    "custom":       "Custom Dimensions",
}

# ── Style presets — each gives a distinct palette + shape language ──────────────
# bg (top,bot) gradient · primary · secondary · header · banner · icon · cta · headline weight/caps
STYLE_PRESETS = {
    "corporate":    dict(bg=((12, 26, 54), (6, 14, 32)),  primary=(43, 108, 214), secondary=(240, 180, 60),
                         header="white", banner="flat",  icon="round",  cta="card",   weight="bold",  caps=True),
    "educational":  dict(bg=((10, 22, 52), (6, 13, 33)),  primary=(37, 99, 235),  secondary=(255, 122, 0),
                         header="white", banner="ribbon", icon="circle", cta="card",   weight="black", caps=True),
    "modern":       dict(bg=((24, 24, 38), (12, 12, 22)), primary=(124, 92, 255), secondary=(0, 209, 255),
                         header="minimal", banner="pill", icon="circle", cta="banner", weight="black", caps=True),
    "premium":      dict(bg=((18, 16, 12), (8, 7, 6)),    primary=(201, 162, 39),  secondary=(230, 210, 150),
                         header="minimal", banner="tag",  icon="hex",    cta="split",  weight="bold",  caps=True),
    "technology":   dict(bg=((6, 18, 30), (4, 10, 18)),   primary=(0, 200, 160),   secondary=(0, 180, 255),
                         header="color", banner="pill",  icon="hex",    cta="banner", weight="black", caps=True),
    "startup":      dict(bg=((22, 20, 46), (14, 12, 30)), primary=(255, 90, 95),   secondary=(120, 110, 255),
                         header="color", banner="pill",  icon="circle", cta="card",   weight="black", caps=False),
    "marketing":    dict(bg=((40, 14, 46), (18, 8, 30)),  primary=(233, 64, 138),  secondary=(255, 150, 40),
                         header="color", banner="ribbon", icon="circle", cta="banner", weight="black", caps=True),
    "event":        dict(bg=((30, 14, 54), (14, 8, 30)),  primary=(160, 90, 255),  secondary=(255, 100, 170),
                         header="minimal", banner="tag",  icon="circle", cta="card",   weight="black", caps=True),
    "professional": dict(bg=((16, 30, 36), (8, 16, 22)),  primary=(20, 160, 130),  secondary=(90, 200, 180),
                         header="white", banner="flat",  icon="round",  cta="card",   weight="bold",  caps=False),
    "modern_marketing_poster": dict(bg=((18, 20, 36), (8, 10, 22)),  primary=(255, 60, 90),   secondary=(255, 180, 50),
                         header="color", banner="ribbon", icon="circle", cta="banner", weight="black", caps=True),
    "educational_premium": dict(bg=((6, 26, 64), (4, 14, 38)),   primary=(255, 120, 30),  secondary=(40, 160, 255),
                         header="minimal", banner="tag",  icon="circle", cta="split",  weight="black", caps=True),
    "tech_startup":      dict(bg=((12, 18, 30), (6, 10, 18)),   primary=(0, 220, 180),   secondary=(160, 80, 255),
                         header="color", banner="pill",  icon="hex",    cta="banner", weight="black", caps=False),
    "ai_product_launch": dict(bg=((20, 10, 35), (10, 5, 20)),   primary=(180, 70, 255),  secondary=(0, 200, 255),
                         header="minimal", banner="tag",  icon="circle", cta="card",   weight="black", caps=True),
    "event_promotion":   dict(bg=((35, 15, 35), (15, 5, 20)),   primary=(255, 70, 150),  secondary=(255, 190, 40),
                         header="color", banner="pill",  icon="round",  cta="banner", weight="black", caps=True),
    "corporate_premium": dict(bg=((20, 24, 30), (10, 12, 16)),  primary=(200, 160, 50),  secondary=(240, 210, 130),
                         header="minimal", banner="flat",  icon="hex",    cta="card",   weight="bold",  caps=True),
    "magazine_style":    dict(bg=((24, 20, 16), (12, 10, 8)),   primary=(240, 90, 80),   secondary=(255, 200, 120),
                         header="white", banner="tag",  icon="circle", cta="split",  weight="black", caps=True),
    "canva_premium":     dict(bg=((25, 18, 40), (12, 8, 20)),   primary=(120, 80, 255),  secondary=(255, 100, 160),
                         header="color", banner="ribbon", icon="round",  cta="banner", weight="black", caps=True),
    "social_media_poster": dict(bg=((10, 14, 26), (4, 8, 16)),  primary=(0, 210, 255),   secondary=(255, 60, 120),
                         header="minimal", banner="pill",  icon="circle", cta="card",   weight="bold",  caps=False),
    "bold_advertising_poster": dict(bg=((22, 12, 16), (10, 4, 8)), primary=(255, 50, 50), secondary=(255, 220, 20),
                         header="color", banner="flat",  icon="hex",    cta="banner", weight="black", caps=True),
}
STYLE_NAMES = list(STYLE_PRESETS.keys())

WIN_BOLD    = "C:/Windows/Fonts/arialbd.ttf"
WIN_BLACK   = "C:/Windows/Fonts/ariblk.ttf"
WIN_REG     = "C:/Windows/Fonts/arial.ttf"
WHITE       = (255, 255, 255)

# Structurally DIFFERENT layout archetypes (not just color swaps)
LAYOUTS = ["hero_top", "split", "fullbleed", "poster", "sidebar", "editorial"]


def _hex(h, default=(37, 99, 235)):
    try:
        h = (h or "").strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))


class FlyerAgent:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.image_agent = ImageAgent()
        self.web_research_agent = WebResearchAgent()
        self.prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    # ── Copy ────────────────────────────────────────────────────────────────────

    def _load_prompt(self):
        with open(os.path.join(self.prompts_dir, "flyer.txt"), "r", encoding="utf-8") as f:
            return f.read()

    def _extract_json(self, text):
        try:
            return json.loads(text.strip())
        except Exception:
            pass
        for pat in (r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", r"\{[\s\S]*\}"):
            m = re.search(pat, text)
            if m:
                try:
                    return json.loads(m.group(1) if m.lastindex else m.group())
                except Exception:
                    continue
        return {}

    def generate_copy(self, content, context_block=""):
        prompt = self._load_prompt().replace("{content}", content[:35000]).replace("{context_block}", context_block)
        try:
            resp = self.openai.chat.completions.create(
                model=self.model, max_tokens=1500, timeout=80, temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )
            data = self._extract_json(resp.choices[0].message.content)
        except Exception as e:
            print(f"    ⚠️  Flyer copy failed: {e}")
            data = {}

        first_line = (content.strip().splitlines() or [content])[0][:60]
        data.setdefault("headline", first_line.upper())
        data.setdefault("subheadline", "")
        data.setdefault("intro_heading", "")
        data.setdefault("intro_paragraph", content.strip()[:240])
        data.setdefault("section_banner", "WHY CHOOSE US")
        data.setdefault("feature_cards", [])
        data.setdefault("benefits", [])
        data.setdefault("stats", [])
        data.setdefault("testimonial", {})
        data.setdefault("call_to_action", "Get Started Today")
        data.setdefault("cta_subtext", "")
        data.setdefault("tagline", "")
        data.setdefault("suggested_primary", "")
        data.setdefault("suggested_secondary", "")
        data.setdefault("background_prompt", f"Professional commercial hero photo for: {first_line}, bright, clean, copy space, no text")
        if not data.get("features"):
            data["features"] = [c.get("title", "") for c in data.get("feature_cards", []) if c.get("title")]
        if not data["feature_cards"] and data.get("features"):
            data["feature_cards"] = [{"title": f, "description": "", "icon": "star"} for f in data["features"][:5]]
        return data

    # ── Brand assets from website (logo + colors) ───────────────────────────────

    def _extract_brand_assets(self, url):
        """Best-effort: pull a logo URL and dominant brand colors from a website."""
        out = {"logo_url": None, "colors": []}
        if not url:
            return out
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            html = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}).text
            soup = BeautifulSoup(html, "html.parser")
            cand = None
            apple = soup.find("link", rel=lambda v: v and "apple-touch-icon" in v.lower())
            og = soup.find("meta", property="og:image")
            icon = soup.find("link", rel=lambda v: v and v.lower() in ("icon", "shortcut icon"))
            logo_img = soup.find("img", src=lambda v: v and "logo" in v.lower())
            for c, attr in ((apple, "href"), (logo_img, "src"), (og, "content"), (icon, "href")):
                if c and c.get(attr):
                    cand = urljoin(url, c.get(attr)); break
            out["logo_url"] = cand
            # Colors from og:image (or logo)
            img_url = (urljoin(url, og.get("content")) if og and og.get("content") else cand)
            if img_url:
                try:
                    raw = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}).content
                    out["colors"] = self._palette_from_image(Image.open(BytesIO(raw)))
                except Exception:
                    pass
        except Exception as e:
            print(f"    ⚠️  Brand asset extraction failed: {e}")
        return out

    @staticmethod
    def _palette_from_image(img):
        img = img.convert("RGB").resize((64, 64))
        vivid = [p for p in img.getdata() if (max(p) - min(p)) > 45 and 35 < sum(p)/3 < 225]
        if not vivid:
            return []
        common = [c for c, _ in Counter(vivid).most_common(10)]
        picked = []
        for c in common:
            if all(sum((c[i]-p[i])**2 for i in range(3)) > 2600 for p in picked):
                picked.append(c)
            if len(picked) >= 2:
                break
        return picked

    # ── Hero / background ────────────────────────────────────────────────────────

    @staticmethod
    def _color_name(rgb):
        """Coarse human color name for an RGB tuple (for image prompts)."""
        import colorsys
        r, g, b = rgb
        hh, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if s < 0.18:
            return "white" if v > 0.65 else ("light gray" if v > 0.4 else "charcoal")
        deg = hh * 360
        for d, n in [(16, "red"), (45, "orange"), (66, "gold"), (90, "lime"),
                     (160, "green"), (200, "teal"), (255, "blue"),
                     (290, "purple"), (330, "magenta"), (361, "red")]:
            if deg < d:
                return n
        return "blue"

    def _generate_hero(self, bg_prompt, w, h, primary=None, secondary=None):
        """
        Generate a PREMIUM MARKETING-POSTER hero scene (not a plain stock photo):
        a composed advertising scene with the subject on the right and clean copy
        space on the left, modern tech aesthetic, brand-colored glow.
        """
        accent = ""
        if primary and secondary:
            accent = (f" Color grade: deep navy blue background with glowing "
                      f"{self._color_name(primary)} and {self._color_name(secondary)} accent lighting.")
        full_prompt = (
            f"{bg_prompt}. Premium MARKETING POSTER hero scene, cinematic dramatic lighting, "
            f"professional commercial advertising photography, ultra-detailed, 8k, high visual impact, "
            f"the main subject placed on the RIGHT side of the frame with clean empty negative space "
            f"on the LEFT for text overlay, modern futuristic technology aesthetic with subtle glowing "
            f"network/connection lines and soft bokeh.{accent} "
            f"No text, no words, no typography, no watermark, no logo."
        )
        neg = ("text, words, typography, captions, watermark, logo, signature, ugly, deformed, "
               "low quality, blurry, distorted, jpeg artifacts, cartoonish, flat, plain background")
        sw, sh = min(w, 1536), min(h, 1536)
        try:
            r = self.image_agent.segmind.generate_image(
                prompt=full_prompt, negative_prompt=neg,
                width=sw, height=sh, filename=f"flyer_bg_{uuid.uuid4().hex[:8]}.png",
            )
            if r.get("status") == "success" and r.get("local_path") and os.path.exists(r["local_path"]):
                return Image.open(r["local_path"]).convert("RGB")
        except Exception as e:
            print(f"    ⚠️  Hero generation error: {e}")
        return self._grad_v(w, h, (24, 44, 92), (10, 18, 40))

    @staticmethod
    def _grad_v(w, h, top, bot):
        base = Image.new("RGB", (1, h)); px = base.load()
        for y in range(h):
            px[0, y] = _mix(top, bot, y / max(1, h-1))
        return base.resize((w, h))

    @staticmethod
    def _cover(img, w, h):
        sw, sh = img.size; sc = max(w/sw, h/sh)
        nw, nh = int(math.ceil(sw*sc)), int(math.ceil(sh*sc))
        img = img.resize((nw, nh), Image.LANCZOS)
        return img.crop(((nw-w)//2, (nh-h)//2, (nw-w)//2+w, (nh-h)//2+h))

    def _fetch_logo(self, url, max_h):
        if not url:
            return None
        try:
            raw = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}).content
            img = Image.open(BytesIO(raw)).convert("RGBA")
            ratio = max_h / img.height
            return img.resize((max(1, int(img.width*ratio)), max_h), Image.LANCZOS)
        except Exception as e:
            print(f"    ⚠️  Logo fetch failed: {e}")
            return None

    # ── Fonts / text ─────────────────────────────────────────────────────────────

    @staticmethod
    def _font(kind, size):
        path = {"black": WIN_BLACK, "bold": WIN_BOLD, "reg": WIN_REG}.get(kind, WIN_BOLD)
        for p in (path, WIN_BOLD, WIN_REG):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap(draw, text, font, max_w):
        out, cur = [], ""
        for word in (text or "").split():
            t = (cur + " " + word).strip()
            if draw.textlength(t, font=font) <= max_w or not cur:
                cur = t
            else:
                out.append(cur); cur = word
        if cur:
            out.append(cur)
        return out

    # ── Shapes ────────────────────────────────────────────────────────────────

    def _disc(self, draw, shape, cx, cy, r, color):
        if shape == "round":
            draw.rounded_rectangle([cx-r, cy-r, cx+r, cy+r], radius=int(r*0.45), fill=color)
        elif shape == "hex":
            pts = [(cx + r*math.cos(math.pi/6 + i*math.pi/3), cy + r*math.sin(math.pi/6 + i*math.pi/3)) for i in range(6)]
            draw.polygon(pts, fill=color)
        else:
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)

    def _icon(self, layer, kind, cx, cy, r, color, shape="circle"):
        d = ImageDraw.Draw(layer)
        self._disc(d, shape, cx, cy, r, color)
        w = WHITE; lw = max(2, int(r*0.12)); s = r*0.52
        k = (kind or "star").lower()
        if k == "person":
            hr = r*0.26; d.ellipse([cx-hr, cy-r*0.5, cx+hr, cy-r*0.5+2*hr], fill=w)
            d.pieslice([cx-r*0.45, cy-r*0.02, cx+r*0.45, cy+r*0.9], 180, 360, fill=w)
        elif k in ("document", "lock"):
            d.rounded_rectangle([cx-s*0.7, cy-s, cx+s*0.7, cy+s], radius=int(r*0.1), fill=w)
            for i, yy in enumerate((-s*0.45, -s*0.1, s*0.25)):
                d.line([cx-s*0.45, cy+yy, cx+s*0.45*(1-0.2*i), cy+yy], fill=color, width=lw)
        elif k == "cap":
            d.polygon([(cx, cy-s), (cx+s, cy-s*0.3), (cx, cy+s*0.4), (cx-s, cy-s*0.3)], fill=w)
            d.rectangle([cx-s*0.45, cy-s*0.1, cx+s*0.45, cy+s*0.6], fill=w)
        elif k in ("clock", "target"):
            d.ellipse([cx-s, cy-s, cx+s, cy+s], outline=w, width=lw)
            d.line([cx, cy, cx, cy-s*0.6], fill=w, width=lw); d.line([cx, cy, cx+s*0.45, cy], fill=w, width=lw)
        elif k in ("globe", "cloud"):
            d.ellipse([cx-s, cy-s, cx+s, cy+s], outline=w, width=lw)
            d.ellipse([cx-s*0.45, cy-s, cx+s*0.45, cy+s], outline=w, width=lw); d.line([cx-s, cy, cx+s, cy], fill=w, width=lw)
        elif k == "chart":
            for i, hh in enumerate((0.4, 0.7, 1.0)):
                bx = cx-s + i*(s*0.8); d.rectangle([bx, cy+s-2*s*hh, bx+s*0.45, cy+s], fill=w)
        elif k == "rocket":
            d.polygon([(cx, cy-s), (cx+s*0.55, cy+s*0.3), (cx-s*0.55, cy+s*0.3)], fill=w)
            d.ellipse([cx-s*0.2, cy-s*0.2, cx+s*0.2, cy+s*0.2], fill=color)
        elif k in ("shield", "gear"):
            d.polygon([(cx, cy-s), (cx+s*0.8, cy-s*0.5), (cx+s*0.6, cy+s*0.7), (cx, cy+s), (cx-s*0.6, cy+s*0.7), (cx-s*0.8, cy-s*0.5)], fill=w)
            d.line([(cx-s*0.35, cy), (cx-s*0.05, cy+s*0.35), (cx+s*0.45, cy-s*0.35)], fill=color, width=lw)
        elif k in ("bulb", "heart"):
            d.ellipse([cx-s*0.6, cy-s, cx+s*0.6, cy+s*0.2], fill=w); d.rectangle([cx-s*0.3, cy+s*0.2, cx+s*0.3, cy+s*0.7], fill=w)
        else:
            pts = []
            for i in range(10):
                ang = -math.pi/2 + i*math.pi/5; rr = s if i % 2 == 0 else s*0.45
                pts.append((cx+rr*math.cos(ang), cy+rr*math.sin(ang)))
            d.polygon(pts, fill=w)

    def _banner(self, draw, shape, cx_center, y, text, font, h, color, text_color=WHITE):
        tw = draw.textlength(text, font=font)
        pad = h
        x0 = cx_center - (tw + pad*2)/2; x1 = cx_center + (tw + pad*2)/2
        if shape == "ribbon":
            draw.polygon([(x0+h*0.5, y), (x1-h*0.5, y), (x1, y+h/2), (x1-h*0.5, y+h), (x0+h*0.5, y+h), (x0, y+h/2)], fill=color)
        elif shape == "pill":
            draw.rounded_rectangle([x0, y, x1, y+h], radius=int(h/2), fill=color)
        elif shape == "tag":
            draw.polygon([(x0, y), (x1, y), (x1, y+h), (x0, y+h), (x0-h*0.4, y+h/2)], fill=color)
        else:  # flat
            draw.rectangle([x0, y, x1, y+h], fill=color)
        draw.text((cx_center - tw/2, y + (h-font.size)/2 - 2), text, font=font, fill=text_color)
        return y + h

    # ── QR ──────────────────────────────────────────────────────────────────────

    def _make_qr(self, data, box):
        if not data:
            return None
        try:
            import qrcode
            qr = qrcode.QRCode(border=2, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(data); qr.make(fit=True)
            return qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((box, box), Image.NEAREST)
        except Exception as e:
            print(f"    ⚠️  QR failed: {e}")
            return None

    # ── Theme builder ─────────────────────────────────────────────────────────

    def _build_theme(self, style, copy, primary_override, secondary_override, brand_colors, rng):
        if style == "auto" or style not in STYLE_PRESETS:
            style = rng.choice(STYLE_NAMES)
        p = dict(STYLE_PRESETS[style])

        # Colors: explicit override > brand colors (website) > AI suggestion > style default
        primary = _hex(primary_override) if primary_override else None
        secondary = _hex(secondary_override) if secondary_override else None
        if not primary and brand_colors:
            primary = brand_colors[0]
        if not secondary and len(brand_colors) > 1:
            secondary = brand_colors[1]
        if not primary and copy.get("suggested_primary"):
            primary = _hex(copy["suggested_primary"], p["primary"])
        if not secondary and copy.get("suggested_secondary"):
            secondary = _hex(copy["suggested_secondary"], p["secondary"])
        primary = primary or p["primary"]
        secondary = secondary or p["secondary"]

        # Pick a structurally distinct LAYOUT archetype + randomize typography,
        # so repeated generations differ in structure, not just colour.
        layout = rng.choice(LAYOUTS)
        align = rng.choice(["left", "left", "center"])
        feature_mode = rng.choice(["row", "grid"])
        body = []
        if copy.get("stats"):                          body.append("stats")
        if copy.get("testimonial", {}).get("quote"):   body.append("testimonial")
        rng.shuffle(body)

        return {
            "style": style, "bg": p["bg"], "primary": primary, "secondary": secondary,
            "header": p["header"], "banner": p["banner"], "icon": p["icon"], "cta": p["cta"],
            "weight": p["weight"], "caps": p["caps"],
            "layout": layout, "align": align, "feature_mode": feature_mode,
            "body_sections": body,
        }

    # ── Composition engine — 6 structurally distinct layouts ───────────────────

    @staticmethod
    def _lum(c):
        return 0.299*c[0] + 0.587*c[1] + 0.114*c[2]

    def _text_on(self, bg):
        return (18, 24, 40) if self._lum(bg) > 150 else (255, 255, 255)

    def _muted_on(self, bg):
        return (96, 108, 128) if self._lum(bg) > 150 else (165, 178, 198)

    def compose(self, copy, hero, w, h, brand_name, partner_name, display_url,
                contact_info, theme, qr_data, brand_logo, partner_logo, rng=None):
        rng = rng or random.Random()
        ctx = dict(copy=copy, hero=hero, w=w, h=h, brand=brand_name, partner=partner_name,
                   url=display_url, contact=contact_info, theme=theme, qr=qr_data,
                   logo=brand_logo, plogo=partner_logo, rng=rng, s=max(0.5, min(w/1080.0, h/1500.0)),
                   margin=int(w*0.06))
        layouts = {
            "hero_top": self._layout_hero_top, "split": self._layout_split,
            "fullbleed": self._layout_fullbleed, "poster": self._layout_poster,
            "sidebar": self._layout_sidebar, "editorial": self._layout_editorial,
        }
        fn = layouts.get(theme.get("layout"), self._layout_hero_top)
        try:
            return fn(ctx)
        except Exception as e:
            print(f"    ⚠️  Layout '{theme.get('layout')}' failed ({e}) — fallback to hero_top")
            return self._layout_hero_top(ctx)

    # ── Shared widgets ──────────────────────────────────────────────────────────

    def _brandmark(self, canvas, draw, x, y, brand, color, size, logo=None):
        if logo is not None:
            canvas.paste(logo, (int(x), int(y)), logo)
        else:
            draw.text((x, y), (brand or "BRAND").upper(), font=self._font("black", int(size)), fill=color)

    def _headline(self, draw, x, y, maxw, copy, theme, color, accent, s, align="left", factor=1.0, max_lines=3):
        txt = copy.get("headline", "")
        if theme.get("caps"):
            txt = txt.upper()
        f = self._font(theme.get("weight", "black"), int(62*s*factor))
        lines = self._wrap(draw, txt, f, maxw)[:max_lines]
        lh = int(62*s*factor) + int(6*s)
        for i, ln in enumerate(lines):
            lw = draw.textlength(ln, font=f)
            lx = x + (maxw-lw)/2 if align == "center" else x
            draw.text((lx+2, y+2), ln, font=f, fill=(0, 0, 0))
            draw.text((lx, y), ln, font=f, fill=accent if i == len(lines)-1 else color)
            y += lh
        return y

    def _para(self, draw, x, y, maxw, text, color, size, s, align="left", max_lines=4, gap=7):
        if not text:
            return y
        f = self._font("reg", int(size*s))
        for ln in self._wrap(draw, text, f, maxw)[:max_lines]:
            lw = draw.textlength(ln, font=f)
            lx = x + (maxw-lw)/2 if align == "center" else x
            draw.text((lx, y), ln, font=f, fill=color)
            y += int(size*s) + int(gap*s)
        return y

    def _hero_into(self, canvas, box, hero, theme, dirn="bottom"):
        x, y, bw, bh = [int(v) for v in box]
        img = self._cover(hero, bw, bh); canvas.paste(img, (x, y))
        ov = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); nb = theme["bg"][1]
        if dirn in ("bottom", "both"):
            for i in range(int(bh*0.5)):
                od.rectangle([0, bh-i, bw, bh-i+1], fill=(nb[0], nb[1], nb[2], int(225*(1-i/(bh*0.5)))))
        if dirn in ("left", "both"):
            for xx in range(int(bw*0.62)):
                od.rectangle([xx, 0, xx+1, bh], fill=(nb[0], nb[1], nb[2], int(225*(1-xx/(bw*0.62)))))
        if dirn in ("right",):
            for xx in range(int(bw*0.62)):
                od.rectangle([bw-xx, 0, bw-xx+1, bh], fill=(nb[0], nb[1], nb[2], int(225*(1-xx/(bw*0.62)))))
        if dirn == "full":
            od.rectangle([0, 0, bw, bh], fill=(nb[0], nb[1], nb[2], 155))
        canvas.paste(Image.alpha_composite(Image.new("RGBA", (bw, bh), (0,0,0,0)), ov), (x, y), ov)

    def _wg_features(self, canvas, x, y, w, copy, theme, tcol, mcol, s, mode="row", max_items=5):
        cards = (copy.get("feature_cards") or [])[:max_items]
        if not cards:
            return y
        draw = ImageDraw.Draw(canvas); pri, sec = theme["primary"], theme["secondary"]
        if mode == "row":
            n = len(cards); gap = int(14*s); cwid = (w-gap*(n-1))/n; ir = int(min(cwid*0.22, 38*s))
            tf = self._font("bold", int(19*s)); df = self._font("reg", int(14*s)); top = y
            for i, c in enumerate(cards):
                cx0 = x + i*(cwid+gap); ccx = cx0 + cwid/2
                self._icon(canvas, c.get("icon", "star"), int(ccx), int(top+ir+int(4*s)), ir, pri if i % 2 == 0 else sec, theme["icon"])
                yy = top + 2*ir + int(14*s)
                for ln in self._wrap(draw, c.get("title", ""), tf, cwid)[:2]:
                    lw = draw.textlength(ln, font=tf); draw.text((ccx-lw/2, yy), ln, font=tf, fill=tcol); yy += int(19*s)+int(3*s)
                for ln in self._wrap(draw, c.get("description", ""), df, cwid-int(8*s))[:2]:
                    lw = draw.textlength(ln, font=df); draw.text((ccx-lw/2, yy), ln, font=df, fill=mcol); yy += int(14*s)+int(2*s)
            return top + int(150*s) + int(14*s)
        else:
            n = len(cards); cols = 2; gap = int(14*s); cwid = (w-gap*(cols-1))/cols; ch = int(138*s)
            tf = self._font("bold", int(20*s)); df = self._font("reg", int(14*s)); rows = (n+1)//2
            for i, c in enumerate(cards):
                r = i//cols; col = i % cols; cx0 = x + col*(cwid+gap); cy0 = y + r*(ch+gap)
                draw.rounded_rectangle([cx0, cy0, cx0+cwid, cy0+ch], radius=int(14*s), fill=_mix(theme["bg"][0], (255,255,255), 0.07))
                ir = int(26*s); self._icon(canvas, c.get("icon", "star"), int(cx0+int(32*s)), int(cy0+int(34*s)), ir, pri if i % 2 == 0 else sec, theme["icon"])
                tx = cx0 + int(18*s); ty = cy0 + int(66*s)
                for ln in self._wrap(draw, c.get("title", ""), tf, cwid-int(36*s))[:1]:
                    draw.text((tx, ty), ln, font=tf, fill=tcol); ty += int(23*s)
                for ln in self._wrap(draw, c.get("description", ""), df, cwid-int(36*s))[:2]:
                    draw.text((tx, ty), ln, font=df, fill=mcol); ty += int(16*s)
            return y + rows*(ch+gap) + int(4*s)

    def _wg_stats(self, canvas, x, y, w, copy, theme, s, surface="dark"):
        stats = (copy.get("stats") or [])[:3]
        if not stats:
            return y
        draw = ImageDraw.Draw(canvas); n = len(stats); cwid = w/n; bh = int(102*s)
        bgc = _mix(theme["bg"][0], (255,255,255), 0.06) if surface == "dark" else (245, 247, 250)
        draw.rounded_rectangle([x, y, x+w, y+bh], radius=int(14*s), fill=bgc)
        vf = self._font("black", int(40*s)); lf = self._font("bold", int(15*s)); lcol = self._muted_on(bgc)
        for i, st in enumerate(stats):
            ccx = x + cwid*(i+0.5)
            vw = draw.textlength(str(st.get("value", "")), font=vf); draw.text((ccx-vw/2, y+int(14*s)), str(st.get("value", "")), font=vf, fill=theme["secondary"])
            lw = draw.textlength(str(st.get("label", "")), font=lf); draw.text((ccx-lw/2, y+int(62*s)), str(st.get("label", "")), font=lf, fill=lcol)
            if i < n-1:
                draw.line([x+cwid*(i+1), y+int(18*s), x+cwid*(i+1), y+bh-int(18*s)], fill=(70, 86, 116), width=1)
        return y + bh + int(16*s)

    def _wg_benefits(self, canvas, x, y, w, copy, theme, color, s, cols=2):
        bens = (copy.get("benefits") or [])[:4]
        if not bens:
            return y
        draw = ImageDraw.Draw(canvas); f = self._font("bold", int(21*s)); colw = w/cols
        for i, b in enumerate(bens):
            bx = x + (i % cols)*colw; by = y + (i//cols)*int(44*s); cr = int(11*s)
            draw.ellipse([bx, by, bx+2*cr, by+2*cr], fill=theme["primary"])
            draw.line([(bx+int(5*s), by+cr), (bx+cr-1, by+cr+int(5*s)), (bx+2*cr-int(4*s), by+int(4*s))], fill=WHITE, width=max(2, int(2.3*s)))
            label = b
            while draw.textlength(label, font=f) > colw-int(40*s) and len(label) > 4:
                label = label[:-2]
            if label != b:
                label = label.rstrip() + "…"
            draw.text((bx+2*cr+int(10*s), by-int(1*s)), label, font=f, fill=color)
        rows = (len(bens)+cols-1)//cols
        return y + rows*int(44*s) + int(12*s)

    def _wg_testimonial(self, canvas, x, y, w, copy, theme, s):
        t = copy.get("testimonial") or {}
        if not t.get("quote"):
            return y
        draw = ImageDraw.Draw(canvas); qh = int(140*s)
        draw.rounded_rectangle([x, y, x+w, y+qh], radius=int(16*s), fill=_mix(theme["bg"][0], (255,255,255), 0.05))
        draw.text((x+int(18*s), y-int(8*s)), "“", font=self._font("black", int(58*s)), fill=theme["secondary"])
        tf = self._font("bold", int(22*s)); yy = y + int(32*s)
        for ln in self._wrap(draw, t["quote"], tf, w-int(80*s))[:3]:
            draw.text((x+int(44*s), yy), ln, font=tf, fill=(235, 242, 250)); yy += int(22*s)+int(6*s)
        who = t.get("author", "") + ((" · " + t.get("role", "")) if t.get("role") else "")
        draw.text((x+int(44*s), y+qh-int(32*s)), who, font=self._font("bold", int(17*s)), fill=theme["primary"])
        return y + qh + int(16*s)

    def _wg_qr(self, canvas, x, y, size, data, s, label="SCAN ME"):
        qr = self._make_qr(data, int(size))
        if qr is None:
            return
        canvas.paste(qr, (int(x), int(y))); draw = ImageDraw.Draw(canvas)
        f = self._font("bold", int(15*s)); lw = draw.textlength(label, font=f)
        draw.rectangle([x, y+size, x+size, y+size+int(22*s)], fill=(18, 28, 48))
        draw.text((x+(size-lw)/2, y+size+int(3*s)), label, font=f, fill=WHITE)

    def _wg_button(self, canvas, x, y, text, theme, s, fill=None, max_w=None):
        draw = ImageDraw.Draw(canvas); fill = fill or theme["secondary"]; fs = int(26*s)
        f = self._font("black", fs)
        if max_w:  # shrink to fit a narrow column
            while draw.textlength(text, font=f) + int(52*s) > max_w and fs > 12:
                fs -= 1; f = self._font("black", fs)
        tw = draw.textlength(text, font=f); padx = int(26*s); pady = int(15*s); bh = fs+2*pady; bw = tw+2*padx
        if max_w:
            bw = min(bw, int(max_w))
        draw.rounded_rectangle([x, y, x+bw, y+bh], radius=int(bh/2), fill=fill)
        draw.text((x+(bw-tw)/2, y+pady), text, font=f, fill=self._text_on(fill))
        return x+bw, y+bh

    def _wg_footer(self, canvas, x, y, w, copy, theme, color, s, url, contact):
        draw = ImageDraw.Draw(canvas); ff = self._font("black", int(23*s)); sf = self._font("reg", int(12*s))
        muted = self._muted_on(theme["bg"][1])
        if url:
            r = int(12*s); draw.ellipse([x, y+int(6*s), x+2*r, y+int(6*s)+2*r], fill=theme["primary"])
            draw.text((x+int(34*s), y), "WEBSITE", font=sf, fill=muted)
            draw.text((x+int(34*s), y+int(15*s)), url, font=ff, fill=color)
        if contact:
            cx = x + w*0.5; draw.ellipse([cx, y+int(6*s), cx+int(24*s), y+int(30*s)], fill=theme["secondary"])
            draw.text((cx+int(34*s), y), "CONTACT", font=sf, fill=muted)
            draw.text((cx+int(34*s), y+int(15*s)), contact, font=self._font("bold", int(18*s)), fill=color)
        if copy.get("tagline"):
            tg = self._font("reg", int(15*s)); tw = draw.textlength(copy["tagline"], font=tg)
            draw.text((x+w-tw, y+int(18*s)), copy["tagline"], font=tg, fill=muted)

    def _cta_card(self, canvas, copy, w, h, margin, cw, s, theme, qr_data):
        draw = ImageDraw.Draw(canvas); cta = copy.get("call_to_action", ""); benefits = (copy.get("benefits") or [])[:4]
        card_h = int(h*0.165); y0 = h - card_h - int(h*0.075); y1 = y0 + card_h
        draw.rounded_rectangle([margin, y0, w-margin, y1], radius=int(22*s), fill=WHITE)
        pad = int(30*s); cf = self._font("black", int(36*s)); cyy = y0+pad
        lines = self._wrap(draw, cta, cf, cw*0.42)[:3]
        for i, ln in enumerate(lines):
            draw.text((margin+pad, cyy), ln, font=cf, fill=theme["secondary"] if i == len(lines)-1 else (18, 28, 48)); cyy += int(36*s)+int(4*s)
        if copy.get("cta_subtext"):
            stf = self._font("reg", int(18*s))
            for ln in self._wrap(draw, copy["cta_subtext"], stf, cw*0.42)[:3]:
                draw.text((margin+pad, cyy), ln, font=stf, fill=(90, 105, 130)); cyy += int(18*s)+int(3*s)
        qr = self._make_qr(qr_data, int(card_h*0.62)); qx = int(w*0.56)
        if qr is not None:
            qy = y0 + (card_h-qr.height)//2; canvas.paste(qr, (qx, qy)); d2 = ImageDraw.Draw(canvas)
            smf = self._font("bold", int(15*s)); lbl = "SCAN ME"; lw2 = d2.textlength(lbl, font=smf)
            d2.rectangle([qx, qy+qr.height, qx+qr.width, qy+qr.height+int(22*s)], fill=(18, 28, 48))
            d2.text((qx+(qr.width-lw2)/2, qy+qr.height+int(3*s)), lbl, font=smf, fill=WHITE)
        if benefits:
            bx = int(w*0.70); bff = self._font("bold", int(18*s))
            avail = (w-margin-int(20*s)) - (bx+int(34*s)); tot = len(benefits)*(int(18*s)+int(13*s)); byy = y0+(card_h-tot)//2+int(6*s)
            for b in benefits:
                cr = int(11*s); draw.ellipse([bx, byy, bx+2*cr, byy+2*cr], fill=theme["primary"])
                draw.line([(bx+int(5*s), byy+cr), (bx+cr-1, byy+cr+int(5*s)), (bx+2*cr-int(4*s), byy+int(4*s))], fill=WHITE, width=max(2, int(2.3*s)))
                lab = b
                while draw.textlength(lab, font=bff) > avail and len(lab) > 4:
                    lab = lab[:-2]
                if lab != b:
                    lab = lab.rstrip()+"…"
                draw.text((bx+2*cr+int(10*s), byy-int(1*s)), lab, font=bff, fill=(18, 28, 48)); byy += int(18*s)+int(13*s)

    def _accent_shapes(self, canvas, theme, rng, n=5):
        d = ImageDraw.Draw(canvas, "RGBA"); w, h = canvas.size
        for _ in range(n):
            col = theme["primary"] if rng.random() > 0.5 else theme["secondary"]
            r = rng.randint(int(w*0.12), int(w*0.32)); cx = rng.randint(0, w); cy = rng.randint(0, int(h*0.6))
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(col[0], col[1], col[2], 28))

    # ── Layout archetypes ────────────────────────────────────────────────────────

    def _layout_hero_top(self, c):
        copy, w, h, theme, s, margin = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["margin"]; cw = w-2*margin
        canvas = self._grad_v(w, h, theme["bg"][0], theme["bg"][1]).convert("RGB"); draw = ImageDraw.Draw(canvas)
        bar_h = int(h*0.06)
        if theme["header"] == "white":
            draw.rectangle([0, 0, w, bar_h], fill=WHITE); draw.rectangle([0, bar_h, w, bar_h+max(3, int(4*s))], fill=theme["secondary"])
            self._brandmark(canvas, draw, margin, (bar_h-int(30*s))//2, c["brand"], (20, 28, 46), 30*s, c["logo"])
        else:
            self._brandmark(canvas, draw, margin, int(bar_h*0.3), c["brand"], WHITE, 28*s, c["logo"])
        hero_top = bar_h + max(3, int(4*s)); hero_h = int(h*0.34)
        self._hero_into(canvas, (0, hero_top, w, hero_h), c["hero"], theme, "bottom"); draw = ImageDraw.Draw(canvas)
        hy = hero_top + hero_h - int(hero_h*0.52)
        hy = self._headline(draw, margin, hy, int(cw*0.92), copy, theme, WHITE, theme["secondary"], s, "left", 1.0, 3)
        self._para(draw, margin, hy, int(cw*0.9), copy.get("subheadline", ""), (225, 233, 245), 24, s, "left", 2)
        y = hero_top + hero_h + int(26*s)
        if copy.get("intro_heading"):
            draw.text((margin, y), copy["intro_heading"], font=self._font("black", int(30*s)), fill=theme["secondary"]); y += int(30*s)+int(8*s)
        y = self._para(draw, margin, y, cw, copy.get("intro_paragraph", ""), (210, 222, 238), 23, s, "left", 3) + int(8*s)
        if copy.get("section_banner"):
            y = self._banner(draw, theme["banner"], w/2, y, copy["section_banner"].upper(), self._font("black", int(30*s)), int(52*s), theme["secondary"]) + int(20*s)
        y = self._wg_features(canvas, margin, y, cw, copy, theme, WHITE, (150, 165, 185), s, theme["feature_mode"])
        for sec in theme["body_sections"][:1]:
            if y > h-int(h*0.3):
                break
            y = (self._wg_stats if sec == "stats" else self._wg_testimonial)(canvas, margin, y, cw, copy, theme, s)
        self._cta_card(canvas, copy, w, h, margin, cw, s, theme, c["qr"])
        self._wg_footer(canvas, margin, h-int(h*0.052), cw, copy, theme, WHITE, s, c["url"], c["contact"])
        return canvas

    def _layout_split(self, c):
        copy, w, h, theme, s, margin, rng = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["margin"], c["rng"]
        canvas = self._grad_v(w, h, theme["bg"][0], theme["bg"][1]).convert("RGB")
        hero_left = rng.random() > 0.5; pw = int(w*0.46)
        hx = 0 if hero_left else w-pw; px = pw if hero_left else 0
        # hero half (full height)
        self._hero_into(canvas, (hx, 0, w-pw, h), c["hero"], theme, "bottom")
        # content panel (solid)
        draw = ImageDraw.Draw(canvas, "RGBA")
        panel = _mix(theme["bg"][0], (0, 0, 0), 0.15)
        draw.rectangle([px, 0, px+pw, h], fill=(panel[0], panel[1], panel[2], 235))
        draw = ImageDraw.Draw(canvas)
        inx = px + int(w*0.04); inw = pw - int(w*0.08)
        y = int(h*0.07)
        self._brandmark(canvas, draw, inx, y, c["brand"], WHITE, 30*s, c["logo"]); y += int(h*0.06)
        y += int(h*0.05)
        y = self._headline(draw, inx, y, inw, copy, theme, WHITE, theme["secondary"], s, "left", 0.92, 4)
        y += int(8*s)
        y = self._para(draw, inx, y, inw, copy.get("subheadline", ""), (210, 222, 240), 23, s, "left", 2) + int(14*s)
        y = self._wg_benefits(canvas, inx, y, inw, copy, theme, (235, 242, 250), s, cols=1) + int(16*s)
        # CTA button + QR lower in panel
        _, by = self._wg_button(canvas, inx, y, copy.get("call_to_action", "Learn More"), theme, s, max_w=inw)
        qy = h - int(h*0.24)
        self._wg_qr(canvas, inx, qy, int(w*0.16), c["qr"], s)
        if c["url"]:
            draw.text((inx, h-int(h*0.075)), c["url"], font=self._font("black", int(20*s)), fill=WHITE)
        if c["contact"]:
            draw.text((inx, h-int(h*0.048)), c["contact"], font=self._font("reg", int(15*s)), fill=(205, 216, 232))
        return canvas

    def _layout_fullbleed(self, c):
        copy, w, h, theme, s, margin, rng = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["margin"], c["rng"]
        canvas = self._cover(c["hero"], w, h).convert("RGB")
        ov = Image.new("RGBA", (w, h), (theme["bg"][1][0], theme["bg"][1][1], theme["bg"][1][2], 150))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        # brand top
        self._brandmark(canvas, draw, margin, int(h*0.05), c["brand"], WHITE, 30*s, c["logo"])
        # floating glass card
        pos = rng.choice(["center", "bottom", "top"]); cardw = int(w*0.86); cardx = (w-cardw)//2
        cardh = int(h*0.5)
        cardy = {"top": int(h*0.14), "center": (h-cardh)//2, "bottom": h-cardh-int(h*0.06)}[pos]
        gl = Image.new("RGBA", (cardw, cardh), (10, 16, 32, 210));
        glass = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(glass).rounded_rectangle([cardx, cardy, cardx+cardw, cardy+cardh], radius=int(26*s), fill=(10, 16, 32, 205))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), glass).convert("RGB"); draw = ImageDraw.Draw(canvas)
        ix = cardx + int(40*s); iw = cardw - int(80*s); y = cardy + int(34*s)
        y = self._headline(draw, ix, y, iw, copy, theme, WHITE, theme["secondary"], s, "left", 0.9, 3) + int(6*s)
        y = self._para(draw, ix, y, iw, copy.get("subheadline", ""), (215, 226, 242), 22, s, "left", 2) + int(14*s)
        y = self._wg_features(canvas, ix, y, iw, copy, theme, WHITE, (160, 174, 196), s, "row", max_items=4)
        # CTA + QR inside card bottom
        _, _ = self._wg_button(canvas, ix, cardy+cardh-int(120*s), copy.get("call_to_action", "Learn More"), theme, s)
        self._wg_qr(canvas, cardx+cardw-int(160*s), cardy+cardh-int(150*s), int(w*0.12), c["qr"], s)
        self._wg_footer(canvas, margin, h-int(h*0.05), w-2*margin, copy, theme, WHITE, s, c["url"], c["contact"])
        return canvas

    def _layout_poster(self, c):
        copy, w, h, theme, s, margin, rng = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["margin"], c["rng"]
        canvas = self._grad_v(w, h, theme["bg"][0], theme["bg"][1]).convert("RGB")
        self._accent_shapes(canvas, theme, rng, n=6); draw = ImageDraw.Draw(canvas)
        align = rng.choice(["left", "center"]); cw = w-2*margin
        y = int(h*0.06)
        self._brandmark(canvas, draw, margin, y, c["brand"], WHITE, 28*s, c["logo"]); y += int(h*0.07)
        y = self._headline(draw, margin, y, cw, copy, theme, WHITE, theme["secondary"], s, align, 1.25, 3) + int(8*s)
        y = self._para(draw, margin, y, cw, copy.get("subheadline", ""), (220, 230, 246), 26, s, align, 2) + int(20*s)
        if copy.get("section_banner"):
            y = self._banner(draw, theme["banner"], w/2, y, copy["section_banner"].upper(), self._font("black", int(30*s)), int(52*s), theme["secondary"]) + int(22*s)
        y = self._wg_features(canvas, margin, y, cw, copy, theme, WHITE, (150, 165, 185), s, "grid") + int(8*s)
        if copy.get("stats") and y < h-int(h*0.34):
            y = self._wg_stats(canvas, margin, y, cw, copy, theme, s) + int(6*s)
        # CTA banner bottom with QR + benefits
        band_h = int(h*0.16); by0 = h-band_h; draw.rectangle([0, by0, w, h], fill=theme["primary"])
        cf = self._font("black", int(38*s)); cyy = by0+int(26*s)
        for i, ln in enumerate(self._wrap(draw, copy.get("call_to_action", ""), cf, cw*0.55)[:2]):
            draw.text((margin, cyy), ln, font=cf, fill=WHITE); cyy += int(38*s)+int(4*s)
        if copy.get("cta_subtext"):
            draw.text((margin, cyy), copy["cta_subtext"][:64], font=self._font("reg", int(18*s)), fill=(235, 240, 250))
        qr_left = rng.random() > 0.5
        qsz = int(band_h*0.62); qx = (w-margin-qsz) if not qr_left else int(w*0.62)
        self._wg_qr(canvas, qx, by0+(band_h-qsz)//2-int(8*s), qsz, c["qr"], s)
        return canvas

    def _layout_sidebar(self, c):
        copy, w, h, theme, s, rng = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["rng"]
        left = rng.random() > 0.4; sw = int(w*0.30)
        sx = 0 if left else w-sw; mx0 = sw if left else 0
        canvas = self._grad_v(w, h, theme["bg"][0], theme["bg"][1]).convert("RGB"); draw = ImageDraw.Draw(canvas)
        # main: hero top + content
        mw = w-sw; mmargin = int(mw*0.07)
        self._hero_into(canvas, (mx0, 0, mw, int(h*0.40)), c["hero"], theme, "bottom"); draw = ImageDraw.Draw(canvas)
        hy = int(h*0.40) - int(h*0.20)
        self._headline(draw, mx0+mmargin, hy, mw-2*mmargin, copy, theme, WHITE, theme["secondary"], s, "left", 0.95, 3)
        y = int(h*0.44)
        if copy.get("intro_heading"):
            draw.text((mx0+mmargin, y), copy["intro_heading"], font=self._font("black", int(28*s)), fill=theme["secondary"]); y += int(28*s)+int(8*s)
        y = self._para(draw, mx0+mmargin, y, mw-2*mmargin, copy.get("intro_paragraph", ""), (210, 222, 238), 22, s, "left", 4) + int(14*s)
        y = self._wg_features(canvas, mx0+mmargin, y, mw-2*mmargin, copy, theme, WHITE, (150, 165, 185), s, "grid", max_items=4) + int(8*s)
        if copy.get("stats") and y < h-int(h*0.2):
            self._wg_stats(canvas, mx0+mmargin, y, mw-2*mmargin, copy, theme, s)
        # sidebar
        pcol = theme["primary"]; draw.rectangle([sx, 0, sx+sw, h], fill=pcol)
        ix = sx + int(sw*0.12); iw = sw - int(sw*0.24); tcol = self._text_on(pcol); mut = self._muted_on(pcol)
        sy = int(h*0.06)
        self._brandmark(canvas, draw, ix, sy, c["brand"], tcol, 24*s, c["logo"]); sy += int(h*0.07)
        sy = self._para(draw, ix, sy, iw, copy.get("tagline", ""), tcol, 18, s, "left", 2) + int(20*s)
        sy = self._wg_benefits(canvas, ix, sy, iw, copy, theme, tcol, s, cols=1) + int(20*s)
        self._wg_button(canvas, ix, sy, copy.get("call_to_action", "Learn More"), theme, s, fill=theme["secondary"], max_w=iw)
        self._wg_qr(canvas, ix, h-int(h*0.26), int(sw*0.6), c["qr"], s)
        cf = self._font("bold", int(16*s))
        if c["url"]:
            draw.text((ix, h-int(h*0.09)), c["url"], font=cf, fill=tcol)
        if c["contact"]:
            draw.text((ix, h-int(h*0.06)), c["contact"], font=self._font("reg", int(13*s)), fill=mut)
        return canvas

    def _layout_editorial(self, c):
        copy, w, h, theme, s, margin = c["copy"], c["w"], c["h"], c["theme"], c["s"], c["margin"]; cw = w-2*margin
        canvas = self._grad_v(w, h, theme["bg"][0], theme["bg"][1]).convert("RGB"); draw = ImageDraw.Draw(canvas)
        y = int(h*0.06)
        self._brandmark(canvas, draw, margin, y, c["brand"], WHITE, 26*s, c["logo"]); y += int(h*0.055)
        # large headline top-left
        y = self._headline(draw, margin, y, cw, copy, theme, WHITE, theme["secondary"], s, "left", 1.15, 3) + int(10*s)
        draw.rectangle([margin, y, margin+int(140*s), y+max(4, int(6*s))], fill=theme["secondary"]); y += int(22*s)
        # hero band (wide, short)
        hh = int(h*0.26); self._hero_into(canvas, (margin, y, cw, hh), c["hero"], theme, "bottom"); draw = ImageDraw.Draw(canvas)
        y += hh + int(20*s)
        # intro paragraph
        y = self._para(draw, margin, y, cw, copy.get("intro_paragraph", ""), (212, 224, 240), 23, s, "left", 3) + int(16*s)
        # features as a plain horizontal icon strip (no cards)
        cards = (copy.get("feature_cards") or [])[:4]
        if cards:
            n = len(cards); cwid = cw/n; tf = self._font("bold", int(18*s))
            for i, cc in enumerate(cards):
                ccx = margin + cwid*(i+0.5)
                self._icon(canvas, cc.get("icon", "star"), int(ccx), int(y+int(26*s)), int(24*s), theme["primary"] if i % 2 == 0 else theme["secondary"], theme["icon"])
                for j, ln in enumerate(self._wrap(draw, cc.get("title", ""), tf, cwid-int(10*s))[:2]):
                    lw = draw.textlength(ln, font=tf); draw.text((ccx-lw/2, y+int(58*s)+j*int(20*s)), ln, font=tf, fill=WHITE)
            y += int(110*s)
        # thin rule + stats inline
        if copy.get("stats"):
            y = self._wg_stats(canvas, margin, y, cw, copy, theme, s) + int(6*s)
        # CTA text bottom-left + button, QR small bottom-right
        cyy = h - int(h*0.16)
        cf = self._font("black", int(34*s))
        for i, ln in enumerate(self._wrap(draw, copy.get("call_to_action", ""), cf, cw*0.6)[:2]):
            draw.text((margin, cyy), ln, font=cf, fill=WHITE if i == 0 else theme["secondary"]); cyy += int(34*s)+int(4*s)
        self._wg_button(canvas, margin, cyy+int(6*s), "Get Started", theme, s)
        self._wg_qr(canvas, w-margin-int(w*0.13), h-int(h*0.17), int(w*0.13), c["qr"], s)
        self._wg_footer(canvas, margin, h-int(h*0.045), cw, copy, theme, WHITE, s, c["url"], c["contact"])
        return canvas

    # ── AI Creative mode (LLM-authored HTML rendered via headless Chrome) ───────

    @staticmethod
    def _find_chrome():
        import shutil as _sh
        exe = _sh.which("chrome") or _sh.which("chromium") or _sh.which("msedge")
        if exe:
            return exe
        for p in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]:
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def _img_data_uri(pil_img, fmt="PNG"):
        if pil_img is None:
            return ""
        buf = BytesIO()
        pil_img.convert("RGB").save(buf, fmt)
        import base64
        return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()

    def _render_html(self, html: str, w: int, h: int, scale: int = 2):
        """Render an HTML string to a PIL image via headless Chrome at w×h (×scale)."""
        chrome = self._find_chrome()
        if not chrome:
            return None
        import subprocess, tempfile, uuid as _uuid
        d = tempfile.mkdtemp(prefix="flyer_")
        html_path = os.path.join(d, "flyer.html")
        out_path = os.path.join(d, "flyer.png")
        prof = os.path.join(d, "prof_" + _uuid.uuid4().hex[:6])
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            f"--force-device-scale-factor={scale}",
            "--run-all-compositor-stages-before-draw", "--virtual-time-budget=6000",
            "--default-background-color=00000000",
            f"--user-data-dir={prof}",
            f"--screenshot={out_path}", f"--window-size={w},{h}",
            "file:///" + html_path.replace("\\", "/"),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
                img = Image.open(out_path).convert("RGB")
                return img
            print("    ⚠️  Chrome produced no/empty screenshot")
        except Exception as e:
            print(f"    ⚠️  Chrome render failed: {e}")
        finally:
            try:
                import shutil as _sh2; _sh2.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        return None

    # Variety pools — produce agency-grade, reference-quality flyers
    _LAYOUT_DIRECTIONS = [
        ("VERSION A — PARTNERSHIP + HERO TOP (like AI365Prep reference): slim white PARTNERSHIP BAR at very top "
         "with both logos; below: FULL-BLEED HERO photo (top 38% canvas) with 110px+ two-tone left-aligned headline "
         "over dark gradient overlay; accent-color section banner pill; ONE horizontal row of 5 icon cards with "
         "proper inline SVG icons (NO letter-circles); white CTA card at bottom: big headline + QR + SCAN ME + "
         "bullet checklist; dark footer bar with website + phone + brand name."),
        ("VERSION B — SPLIT SCREEN: left 48% dark navy gradient: brand logo top-left, massive 110px headline, "
         "sub-headline, benefits checklist, pill CTA button, QR small bottom; right 52% hero photo full height "
         "with accent-color strip on seam; dark footer spanning full width."),
        ("VERSION C — CORPORATE BROCHURE: white/light background; slim colored top bar with brand+partner logos; "
         "hero photo in rounded card top-right (45% wide, 35% height); large dark headline left; "
         "3-column feature grid with SVG icon circles; horizontal stats bar 3 large numbers; "
         "full-width accent CTA banner with QR; minimal footer."),
        ("VERSION D — DARK PREMIUM POSTER: deep dark gradient; HUGE 130px centered headline last word accent color; "
         "hero photo full-width band 30% height with dark overlay; 4 glassmorphism feature cards; "
         "stats strip; accent CTA button centered; QR beside CTA; minimal footer."),
        ("VERSION E — MODERN SAAS: navy-to-indigo gradient; hero image right side 50% wide clipped; "
         "left: bold 100px headline, accent sub-headline, 2-col feature grid, big rounded CTA pill; "
         "stats row large numbers; QR in footer beside contact. Radial glow behind hero."),
        ("VERSION F — EDITORIAL MAGAZINE: 120px left-aligned headline top 30%; thin accent divider; "
         "hero photo full-width band 25% height; intro paragraph; feature list 2-col icon+title+desc; "
         "pull-quote testimonial card large quotation mark; white CTA card with pill button + QR; dark footer."),
        ("VERSION G — EVENT POSTER: bold angled color block top-left; hero photo right half overlapping it; "
         "enormous 120px centered headline; accent pill banner; 4 feature cards row; "
         "full-width contrasting CTA banner; large QR; footer with all contact details."),
        ("VERSION H — INFOGRAPHIC: dark bg; top brand bar; headline left + hero right; "
         "numbered icon features 01 02 03 in accent color; stats band; testimonial; "
         "bottom CTA card split: headline+button left, QR center, benefits checklist right."),
    ]
    _FONT_PAIRS = [
        "Poppins:wght@400;600;700;900",
        "Montserrat:wght@400;700;900",
        "Sora:wght@400;700;900",
        "Plus+Jakarta+Sans:wght@400;600;700;800",
        "Outfit:wght@400;600;700;900",
        "Manrope:wght@400;600;700;800",
    ]
    _COMPOSITIONS = [
        "strong vertical Z-reading: top-bar → hero → banner → cards → CTA → footer",
        "F-pattern: top-left logo, right-side hero photo, left-side content blocks",
        "layered depth: hero photo behind text, cards floating over with shadows",
        "modular grid: strict columns and rows, clean alignment, generous gutters",
        "center-stage: massive centered headline, everything organized below",
    ]
    _COLOR_TREATMENTS = [
        "deep navy #0a1628 to dark blue #0f2044 gradient — accent = orange or cyan",
        "brand-primary gradient top to bottom — white text — accent highlights key words",
        "dark background ONE vivid accent for: banner icons headline-word CTA button",
        "rich dark navy + white sections for CTA/footer contrast — accent highlights",
        "charcoal #1a1a2e to navy gradient — neon accent brand secondary",
    ]
    _ACCENT_STYLES = [
        "solid rounded cards border-radius:12px box-shadow:0 4px 24px rgba(0,0,0,0.35)",
        "frosted glass: background:rgba(255,255,255,0.07) backdrop-filter:blur(12px) border:1px solid rgba(255,255,255,0.15)",
        "white cards on dark background — crisp contrast — for CTA and stats sections",
        "thin 2px accent-color border on card top edge; rest transparent/dark",
        "no cards — generous padding and background color bands as section separators",
    ]
    _SHAPES = [
        "subtle radial gradient glow accent color 18% opacity behind hero photo",
        "faint connected-dots SVG pattern overlay on dark background opacity 0.06",
        "two large blurred ellipses in accent colors in background opacity 0.12",
        "no extra background graphics — hero photo and typography carry the design",
        "thin accent-color horizontal rules between sections",
    ]

    def _design_brief(self, rng):
        return ("- Layout direction: " + rng.choice(self._LAYOUT_DIRECTIONS) +
                "\n- Typography: pair " + rng.choice(self._FONT_PAIRS) +
                "\n- Composition: " + rng.choice(self._COMPOSITIONS) +
                "\n- Color treatment: " + rng.choice(self._COLOR_TREATMENTS) +
                "\n- Card / accent style: " + rng.choice(self._ACCENT_STYLES) +
                "\n- Background graphics: " + rng.choice(self._SHAPES) +
                "\n- Make THIS flyer clearly different from a standard vertical template.")

    def generate_html(self, content, copy, w, h, brand_name, display_url, contact_info,
                      primary_hex, secondary_hex, style, has_qr, has_logo,
                      partner_name="", has_partner=False, rng=None):
        """Ask the LLM to author a complete, unique HTML flyer driven by a random design brief."""
        rng = rng or random.Random()
        tmpl_path = os.path.join(self.prompts_dir, "flyer_html.txt")
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        copy_json = json.dumps({k: copy.get(k) for k in (
            "headline", "subheadline", "intro_heading", "intro_paragraph", "section_banner",
            "feature_cards", "benefits", "stats", "testimonial", "call_to_action",
            "cta_subtext", "tagline")}, ensure_ascii=False)[:2500]
        seed = uuid.uuid4().hex[:8]
        partner_h = 60
        hero_h    = int(h * 0.46)
        footer_h  = 68
        cta_h     = 200
        repl = {
            "{W}": str(w), "{H}": str(h),
            "{HERO_H}": str(hero_h),
            "{PARTNER_H_VAL}": str(partner_h),
            "{brand}": brand_name or "",
            "{url}": display_url or "", "{contact}": contact_info or "",
            "{primary}": primary_hex, "{secondary}": secondary_hex, "{style}": style or "modern",
            "{content}": (content or "")[:35000], "{copy_json}": copy_json,
            "{design_brief}": self._design_brief(rng), "{seed}": seed,
            "{partner_note}": (f"- Partner: {partner_name} — show a tasteful 'PROUD PARTNERSHIP' bar/lockup pairing both brands."
                               if (partner_name or has_partner) else ""),
            "{qr_note}": ("A QR code IS provided — include it." if has_qr else "No QR — omit it."),
            "{logo_note}": ("a logo IS available — use <img src=\"{{BRAND_LOGO}}\"> for it."
                            if has_logo else "no logo image — render the brand name as bold styled text (do not use {{BRAND_LOGO}})."),
            "{partner_logo_note}": ("a partner logo IS available — use <img src=\"{{PARTNER_LOGO}}\"> in the partnership lockup."
                                    if has_partner else "no partner logo — if a partner name exists, render it as styled text (do not use {{PARTNER_LOGO}})."),
        }
        prompt = tmpl
        for k, v in repl.items():
            prompt = prompt.replace(k, v)

        resp = self.openai.chat.completions.create(
            model=self.model, max_tokens=4600, temperature=1.0, timeout=140,
            messages=[{"role": "user", "content": prompt}],
        )
        html = resp.choices[0].message.content.strip()
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```$", "", html).strip()
        m = re.search(r"<!DOCTYPE html[\s\S]*</html>", html, re.IGNORECASE)
        if m:
            html = m.group(0)
        return html

    def render_creative(self, content, copy, w, h, brand_name, display_url, contact_info,
                        primary_hex, secondary_hex, style, qr_data, hero_img, brand_logo,
                        partner_name="", partner_logo=None, rng=None):
        """Full AI-creative pipeline: random brief → LLM HTML → embed images → Chrome render."""
        qr_img = self._make_qr(qr_data, 600) if qr_data else None
        html = self.generate_html(
            content, copy, w, h, brand_name, display_url, contact_info,
            primary_hex, secondary_hex, style, has_qr=bool(qr_img), has_logo=bool(brand_logo),
            partner_name=partner_name, has_partner=bool(partner_logo) or bool(partner_name), rng=rng,
        )
        html = html.replace("{{HERO_IMAGE}}", self._img_data_uri(hero_img))
        html = html.replace("{{QR_IMAGE}}", self._img_data_uri(qr_img))
        html = html.replace("{{BRAND_LOGO}}", self._img_data_uri(brand_logo) if brand_logo else "")
        html = html.replace("{{PARTNER_LOGO}}", self._img_data_uri(partner_logo) if partner_logo else "")
        img = self._render_html(html, w, h, scale=2)
        return img, html

    def edit_html(self, current_html: str, instruction: str, w: int, h: int) -> tuple:
        """
        Apply a targeted edit to an existing flyer HTML via GPT-4o (ChatGPT-style).
        Returns (PIL image | None, updated_html).
        """
        tmpl_path = os.path.join(self.prompts_dir, "flyer_edit.txt")
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        prompt = (tmpl.replace("{instruction}", instruction.strip())
                      .replace("{html}", current_html[:18000])   # stay under context limit
                      .replace("{W}", str(w))
                      .replace("{H}", str(h)))
        resp = self.openai.chat.completions.create(
            model=self.model, max_tokens=4600, temperature=0.3, timeout=140,
            messages=[{"role": "user", "content": prompt}],
        )
        html = resp.choices[0].message.content.strip()
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```$", "", html).strip()
        m = re.search(r"<!DOCTYPE html[\s\S]*</html>", html, re.IGNORECASE)
        if m:
            html = m.group(0)
        img = self._render_html(html, w, h, scale=2)
        return img, html

    @staticmethod
    def logo_from_bytes(raw: bytes, max_h: int) -> "Image.Image | None":
        """Convert raw logo bytes (e.g. from an upload) into a sized PIL RGBA image."""
        try:
            from io import BytesIO as _B
            img = Image.open(_B(raw)).convert("RGBA")
            ratio = max_h / img.height
            return img.resize((max(1, int(img.width * ratio)), max_h), Image.LANCZOS)
        except Exception as e:
            print(f"    ⚠️  Logo parse failed: {e}")
            return None

    # ── Export ──────────────────────────────────────────────────────────────────

    def export(self, img, base, formats):
        files = {}; fmts = [f.lower() for f in (formats or ["png"])]
        if "png" in fmts:
            p = os.path.join(self.output_dir, f"{base}.png"); img.save(p, "PNG"); files["png"] = p
        if "jpg" in fmts or "jpeg" in fmts:
            p = os.path.join(self.output_dir, f"{base}.jpg"); img.convert("RGB").save(p, "JPEG", quality=92); files["jpg"] = p
        if "pdf" in fmts:
            p = os.path.join(self.output_dir, f"{base}.pdf"); img.convert("RGB").save(p, "PDF", resolution=150.0); files["pdf"] = p
        return files

    # ── Orchestration ─────────────────────────────────────────────────────────

    def run(self, content="", topic="", style="auto", website_url="", custom_content="",
            ratio="a4_portrait", custom_width=None, custom_height=None, formats=None,
            brand_name="", contact_info="", display_url="", accent_color="",
            secondary_color="", partner_name="", brand_logo_url="", partner_logo_url="",
            brand_logo_bytes: bytes = None, partner_logo_bytes: bytes = None,
            run_research=True, **kwargs):
        formats = formats or ["png", "pdf"]
        # Content-first: prefer `content`; fall back to legacy topic/custom_content
        content = (content or "").strip() or (topic or "").strip()
        if custom_content:
            content = (content + "\n\n" + custom_content).strip()
        if not content:
            content = topic or "Marketing Flyer"
        title = (content.splitlines()[0] if content.splitlines() else content)[:80]

        if ratio == "custom" and custom_width and custom_height:
            w = max(320, min(int(custom_width), 4096)); h = max(320, min(int(custom_height), 4096))
        else:
            w, h = FLYER_SIZES.get(ratio, FLYER_SIZES["a4_portrait"])

        print(f"\n{'='*60}\n🪧  FLYER CREATOR (dynamic)\n{'='*60}\n📐 {ratio} {w}x{h} | 🎨 style={style}")

        # Website brand context + assets
        website_context = None; brand_colors = []
        parts = []
        if website_url and run_research:
            try:
                website_context = self.web_research_agent.analyze(website_url)
                if website_context.get("summary"):
                    wc = website_context
                    parts.append(f"BRAND CONTEXT:\n  Brand: {wc.get('brand_name','')}\n  Summary: {wc.get('summary','')}\n"
                                 f"  Products/Services: {', '.join(wc.get('products_services', [])[:5])}\n  Tone: {wc.get('tone_of_voice','')}")
                    if not brand_name:
                        brand_name = wc.get("brand_name", "") or brand_name
            except Exception as e:
                print(f"  ⚠️  Website research failed: {e}")
            try:
                assets = self._extract_brand_assets(website_url)
                brand_colors = assets.get("colors", [])
                if not brand_logo_url and assets.get("logo_url"):
                    brand_logo_url = assets["logo_url"]
                if brand_colors:
                    print(f"  🎨 Brand colors extracted: {brand_colors}")
            except Exception as e:
                print(f"  ⚠️  Brand assets failed: {e}")
        context_block = "\n\n".join(parts)

        print("✍️  Generating copy from content...")
        copy = self.generate_copy(content, context_block)

        rng = random.Random()  # unseeded → designs vary every run
        theme = self._build_theme(style, copy, accent_color, secondary_color, brand_colors, rng)
        print(f"  🎨 Theme: {theme['style']} | layout={theme['layout']} | features={theme['feature_mode']} | body={theme['body_sections']}")

        print("🎨 Generating marketing-poster hero scene...")
        hero = self._generate_hero(copy.get("background_prompt", title), w, int(h*0.46),
                                   primary=theme["primary"], secondary=theme["secondary"])

        # Logo: uploaded bytes take priority over URL
        if brand_logo_bytes:
            brand_logo = self.logo_from_bytes(brand_logo_bytes, int(h*0.05))
            if brand_logo and not brand_colors:
                try:
                    brand_colors = self._palette_from_image(brand_logo)
                    print(f"  🎨 Brand colors from logo: {brand_colors}")
                except Exception:
                    pass
        elif brand_logo_url:
            brand_logo = self._fetch_logo(brand_logo_url, int(h*0.05))
        else:
            brand_logo = None

        partner_logo = (self.logo_from_bytes(partner_logo_bytes, int(h*0.045))
                        if partner_logo_bytes else
                        self._fetch_logo(partner_logo_url, int(h*0.045)) if partner_logo_url else None)

        qr_data = display_url or website_url or ""
        engine = "pil"
        saved_html = ""

        # ── AI Creative mode: let the LLM author a unique HTML design, rendered
        #    via headless Chrome. Falls back to the PIL layout engine on any issue.
        creative = kwargs.get("creative", True)
        if creative and self._find_chrome():
            print("🎨 AI Creative mode — generating unique HTML design...")
            try:
                primary_hex = "#%02X%02X%02X" % theme["primary"]
                secondary_hex = "#%02X%02X%02X" % theme["secondary"]
                img, html = self.render_creative(
                    content=content, copy=copy, w=w, h=h, brand_name=brand_name,
                    display_url=display_url or website_url, contact_info=contact_info,
                    primary_hex=primary_hex, secondary_hex=secondary_hex,
                    style=(style if style != "auto" else theme["style"]),
                    qr_data=qr_data, hero_img=hero, brand_logo=brand_logo,
                    partner_name=partner_name, partner_logo=partner_logo, rng=rng,
                )
                if img is not None:
                    flyer = img; engine = "ai_html"; saved_html = html
                    print(f"  ✅ AI flyer rendered ({img.size[0]}×{img.size[1]})")
                else:
                    raise RuntimeError("render returned no image")
            except Exception as e:
                print(f"  ⚠️  Creative mode failed ({e}) — falling back to layout engine")
                flyer = self.compose(copy, hero, w, h, brand_name, partner_name, display_url or website_url,
                                     contact_info, theme, qr_data, brand_logo, partner_logo, rng)
        else:
            print("🖼️  Composing flyer (layout engine)...")
            flyer = self.compose(copy, hero, w, h, brand_name, partner_name, display_url or website_url,
                                 contact_info, theme, qr_data, brand_logo, partner_logo, rng)

        base = f"flyer_{engine}_{ratio.replace(':','x')}_{uuid.uuid4().hex[:8]}"
        files = self.export(flyer, base, formats)
        file_urls = {k: f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/output/{os.path.basename(v)}" for k, v in files.items()}
        print(f"✅ Flyer exported: {list(file_urls.keys())}\n{'='*60}\n")

        return {
            "topic": title, "content": content, "ratio": ratio,
            "size_label": FLYER_SIZE_LABELS.get(ratio, ratio), "dimensions": {"width": w, "height": h},
            "style": theme["style"], "copy": copy, "brand_name": brand_name, "partner_name": partner_name,
            "display_url": display_url or website_url, "contact_info": contact_info,
            "accent_color": "#%02X%02X%02X" % theme["primary"], "secondary_color": "#%02X%02X%02X" % theme["secondary"],
            "website_context": website_context, "brand_colors": ["#%02X%02X%02X" % c for c in brand_colors],
            "files": file_urls, "preview_url": file_urls.get("png") or next(iter(file_urls.values()), None),
            "has_qr": bool(qr_data), "engine": engine, "html": saved_html,
            "dimensions_wh": [w, h],
        }
