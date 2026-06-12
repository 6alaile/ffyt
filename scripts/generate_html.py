"""
scripts/generate_html.py
─────────────────────────────────────────────────────────────
Reads a video config JSON and generates a HyperFrames-ready
HTML composition (index.html style) for rendering.

Usage:
  python scripts/generate_html.py \
    --config configs/wc2026_ep01.json \
    --format landscape \
    --output composition.html

Config JSON structure:
  {
    "title": "Why the 2026 World Cup Is Different",
    "channel": "@6allerAlert",
    "youtube": {
      "description": "...",
      "tags": ["..."],
      "category": "Sports"
    },
    "scenes": [
      {
        "id": "01_hook",
        "template": "impact_statement",
        "duration": 8,
        "clip_query": "soccer stadium crowd cheering",
        "section_label": "THE RECKONING",
        "data": {
          "line1": "EVERY WORLD CUP GETS CALLED",
          "line1_accent": "HISTORIC.",
          "line2": "THIS ONE",
          "line2_accent": "ACTUALLY IS.",
          "subhead": "// 4 MINUTES // 8 REASONS // 1 VERDICT",
          "footer_left": "JUNE 11, 2026 — JULY 19, 2026",
          "footer_right_pill": "PROOF"
        }
      },
      {
        "id": "02_scale",
        "template": "stat_split",
        "duration": 22,
        "clip_query": "soccer football world cup stadium",
        "section_label": "THE ANIMAL IS DIFFERENT",
        "data": {
          "eyebrow": "// THE ANIMAL IS DIFFERENT",
          "headline": "BIGGER THAN EVERY CUP",
          "headline_accent": "BEFORE.",
          "body": "A completely different tournament. The largest single sporting event on Earth.",
          "stats": [
            {"value": "48", "label": "NATIONS"},
            {"value": "104", "label": "MATCHES"},
            {"value": "16", "label": "HOST CITIES"},
            {"value": "3", "label": "COUNTRIES"}
          ],
          "footer_left": "FIFA WORLD CUP — FORMAT REFORM",
          "footer_right": "USA · CAN · MEX"
        }
      }
    ]
  }

Templates available:
  impact_statement  — two large centred lines, accent word, subhead
  stat_split        — headline left, stat cards right
  title_card        — giant centred title, italic caption, names row
  stat_focus        — large bordered stat card left, name + quote right
  three_column      — headline + 3 equal cards with metadata
  tag_list          — centred headline + horizontal tag chips
  cta               — subscribe screen

Format:
  landscape  → 1920x1080 (long form, 16:9)
  portrait   → 1080x1920 (shorts, 9:16)
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


def top_bar(section_label: str, show_timestamp: bool = False) -> str:
    """Renders the top metadata bar. Timestamps suppressed by default."""
    right = ""  # no timestamps in production renders
    return f"""
        <div class="top-bar">
          <span><span class="mark">●</span>&nbsp;&nbsp;{section_label}</span>
          {right}
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
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
        <div class="scene-vignette"></div>
        {top_bar(d.get('section_label', scene.get('section_label', '')))}
        <div class="scene-content" style="align-items:center;text-align:center;">
          <div class="eyebrow" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
          <h1 class="display headline" id="s{idx}-headline">
            {d.get('line1', '')}<br />
            {d.get('line2', '')} <span class="accent">{d.get('line2_accent', '')}</span>
          </h1>
          <div class="gold-rule" id="s{idx}-rule"
            style="left:50%;top:50%;transform:translate(-50%,-50%);width:0;height:4px;"></div>
          <div class="subhead" id="s{idx}-subhead">{d.get('subhead', '')}</div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right_pill', ''), pill=True)}
      </div>"""


def tpl_stat_split(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    stats_html = ""
    for i, stat in enumerate(d.get("stats", [])):
        stats_html += f"""
            <div class="stat" id="s{idx}-stat{i+1}">
              <span class="num display">{stat['value']}</span>
              <span class="label mono">{stat['label']}</span>
            </div>"""
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content split-layout">
          <div class="left">
            <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
            <h2 class="display headline" id="s{idx}-headline">
              {d.get('headline', '')} <span class="accent">{d.get('headline_accent', '')}</span>
            </h2>
            <p class="body-text" id="s{idx}-sub">{d.get('body', '')}</p>
          </div>
          <div class="right stats-col">{stats_html}
          </div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right', ''))}
      </div>"""


