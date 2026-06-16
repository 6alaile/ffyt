"""
scripts/generate_html.py (Fixed for HyperFrames Studio)
─────────────────────────────────────────────────────────────
Fixes:
- Removed window.__timelines manual registration.
- Replaced gsap.set() with CSS initial states for better Studio compatibility.
- Streamlined timeline creation to allow HyperFrames auto-detection.
"""

import argparse
import json
import sys
from pathlib import Path

# ─────────────────────────────────────────────
# DIMENSIONS
# ─────────────────────────────────────────────
FORMATS = {
    "landscape": {"width": 1920, "height": 1080, "font_scale": 1.0},
    "portrait":  {"width": 1080, "height": 1920, "font_scale": 0.65},
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def scale_font(size_px: int, scale: float) -> int:
    return int(size_px * scale)

def clip_src(scene_id: str) -> str:
    return f"assets/clips/{scene_id}_processed.mp4"

def top_bar(section_label: str) -> str:
    return f"""
        <div class="top-bar">
          <span><span class="mark">●</span>&nbsp;&nbsp;{section_label}</span>
        </div>"""

def bottom_bar(left: str, right: str = "", pill: bool = False) -> str:
    right_html = f'<span class="pill">{right}</span>' if (pill and right) else f"<span>{right}</span>"
    return f"""
        <div class="bottom-bar">
          <span>{left}</span>
          {right_html}
        </div>"""

# ─────────────────────────────────────────────
# TEMPLATE RENDERERS
# ─────────────────────────────────────────────

def tpl_impact_statement(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        {top_bar(d.get('section_label', scene.get('section_label', '')))}
        <div class="scene-content" style="align-items:center;text-align:center;">
          <div class="eyebrow" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
          <h1 class="display headline" id="s{idx}-headline">
            {d.get('line1', '')}<br />
            {d.get('line2', '')} <span class="accent">{d.get('line2_accent', '')}</span>
          </h1>
          <div class="gold-rule" id="s{idx}-rule" style="left:50%;top:50%;transform:translate(-50%,-50%);height:4px;"></div>
          <div class="subhead" id="s{idx}-subhead">{d.get('subhead', '')}</div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right_pill', ''), pill=True)}
      </div>"""

def tpl_stat_split(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    stats_html = "".join([f'<div class="stat" id="s{idx}-stat{i+1}"><span class="num display">{s["value"]}</span><span class="label mono">{s["label"]}</span></div>' for i, s in enumerate(d.get("stats", []))])
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content split-layout">
          <div class="left">
            <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
            <h2 class="display headline" id="s{idx}-headline">{d.get('headline', '')} <span class="accent">{d.get('headline_accent', '')}</span></h2>
            <p class="body-text" id="s{idx}-sub">{d.get('body', '')}</p>
          </div>
          <div class="right stats-col">{stats_html}</div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right', ''))}
      </div>"""

def tpl_title_card(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    names_html = "".join([f'<div class="display name">{n["name"]}<span class="year mono">{n.get("detail","")}</span></div><div class="vs mono">VS</div>' for n in d.get("names", [])])
    if names_html.endswith('<div class="vs mono">VS</div>'): names_html = names_html[:-len('<div class="vs mono">VS</div>')]
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        <div class="scene-glow" id="s{idx}-glow" style="left:-400px;top:-200px;"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="align-items:center;text-align:center;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
          <h2 class="display headline" id="s{idx}-headline">{d.get('headline', '')} <span class="accent">{d.get('headline_accent', '')}</span></h2>
          <div class="gold-rule" id="s{idx}-rule" style="left:50%;transform:translateX(-50%);height:2px;top:50%;"></div>
          <p class="body-italic" id="s{idx}-sub">{d.get('body', '')}</p>
          <div class="names" id="s{idx}-names">{names_html}</div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right', ''))}
      </div>"""

def tpl_stat_focus(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content split-layout" style="align-items:center;">
          <div class="counter-wrap" id="s{idx}-counter">
            <div class="counter-label mono">{d.get('stat_label', '')}</div>
            <div class="display counter" id="s{idx}-counter-num">{d.get('stat_value', '')}</div>
            <div class="counter-suffix mono">{d.get('stat_context', '')}</div>
          </div>
          <div class="right">
            <div class="age mono" id="s{idx}-age">{d.get('tag', '')}</div>
            <h2 class="display name" id="s{idx}-name">{d.get('name', '')}</h2>
            <p class="quote" id="s{idx}-quote">{d.get('quote', '')}</p>
          </div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right_pill', ''), pill=True)}
      </div>"""

def tpl_three_column(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    cards_html = "".join([f'<div class="host-card" id="s{idx}-card{i+1}"><div class="flag">{c.get("flag","")}</div><div class="display host-name">{c.get("name","")}</div><div class="host-stats">{"".join([f\'<div class="host-stat"><span class="v">{s["value"]}</span> · {s["label"]}</div>\' for s in c.get("stats", [])])}</div><div class="host-quote">"{c.get("quote","")}"</div></div>' for i, c in enumerate(d.get("cards", []))])
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="padding:0 120px;align-items:stretch;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow','')}</div>
          <h2 class="display headline" id="s{idx}-headline">{d.get('headline','')}</h2>
          <div class="host-grid">{cards_html}</div>
        </div>
        {bottom_bar(d.get('footer_left',''), d.get('footer_right',''))}
      </div>"""

def tpl_tag_list(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    tags_html = "".join([f'<div class="nation"><span class="new">{t.get("prefix","DEBUT")}</span> {t["name"]}</div>' for t in d.get("tags", [])])
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        <div class="scene-glow" id="s{idx}-glow" style="right:-400px;top:-200px;"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="align-items:center;text-align:center;padding:0 120px;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow','')}</div>
          <h2 class="display headline" id="s{idx}-headline">{d.get('headline','')} <span class="accent">{d.get('headline_accent','')}</span></h2>
          <p class="body-text" id="s{idx}-sub">{d.get('body','')}</p>
          <div class="nations" id="s{idx}-nations">{tags_html}</div>
        </div>
        {bottom_bar(d.get('footer_left',''), d.get('footer_right',''))}
      </div>"""

def tpl_cta(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    return f"""
      <div id="{sid}" class="scene clip" data-duration="{scene['duration']}">
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="align-items:center;text-align:center;">
          <div class="badge mono" id="s{idx}-badge">{d.get('badge','// THE CHANNEL')}</div>
          <h2 class="display headline" id="s{idx}-headline">{d.get('headline','SUBSCRIBE.')}</h2>
          <p class="body-text" id="s{idx}-sub">{d.get('body','')}</p>
          <div class="subscribe-btn" id="s{idx}-btn">▶&nbsp;&nbsp;SUBSCRIBE</div>
          <div class="sub-bottom mono" id="s{idx}-subbottom">{d.get('sub_bottom','')}</div>
        </div>
        {bottom_bar(d.get('footer_left',''), d.get('footer_right',''))}
      </div>"""

TEMPLATE_MAP = {
    "impact_statement": tpl_impact_statement,
    "stat_split":       tpl_stat_split,
    "title_card":       tpl_title_card,
    "stat_focus":       tpl_stat_focus,
    "three_column":     tpl_three_column,
    "tag_list":         tpl_tag_list,
    "cta":              tpl_cta,
}

# ─────────────────────────────────────────────
# CSS FOR PORTRAIT MODE AND INITIAL STATES
# ─────────────────────────────────────────────
PORTRAIT_OVERRIDES = """
      html, body { width: 1080px; height: 1920px; font-size: 22px; }
      .scene, .scene-video { width: 1080px; height: 1920px; }
      .scene-content { padding: 80px 80px; }
      .top-bar, .bottom-bar { padding: 0 80px; }
      .split-layout { flex-direction: column !important; gap: 40px; }
      .stats-col { flex-direction: row !important; flex-wrap: wrap; gap: 20px; }
      .stat .num { font-size: 80px; }
      .host-grid { grid-template-columns: 1fr !important; }
      .counter-wrap { flex: none !important; width: 100%; }
"""

def _scene_initial_css(scene: dict) -> str:
    """CSS initial states for sub-comp elements (REQUIRED by HyperFrames Studio)."""
    tpl = scene.get("template", "impact_statement")
    lines = ["      #scene1 { opacity: 0; }"] # All scenes start invisible
    if tpl == "impact_statement":
        lines += [
            "      #s1-eyebrow { opacity: 0; transform: translateY(-30px); }",
            "      #s1-headline { opacity: 0; transform: translateY(80px) scale(0.9); }",
            "      #s1-rule { width: 0 !important; }",
            "      #s1-subhead { opacity: 0; transform: translateY(20px); }",
        ]
    elif tpl == "stat_split":
        lines += [
            "      #s1-eyebrow { opacity: 0; transform: translateX(-40px); }",
            "      #s1-headline { opacity: 0; transform: translateY(60px); }",
            "      #s1-sub { opacity: 0; transform: translateY(30px); }",
            "      .stat { opacity: 0; transform: translateX(60px); }",
        ]
    elif tpl == "title_card":
        lines += [
            "      #s1-glow { opacity: 0; transform: scale(0); }",
            "      #s1-eyebrow { opacity: 0; letter-spacing: 0.8em; }",
            "      #s1-headline { opacity: 0; transform: translateY(100px) scale(0.85); }",
            "      #s1-rule { width: 0 !important; }",
            "      #s1-sub { opacity: 0; transform: translateY(20px); }",
        ]
    elif tpl == "stat_focus":
        lines += [
            "      #s1-counter { opacity: 0; transform: scale(0.5); }",
            "      #s1-counter-num { opacity: 0; transform: scale(0); }",
            "      #s1-age { opacity: 0; transform: translateY(20px); }",
            "      #s1-name { opacity: 0; transform: translateX(80px); }",
            "      #s1-quote { opacity: 0; transform: translateY(30px); }",
        ]
    elif tpl == "three_column":
        lines += [
            "      #s1-eyebrow { opacity: 0; transform: translateY(-20px); }",
            "      #s1-headline { opacity: 0; transform: translateY(60px); }",
            "      .host-card { opacity: 0; transform: translateY(80px); }",
        ]
    elif tpl == "tag_list":
        lines += [
            "      #s1-glow { opacity: 0; transform: scale(0); }",
            "      #s1-eyebrow { opacity: 0; transform: translateY(-20px); }",
            "      #s1-headline { opacity: 0; transform: translateY(60px) scale(0.95); }",
            "      #s1-sub { opacity: 0; transform: translateY(20px); }",
            "      .nation { opacity: 0; transform: translateY(40px) scale(0.8); }",
        ]
    elif tpl == "cta":
        lines += [
            "      #s1-badge { opacity: 0; transform: translateY(-20px); }",
            "      #s1-headline { opacity: 0; transform: translateY(80px) scale(0.9); }",
            "      #s1-sub { opacity: 0; transform: translateY(20px); }",
            "      #s1-btn { opacity: 0; transform: scale(0); }",
            "      #s1-subbottom { opacity: 0; transform: translateY(20px); }",
        ]
    return "\n".join(lines)

def _scene_tweens(scene: dict, duration: float) -> str:
    """GSAP tweens for a sub-comp. No window registration."""
    tpl = scene.get("template", "impact_statement")
    lines = ["        var tl = gsap.timeline({ paused: true });"]
    if tpl == "impact_statement":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.4 }, 0.0);',
            '        tl.to("#s1-eyebrow", { y: 0, opacity: 1, duration: 0.5, ease: "power3.out" }, 0.3);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, scale: 1, duration: 0.8, ease: "expo.out" }, 0.7);',
            '        tl.to("#s1-rule", { width: 240, duration: 0.4, ease: "power3.inOut" }, 2.0);',
            '        tl.to("#s1-subhead", { y: 0, opacity: 1, duration: 0.6, ease: "power2.out" }, 3.0);',
        ]
    elif tpl == "stat_split":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.3 }, 0.0);',
            '        tl.to("#s1-eyebrow", { x: 0, opacity: 1, duration: 0.6, ease: "power3.out" }, 0.4);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, duration: 0.7, ease: "expo.out" }, 0.7);',
            '        tl.to("#s1-sub", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 1.4);',
        ]
        for k in range(len(scene["data"].get("stats", []))):
            lines.append(f'        tl.to("#s1-stat{k+1}", {{ x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }}, {2.0+k*0.4:.1f});')
    elif tpl == "title_card":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.4 }, 0.0);',
            '        tl.to("#s1-glow", { scale: 1, opacity: 1, duration: 1.5, ease: "power2.out" }, 0.2);',
            '        tl.to("#s1-eyebrow", { letterSpacing: "0.4em", opacity: 1, duration: 1.0, ease: "power2.out" }, 0.5);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, scale: 1, duration: 1.0, ease: "expo.out" }, 1.0);',
            '        tl.to("#s1-rule", { width: 800, duration: 0.6, ease: "power3.inOut" }, 3.0);',
            '        tl.to("#s1-sub", { y: 0, opacity: 1, duration: 0.7, ease: "power2.out" }, 4.0);',
        ]
    elif tpl == "stat_focus":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.3 }, 0.0);',
            '        tl.to("#s1-counter", { scale: 1, opacity: 1, duration: 0.6, ease: "expo.out" }, 0.4);',
            '        tl.to("#s1-counter-num", { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.7)" }, 0.8);',
            '        tl.to("#s1-age", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 1.5);',
            '        tl.to("#s1-name", { x: 0, opacity: 1, duration: 0.7, ease: "expo.out" }, 2.0);',
            '        tl.to("#s1-quote", { y: 0, opacity: 1, duration: 0.6, ease: "power2.out" }, 2.8);',
        ]
    elif tpl == "three_column":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.4 }, 0.0);',
            '        tl.to("#s1-eyebrow", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 0.3);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, duration: 0.7, ease: "expo.out" }, 0.6);',
        ]
        for k in range(len(scene["data"].get("cards", []))):
            lines.append(f'        tl.to("#s1-card{k+1}", {{ y: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, {1.3+k*0.3:.1f});')
    elif tpl == "tag_list":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.3 }, 0.0);',
            '        tl.to("#s1-glow", { scale: 1, opacity: 1, duration: 1.2, ease: "power2.out" }, 0.2);',
            '        tl.to("#s1-eyebrow", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 0.4);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, scale: 1, duration: 0.7, ease: "expo.out" }, 0.7);',
            '        tl.to("#s1-sub", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 1.5);',
        ]
        for k in range(len(scene["data"].get("tags", []))):
            lines.append(f'        tl.to("#s1-nations .nation:nth-child({k+1})", {{ y: 0, opacity: 1, scale: 1, duration: 0.4, ease: "back.out(1.4)" }}, {2.5+k*0.3:.1f});')
    elif tpl == "cta":
        lines += [
            '        tl.to("#scene1", { opacity: 1, duration: 0.4 }, 0.0);',
            '        tl.to("#s1-badge", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 0.4);',
            '        tl.to("#s1-headline", { y: 0, opacity: 1, scale: 1, duration: 0.9, ease: "expo.out" }, 0.7);',
            '        tl.to("#s1-sub", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 2.0);',
            '        tl.to("#s1-btn", { scale: 1, opacity: 1, duration: 0.6, ease: "back.out(1.5)" }, 3.0);',
            '        tl.to("#s1-subbottom", { y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }, 4.0);',
        ]
    
    # Final fade out
    lines += [
        f'        tl.to("#scene1 .scene-content > *", {{ opacity: 0, y: -20, duration: 0.5, stagger: 0.05 }}, {duration-1.5:.1f});',
        f'        tl.to("#scene1", {{ opacity: 0, duration: 0.4 }}, {duration-0.8:.1f});',
    ]
    return "\n".join(lines)