def tpl_title_card(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    names_html = ""
    for name in d.get("names", []):
        names_html += f"""
            <div class="display name">{name['name']}<span class="year mono">{name.get('detail','')}</span></div>"""
        names_html += '<div class="vs mono">VS</div>'
    if names_html.endswith('<div class="vs mono">VS</div>'):
        names_html = names_html[:-len('<div class="vs mono">VS</div>')]
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
        <div class="scene-vignette"></div>
        <div class="scene-glow" id="s{idx}-glow" style="left:-400px;top:-200px;"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="align-items:center;text-align:center;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow', '')}</div>
          <h2 class="display headline" id="s{idx}-headline">
            {d.get('headline', '')} <span class="accent">{d.get('headline_accent', '')}</span>
          </h2>
          <div class="gold-rule" id="s{idx}-rule"
            style="left:50%;transform:translateX(-50%);width:0;height:2px;top:50%;"></div>
          <p class="body-italic" id="s{idx}-sub">{d.get('body', '')}</p>
          <div class="names" id="s{idx}-names">{names_html}
          </div>
        </div>
        {bottom_bar(d.get('footer_left', ''), d.get('footer_right', ''))}
      </div>"""


def tpl_stat_focus(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
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
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    cards_html = ""
    for i, card in enumerate(d.get("cards", [])):
        stats_html = "".join(
            f'<div class="host-stat"><span class="v">{s["value"]}</span> · {s["label"]}</div>'
            for s in card.get("stats", [])
        )
        cards_html += f"""
            <div class="host-card" id="s{idx}-card{i+1}">
              <div class="flag">{card.get('flag','')}</div>
              <div class="display host-name">{card.get('name','')}</div>
              <div class="host-stats">{stats_html}</div>
              <div class="host-quote">"{card.get('quote','')}"</div>
            </div>"""
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
        <div class="scene-vignette"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="padding:0 120px;align-items:stretch;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow','')}</div>
          <h2 class="display headline" id="s{idx}-headline">{d.get('headline','')}</h2>
          <div class="host-grid">{cards_html}
          </div>
        </div>
        {bottom_bar(d.get('footer_left',''), d.get('footer_right',''))}
      </div>"""


def tpl_tag_list(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    tags_html = "".join(
        f'<div class="nation"><span class="new">{t.get("prefix","DEBUT")}</span> {t["name"]}</div>'
        for t in d.get("tags", [])
    )
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
        <div class="scene-vignette"></div>
        <div class="scene-glow" id="s{idx}-glow" style="right:-400px;top:-200px;"></div>
        {top_bar(scene.get('section_label', ''))}
        <div class="scene-content" style="align-items:center;text-align:center;padding:0 120px;">
          <div class="eyebrow mono" id="s{idx}-eyebrow">{d.get('eyebrow','')}</div>
          <h2 class="display headline" id="s{idx}-headline">
            {d.get('headline','')} <span class="accent">{d.get('headline_accent','')}</span>
          </h2>
          <p class="body-text" id="s{idx}-sub">{d.get('body','')}</p>
          <div class="nations" id="s{idx}-nations">{tags_html}
          </div>
        </div>
        {bottom_bar(d.get('footer_left',''), d.get('footer_right',''))}
      </div>"""


def tpl_cta(scene: dict, idx: int, fs: float) -> str:
    d = scene["data"]
    sid = f"scene{idx}"
    z = "z-index: 1;" if idx == 1 else "z-index: 2; opacity: 0;"
    return f"""
      <!-- ──────────── SCENE {idx}: {scene['id'].upper()} ──────────── -->
      <div id="{sid}" class="scene" style="{z}">
        <video id="vid-{sid}" class="scene-video"
          src="{clip_src(scene['id'])}" muted playsinline
          data-start="{{{{START_{idx}}}}}" data-duration="{scene['duration']}" data-track-index="0"></video>
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
# GSAP ANIMATION GENERATOR
# ─────────────────────────────────────────────

TRANSITIONS = [
    # (name, out_tween, in_setup)
    ("glitch_zoom",
     'tl.to("#{sid}", {{ scale: 1.08, duration: 0.25, ease: "power3.in" }}, {t_out});\n'
     '      tl.to("#{sid}", {{ opacity: 0, duration: 0.05 }}, {t_cut});\n'
     '      tl.set("#{sid}", {{ visibility: "hidden" }}, {t_next});',
     ''),
    ("burn",
     'tl.to("#{sid}", {{ filter: "brightness(2.5) saturate(0.5)", duration: 0.4, ease: "power3.in" }}, {t_out});\n'
     '      tl.to("#{sid}", {{ opacity: 0, duration: 0.05 }}, {t_cut});\n'
     '      tl.set("#{sid}", {{ visibility: "hidden" }}, {t_next});\n'
     '      tl.set("#{sid}", {{ filter: "none" }}, {t_next});',
     ''),
    ("whip_pan",
     'tl.to("#{sid}", {{ x: -600, scale: 1.1, duration: 0.4, ease: "power3.in" }}, {t_out});\n'
     '      tl.to("#{sid}", {{ opacity: 0, duration: 0.05 }}, {t_cut});\n'
     '      tl.set("#{sid}", {{ visibility: "hidden" }}, {t_next});\n'
     '      tl.set("#{sid}", {{ x: 0, scale: 1 }});',
     ''),
    ("fade",
     'tl.to("#{sid}", {{ opacity: 0, duration: 0.4, ease: "power2.in" }}, {t_out});\n'
     '      tl.set("#{sid}", {{ visibility: "hidden" }}, {t_next});',
     ''),
]


def build_gsap(scenes: list) -> str:
    """Generate GSAP timeline for all scenes."""
    js = []
    js.append("      window.__timelines = window.__timelines || {};")
    js.append("      var tl = gsap.timeline({ paused: true });")
    js.append("")

    # Compute cumulative start times
    starts = []
    t = 0.0
    for s in scenes:
        starts.append(t)
        t += s["duration"]
    total = t

    for i, scene in enumerate(scenes):
        idx = i + 1
        sid = f"scene{idx}"
        t_start = starts[i]
        t_end = t_start + scene["duration"]
        tpl = scene.get("template", "impact_statement")

        js.append(f"      // ════ SCENE {idx}: {scene['id'].upper()} ({t_start:.1f}s → {t_end:.1f}s) ════")
        js.append(f'      gsap.set("#{sid}", {{ opacity: 0 }});')

        # Per-template element animations
        if tpl == "impact_statement":
            js.append(f'      gsap.set("#s{idx}-eyebrow", {{ y: -30, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 80, opacity: 0, scale: 0.9 }});')
            js.append(f'      gsap.set("#s{idx}-rule", {{ width: 0 }});')
            js.append(f'      gsap.set("#s{idx}-subhead", {{ y: 20, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.4, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-eyebrow", {{ y: 0, opacity: 1, duration: 0.5, ease: "power3.out" }}, {t_start+0.3:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, scale: 1, duration: 0.8, ease: "expo.out" }}, {t_start+0.7:.1f});')
            js.append(f'      tl.to("#s{idx}-rule", {{ width: 240, duration: 0.4, ease: "power3.inOut" }}, {t_start+2.0:.1f});')
            js.append(f'      tl.to("#s{idx}-subhead", {{ y: 0, opacity: 1, duration: 0.6, ease: "power2.out" }}, {t_start+3.0:.1f});')

        elif tpl == "stat_split":
            js.append(f'      gsap.set("#s{idx}-eyebrow", {{ x: -40, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 60, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-sub", {{ y: 30, opacity: 0 }});')
            n_stats = len(scene["data"].get("stats", []))
            for k in range(n_stats):
                js.append(f'      gsap.set("#s{idx}-stat{k+1}", {{ x: 60, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.3, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-eyebrow", {{ x: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, {t_start+0.4:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, duration: 0.7, ease: "expo.out" }}, {t_start+0.7:.1f});')
            js.append(f'      tl.to("#s{idx}-sub", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+1.4:.1f});')
            for k in range(n_stats):
                js.append(f'      tl.to("#s{idx}-stat{k+1}", {{ x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }}, {t_start+2.0+k*0.4:.1f});')

        elif tpl == "title_card":
            js.append(f'      gsap.set("#s{idx}-glow", {{ scale: 0, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-eyebrow", {{ letterSpacing: "0.8em", opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 100, opacity: 0, scale: 0.85 }});')
            js.append(f'      gsap.set("#s{idx}-rule", {{ width: 0 }});')
            js.append(f'      gsap.set("#s{idx}-sub", {{ y: 20, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.4, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-glow", {{ scale: 1, opacity: 1, duration: 1.5, ease: "power2.out" }}, {t_start+0.2:.1f});')
            js.append(f'      tl.to("#s{idx}-eyebrow", {{ letterSpacing: "0.4em", opacity: 1, duration: 1.0, ease: "power2.out" }}, {t_start+0.5:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, scale: 1, duration: 1.0, ease: "expo.out" }}, {t_start+1.0:.1f});')
            js.append(f'      tl.to("#s{idx}-rule", {{ width: 800, duration: 0.6, ease: "power3.inOut" }}, {t_start+3.0:.1f});')
            js.append(f'      tl.to("#s{idx}-sub", {{ y: 0, opacity: 1, duration: 0.7, ease: "power2.out" }}, {t_start+4.0:.1f});')

        elif tpl == "stat_focus":
            js.append(f'      gsap.set("#s{idx}-counter", {{ scale: 0.5, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-counter-num", {{ scale: 0, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-age", {{ y: 20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-name", {{ x: 80, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-quote", {{ y: 30, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.3, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-counter", {{ scale: 1, opacity: 1, duration: 0.6, ease: "expo.out" }}, {t_start+0.4:.1f});')
            js.append(f'      tl.to("#s{idx}-counter-num", {{ scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.7)" }}, {t_start+0.8:.1f});')
            js.append(f'      tl.to("#s{idx}-age", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+1.5:.1f});')
            js.append(f'      tl.to("#s{idx}-name", {{ x: 0, opacity: 1, duration: 0.7, ease: "expo.out" }}, {t_start+2.0:.1f});')
            js.append(f'      tl.to("#s{idx}-quote", {{ y: 0, opacity: 1, duration: 0.6, ease: "power2.out" }}, {t_start+2.8:.1f});')

        elif tpl == "three_column":
            js.append(f'      gsap.set("#s{idx}-eyebrow", {{ y: -20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 60, opacity: 0 }});')
            n_cards = len(scene["data"].get("cards", []))
            for k in range(n_cards):
                js.append(f'      gsap.set("#s{idx}-card{k+1}", {{ y: 80, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.4, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-eyebrow", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+0.3:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, duration: 0.7, ease: "expo.out" }}, {t_start+0.6:.1f});')
            for k in range(n_cards):
                js.append(f'      tl.to("#s{idx}-card{k+1}", {{ y: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, {t_start+1.3+k*0.3:.1f});')

        elif tpl == "tag_list":
            js.append(f'      gsap.set("#s{idx}-glow", {{ scale: 0, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-eyebrow", {{ y: -20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 60, opacity: 0, scale: 0.95 }});')
            js.append(f'      gsap.set("#s{idx}-sub", {{ y: 20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-nations .nation", {{ y: 40, opacity: 0, scale: 0.8 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.3, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-glow", {{ scale: 1, opacity: 1, duration: 1.2, ease: "power2.out" }}, {t_start+0.2:.1f});')
            js.append(f'      tl.to("#s{idx}-eyebrow", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+0.4:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, scale: 1, duration: 0.7, ease: "expo.out" }}, {t_start+0.7:.1f});')
            js.append(f'      tl.to("#s{idx}-sub", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+1.5:.1f});')
            n_tags = len(scene["data"].get("tags", []))
            for k in range(n_tags):
                js.append(f'      tl.to("#s{idx}-nations .nation:nth-child({k+1})", {{ y: 0, opacity: 1, scale: 1, duration: 0.4, ease: "back.out(1.4)" }}, {t_start+2.5+k*0.3:.1f});')

        elif tpl == "cta":
            js.append(f'      gsap.set("#s{idx}-badge", {{ y: -20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-headline", {{ y: 80, opacity: 0, scale: 0.9 }});')
            js.append(f'      gsap.set("#s{idx}-sub", {{ y: 20, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-btn", {{ scale: 0, opacity: 0 }});')
            js.append(f'      gsap.set("#s{idx}-subbottom", {{ y: 20, opacity: 0 }});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 1, duration: 0.4, ease: "power2.inOut" }}, {t_start:.1f});')
            js.append(f'      tl.to("#s{idx}-badge", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+0.4:.1f});')
            js.append(f'      tl.to("#s{idx}-headline", {{ y: 0, opacity: 1, scale: 1, duration: 0.9, ease: "expo.out" }}, {t_start+0.7:.1f});')
            js.append(f'      tl.to("#s{idx}-sub", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+2.0:.1f});')
            js.append(f'      tl.to("#s{idx}-btn", {{ scale: 1, opacity: 1, duration: 0.6, ease: "back.out(1.5)" }}, {t_start+3.0:.1f});')
            js.append(f'      tl.to("#s{idx}-subbottom", {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out" }}, {t_start+4.0:.1f});')

        # Transition out (skip last scene)
        if i < len(scenes) - 1:
            trans = TRANSITIONS[i % len(TRANSITIONS)]
            t_out = t_end - 0.4
            t_cut = t_end - 0.05
            t_next = t_end
            out_js = trans[1].replace("{sid}", sid).replace(
                "{t_out}", f"{t_out:.2f}").replace(
                "{t_cut}", f"{t_cut:.2f}").replace(
                "{t_next}", f"{t_next:.1f}")
            js.append(f"      // Transition → scene{idx+1}")
            js.append(f"      {out_js}")
        else:
            # Final scene: fade everything out
            js.append(f'      tl.to("#{sid} .scene-content > *", {{ opacity: 0, y: -20, duration: 0.5, ease: "power2.in", stagger: 0.05 }}, {t_end-1.5:.1f});')
            js.append(f'      tl.to("#{sid} .top-bar, #{sid} .bottom-bar", {{ opacity: 0, duration: 0.3 }}, {t_end-1.5:.1f});')
            js.append(f'      tl.to("#{sid}", {{ opacity: 0, duration: 0.4 }}, {t_end-0.8:.1f});')
            js.append(f'      tl.set("#{sid}", {{ visibility: "hidden" }}, {t_end-0.4:.1f});')

        js.append("")

    js.append(f'      window.__timelines["{{}}" ] = tl;'.format("composition"))
    return "\n".join(js)


# ─────────────────────────────────────────────
# CSS FOR PORTRAIT MODE OVERRIDES
# ─────────────────────────────────────────────
PORTRAIT_OVERRIDES = """
      /* ── Portrait (9:16) overrides ── */
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


# ─────────────────────────────────────────────
# FULL HTML ASSEMBLY
# ─────────────────────────────────────────────

def build_html(config: dict, fmt: dict, fmt_name: str) -> str:
    scenes = config["scenes"]
    w, h = fmt["width"], fmt["height"]
    fs = fmt["font_scale"]

    # Compute start times for placeholder replacement
    starts = []
    t = 0.0
    for s in scenes:
        starts.append(t)
        t += s["duration"]
    total_duration = t

    # Build scene visibility CSS
    scene_vis_css = "\n".join(
        f"      #scene{i+1} {{ z-index: {'1' if i == 0 else '2'}; {'opacity: 0;' if i > 0 else ''} }}"
        for i in range(len(scenes))
    )

    portrait_css = PORTRAIT_OVERRIDES if fmt_name == "portrait" else ""

    # Build scene HTML
    scenes_html = ""
    for i, scene in enumerate(scenes):
        tpl_fn = TEMPLATE_MAP.get(scene.get("template", "impact_statement"), tpl_impact_statement)
        scenes_html += tpl_fn(scene, i + 1, fs)

    # Voiceover element
    vo_html = f"""
      <!-- ──────────── VOICEOVER ──────────── -->
      <audio id="vo-track" src="assets/audio/full_voiceover.mp3"
        data-start="0" data-duration="{total_duration:.2f}"
        data-track-index="2" data-volume="1"></audio>"""

    gsap_js = build_gsap(scenes)

    # Replace start time placeholders
    for i, t_start in enumerate(starts):
        scenes_html = scenes_html.replace(f"{{{{START_{i+1}}}}}", str(t_start))

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>{config.get('title', 'Video Composition')}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Anton&family=Manrope:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      :root {{
        --bg: #0a0a0a;
        --fg: #f5f5f0;
        --accent: #ffd700;
        --accent-dim: #b8980a;
        --rule: #2a2a2a;
        --muted: #888;
      }}

      html, body {{
        margin: 0; padding: 0;
        background: var(--bg);
        color: var(--fg);
        font-family: "Manrope", system-ui, sans-serif;
        font-weight: 350;
        font-size: {scale_font(28, fs)}px;
        line-height: 1.35;
        overflow: hidden;
        width: {w}px;
        height: {h}px;
      }}

      .display, .display * {{
        font-family: "Anton", "Arial Narrow", sans-serif;
        font-weight: 400;
        letter-spacing: -0.005em;
        line-height: 0.92;
        text-transform: uppercase;
      }}

      .mono, .mono * {{
        font-family: "JetBrains Mono", "Courier New", monospace;
        font-variant-numeric: tabular-nums;
        letter-spacing: 0;
      }}

      .scene {{
        position: absolute;
        inset: 0;
        width: {w}px;
        height: {h}px;
        overflow: hidden;
        background: var(--bg);
      }}

      {scene_vis_css}

      .scene-content {{
        position: relative;
        width: 100%;
        height: 100%;
        padding: 100px 120px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 32px;
        z-index: 3;
      }}

      .scene-video {{
        position: absolute;
        inset: 0;
        width: {w}px;
        height: {h}px;
        object-fit: cover;
        z-index: 1;
        filter: brightness(0.55) saturate(0.7);
      }}

      .scene-vignette {{
        position: absolute;
        inset: 0;
        z-index: 2;
        background:
          radial-gradient(ellipse 80% 60% at 50% 50%, rgba(10,10,10,0.35), rgba(10,10,10,0.85) 100%),
          linear-gradient(180deg, rgba(10,10,10,0.4) 0%, rgba(10,10,10,0.1) 30%, rgba(10,10,10,0.7) 100%);
        pointer-events: none;
      }}

      .scene-glow {{
        position: absolute;
        width: 1400px; height: 1400px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,215,0,0.12) 0%, rgba(255,215,0,0) 60%);
        z-index: 2;
        pointer-events: none;
      }}

      .top-bar {{
        position: absolute; top: 0; left: 0; right: 0;
        height: 60px; padding: 0 120px;
        display: flex; justify-content: space-between; align-items: center;
        z-index: 5;
        font-family: "JetBrains Mono", monospace;
        font-size: {scale_font(18, fs)}px;
        color: var(--muted);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        border-bottom: 1px solid var(--rule);
      }}
      .top-bar .mark {{ color: var(--accent); font-weight: 700; }}

      .bottom-bar {{
        position: absolute; bottom: 0; left: 0; right: 0;
        height: 80px; padding: 0 120px;
        display: flex; justify-content: space-between; align-items: center;
        z-index: 5;
        font-family: "JetBrains Mono", monospace;
        font-size: {scale_font(20, fs)}px;
        color: var(--muted);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        border-top: 1px solid var(--rule);
      }}
      .bottom-bar .pill {{
        color: var(--accent);
        padding: 6px 14px;
        border: 1px solid var(--accent);
        border-radius: 2px;
      }}

      /* Layout helpers */
      .split-layout {{ flex-direction: row !important; align-items: stretch; gap: 80px; padding: 0 120px; }}
      .left {{ flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 40px; }}
      .right {{ flex: 1; display: flex; flex-direction: column; gap: 32px; justify-content: center; }}
      .stats-col {{ flex: 0 0 700px; display: flex; flex-direction: column; gap: 24px; justify-content: center; }}

      /* Typography */
      .eyebrow {{ font-family: "JetBrains Mono",monospace; font-size:{scale_font(22,fs)}px; color:var(--accent); letter-spacing:0.4em; text-transform:uppercase; }}
      .headline {{ font-size:{scale_font(150,fs)}px; color:var(--fg); }}
      .headline .accent {{ color:var(--accent); }}
      .body-text {{ font-size:{scale_font(34,fs)}px; color:var(--fg); line-height:1.3; max-width:1200px; }}
      .body-italic {{ font-size:{scale_font(36,fs)}px; color:var(--fg); font-style:italic; font-weight:300; max-width:1100px; margin-top:24px; }}
      .subhead {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(28,fs)}px; color:var(--muted); letter-spacing:0.1em; text-transform:uppercase; margin-top:32px; }}

      /* Stat cards */
      .stat {{ display:flex; flex-direction:column; gap:8px; padding:24px 32px; border-left:4px solid var(--accent); background:rgba(255,215,0,0.04); }}
      .stat .num {{ font-size:{scale_font(110,fs)}px; color:var(--accent); line-height:0.9; }}
      .stat .label {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(22,fs)}px; color:var(--fg); letter-spacing:0.1em; text-transform:uppercase; }}

      /* Names row */
      .names {{ display:flex; gap:80px; margin-top:40px; align-items:center; justify-content:center; }}
      .name {{ font-size:{scale_font(80,fs)}px; color:var(--accent); }}
      .name .year {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(24,fs)}px; color:var(--muted); letter-spacing:0.1em; display:block; margin-top:8px; }}
      .vs {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(32,fs)}px; color:var(--muted); }}
      .gold-rule {{ position:absolute; background:var(--accent); z-index:4; }}

      /* Stat focus */
      .counter-wrap {{ flex:0 0 900px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:60px; border:4px solid var(--accent); background:rgba(255,215,0,0.05); }}
      .counter-label {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(24,fs)}px; color:var(--accent); letter-spacing:0.3em; text-transform:uppercase; margin-bottom:16px; }}
      .counter {{ font-size:{scale_font(380,fs)}px; color:var(--accent); line-height:0.85; }}
      .counter-suffix {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(36,fs)}px; color:var(--fg); letter-spacing:0.1em; text-transform:uppercase; margin-top:16px; }}
      .age {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(32,fs)}px; color:var(--accent); letter-spacing:0.15em; text-transform:uppercase; }}
      .quote {{ font-size:{scale_font(36,fs)}px; color:var(--fg); line-height:1.3; border-left:4px solid var(--accent); padding-left:24px; margin-top:24px; }}

      /* Three column */
      .host-grid {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:40px; flex:1; }}
      .host-card {{ display:flex; flex-direction:column; gap:16px; padding:40px 32px; background:rgba(255,255,255,0.03); border-top:6px solid var(--accent); }}
      .flag {{ font-size:{scale_font(90,fs)}px; line-height:1; filter:drop-shadow(0 4px 12px rgba(0,0,0,0.6)); }}
      .host-name {{ font-size:{scale_font(64,fs)}px; color:var(--fg); }}
      .host-stats {{ display:flex; flex-direction:column; gap:4px; margin-top:auto; }}
      .host-stat {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(20,fs)}px; color:var(--muted); letter-spacing:0.05em; text-transform:uppercase; }}
      .host-stat .v {{ color:var(--fg); }}
      .host-quote {{ font-size:{scale_font(22,fs)}px; color:var(--accent); font-style:italic; margin-top:12px; }}

      /* Tag list */
      .nations {{ display:flex; flex-wrap:wrap; gap:24px; justify-content:center; max-width:1600px; }}
      .nation {{ display:flex; align-items:center; gap:12px; padding:16px 28px; background:rgba(255,215,0,0.08); border:1px solid var(--accent); font-family:"JetBrains Mono",monospace; font-size:{scale_font(32,fs)}px; color:var(--fg); text-transform:uppercase; letter-spacing:0.04em; }}
      .nation .new {{ color:var(--accent); font-size:{scale_font(18,fs)}px; letter-spacing:0.2em; }}

      /* CTA */
      .badge {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(22,fs)}px; color:var(--accent); letter-spacing:0.4em; text-transform:uppercase; margin-bottom:24px; padding:12px 32px; border:2px solid var(--accent); }}
      .subscribe-btn {{ display:inline-flex; align-items:center; gap:16px; margin-top:48px; padding:24px 64px; background:var(--accent); color:var(--bg); font-family:"Anton",sans-serif; font-size:{scale_font(56,fs)}px; text-transform:uppercase; letter-spacing:0.05em; cursor:pointer; }}
      .sub-bottom {{ font-family:"JetBrains Mono",monospace; font-size:{scale_font(22,fs)}px; color:var(--muted); letter-spacing:0.2em; text-transform:uppercase; margin-top:24px; }}
      .trophy {{ position:absolute; bottom:100px; right:100px; font-size:{scale_font(180,fs)}px; opacity:0.15; }}

      {portrait_css}
    </style>
  </head>
  <body>
    <div id="root"
      data-composition-id="composition"
      data-width="{w}"
      data-height="{h}"
      data-start="0"
      data-duration="{total_duration:.1f}"
    >
      {scenes_html}
      {vo_html}
    </div>

    <script>
      {gsap_js}
    </script>
  </body>
</html>"""

    return html


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate HyperFrames HTML from config JSON")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument("--format", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--output", default="composition.html")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    fmt = FORMATS[args.format]
    html = build_html(config, fmt, args.format)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(s["duration"] for s in config["scenes"])
    print(f"✅ Generated {out_path}")
    print(f"   Format:   {args.format} ({fmt['width']}x{fmt['height']})")
    print(f"   Scenes:   {len(config['scenes'])}")
    print(f"   Duration: {total:.0f}s ({total/60:.1f} min)")


if __name__ == "__main__":
    main()