def build_scene_html(scene: dict, idx: int, fmt: dict, fmt_name: str) -> str:
    w, h = fmt["width"], fmt["height"]
    fs = fmt["font_scale"]
    portrait_css = PORTRAIT_OVERRIDES if fmt_name == "portrait" else ""
    tpl_fn = TEMPLATE_MAP.get(scene.get("template", "impact_statement"), tpl_impact_statement)
    
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="stylesheet" href="../assets/fonts/fonts.css" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
    <style>
      :root {{ --bg: #0a0a0a; --fg: #f5f5f0; --accent: #ffd700; --rule: #2a2a2a; --muted: #888; }}
      html, body {{ margin:0; padding:0; background:var(--bg); color:var(--fg); font-family:"Manrope",sans-serif; font-size:{scale_font(28,fs)}px; width:{w}px; height:{h}px; overflow:hidden; }}
      .display {{ font-family:"Anton",sans-serif; text-transform:uppercase; line-height:0.92; }}
      .mono {{ font-family:"JetBrains Mono",monospace; text-transform:uppercase; }}
      #hyperframes-root {{ position:relative; width:{w}px; height:{h}px; background:var(--bg); }}
      .scene {{ position:absolute; inset:0; z-index:1; }}
      .scene-video {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; filter:brightness(0.5); }}
      .scene-content {{ position:relative; width:100%; height:100%; padding:100px 120px; box-sizing:border-box; display:flex; flex-direction:column; justify-content:center; gap:32px; z-index:3; }}
      .top-bar {{ position:absolute; top:0; left:0; right:0; height:60px; padding:0 120px; display:flex; align-items:center; border-bottom:1px solid var(--rule); color:var(--muted); font-size:18px; }}
      .bottom-bar {{ position:absolute; bottom:0; left:0; right:0; height:80px; padding:0 120px; display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--rule); color:var(--muted); font-size:20px; }}
      .stat {{ padding:24px; border-left:4px solid var(--accent); background:rgba(255,215,0,0.04); }}
      .stat .num {{ font-size:110px; color:var(--accent); }}
      .headline {{ font-size:150px; }}
      .accent {{ color:var(--accent); }}
      .gold-rule {{ position:absolute; background:var(--accent); width:240px; }}
      {portrait_css}
      /* Initial States */
{_scene_initial_css(scene)}
    </style>
  </head>
  <body>
    <div id="hyperframes-root" data-composition-id="scene_{idx:02d}" data-width="{w}" data-height="{h}" data-duration="{scene['duration']:.1f}">
      <video id="vid-scene1" class="scene-video clip" src="../{clip_src(scene['id'])}" muted playsinline data-start="0" data-duration="{scene['duration']}"></video>
      {tpl_fn(scene, 1, fs)}
    </div>
    <script>
      document.addEventListener("DOMContentLoaded", function() {{
{_scene_tweens(scene, scene['duration'])}
        // HyperFrames will find 'tl' automatically if it is in the scope
        window.sceneTimeline = tl;
      }});
    </script>
  </body>
</html>"""

def build_parent_html(config: dict, fmt: dict, total_duration: float) -> str:
    w, h = fmt["width"], fmt["height"]
    mounts = "".join([f'<div data-composition-src="compositions/scene_{i+1:02d}.html" data-composition-id="scene_{i+1:02d}" data-start="{sum(s["duration"] for s in config["scenes"][:i]):.1f}" data-duration="{s["duration"]:.1f}" class="clip"></div>' for i, s in enumerate(config["scenes"])])
    return f"""<!doctype html>
<html lang="en">
  <head><meta charset="UTF-8" /><script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
    <style>html,body{{margin:0;padding:0;background:#000;width:{w}px;height:{h}px;overflow:hidden;}}</style>
  </head>
  <body>
    <div id="hyperframes-root" data-composition-id="composition" data-width="{w}" data-height="{h}" data-duration="{total_duration:.1f}">
      {mounts}
      <audio id="vo-track" src="assets/audio/full_voiceover.mp3" data-start="0" data-duration="{total_duration:.2f}" class="clip"></audio>
    </div>
  </body>
</html>"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--format", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--output", default="composition.html")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    fmt = FORMATS[args.format]
    out_path = Path(args.output)
    comps_dir = out_path.parent / "compositions"
    comps_dir.mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(config["scenes"]):
        with open(comps_dir / f"scene_{i+1:02d}.html", "w", encoding="utf-8") as f:
            f.write(build_scene_html(scene, i + 1, fmt, args.format))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_parent_html(config, fmt, sum(s["duration"] for s in config["scenes"])))

    print(f"✅ Generated {out_path} and {len(config['scenes'])} scenes.")

if __name__ == "__main__":
    main()