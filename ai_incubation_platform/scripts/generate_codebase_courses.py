#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为孵化器十个子项目各生成一份 codebase-to-course 风格单页 HTML（自包含）。"""
from __future__ import annotations

import html
import os
import sys
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def term(d: str, text: str) -> str:
    return f'<span class="term" data-definition="{esc(d)}">{esc(text)}</span>'


COMMON_CSS = r"""
:root {
  --color-bg: #FAF7F2;
  --color-bg-warm: #F5F0E8;
  --color-bg-code: #1E1E2E;
  --color-text: #2C2A28;
  --color-text-secondary: #6B6560;
  --color-text-muted: #9E9790;
  --color-border: #E5DFD6;
  --color-border-light: #EEEBE5;
  --color-surface: #FFFFFF;
  --color-surface-warm: #FDF9F3;
  --color-accent: #D94F30;
  --color-accent-hover: #C4432A;
  --color-accent-light: #FDEEE9;
  --color-accent-muted: #E8836C;
  --color-success: #2D8B55;
  --color-success-light: #E8F5EE;
  --color-error: #C93B3B;
  --color-error-light: #FDE8E8;
  --color-info: #2A7B9B;
  --color-info-light: #E4F2F7;
  --color-actor-1: #D94F30;
  --color-actor-2: #2A7B9B;
  --color-actor-3: #7B6DAA;
  --color-actor-4: #D4A843;
  --color-actor-5: #2D8B55;
  --font-display: 'Bricolage Grotesque', Georgia, serif;
  --font-body: 'DM Sans', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;
  --text-5xl: 3rem;
  --text-6xl: 3.75rem;
  --leading-tight: 1.15;
  --leading-snug: 1.3;
  --leading-normal: 1.6;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --content-width: 800px;
  --content-width-wide: 1000px;
  --nav-height: 52px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(44, 42, 40, 0.05);
  --shadow-md: 0 4px 12px rgba(44, 42, 40, 0.08);
  --shadow-lg: 0 8px 24px rgba(44, 42, 40, 0.1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;
}
* { box-sizing: border-box; }
html { scroll-snap-type: y proximity; scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-body);
  color: var(--color-text);
  background: var(--color-bg);
  background-image: radial-gradient(ellipse at 20% 50%, rgba(217, 79, 48, 0.03) 0%, transparent 50%);
  line-height: var(--leading-normal);
  font-size: var(--text-base);
}
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(250, 247, 242, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-border-light);
  min-height: var(--nav-height);
}
.progress-bar {
  height: 3px;
  background: var(--color-accent);
  width: 0%;
  transition: width 0.15s linear;
}
.nav-inner {
  max-width: var(--content-width-wide);
  margin: 0 auto;
  padding: var(--space-3) var(--space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}
.nav-title { font-family: var(--font-display); font-weight: 700; font-size: var(--text-sm); }
.nav-dots { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.nav-dot {
  width: 11px; height: 11px;
  border-radius: 50%;
  border: 2px solid var(--color-text-muted);
  background: transparent;
  cursor: pointer;
  padding: 0;
}
.nav-dot.current { border-color: var(--color-accent); background: var(--color-accent); box-shadow: 0 0 0 3px rgba(217,79,48,0.15); }
.nav-dot.visited { background: var(--color-accent-muted); border-color: var(--color-accent-muted); }
.module {
  min-height: 100vh;
  min-height: 100dvh;
  scroll-snap-align: start;
  padding: var(--space-16) var(--space-6);
  padding-top: calc(var(--nav-height) + var(--space-12));
}
.module-content { max-width: var(--content-width); margin: 0 auto; }
.module-header { margin-bottom: var(--space-10); }
.module-number {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: var(--text-6xl);
  line-height: 1;
  color: rgba(217, 79, 48, 0.15);
  display: block;
}
.module-title { font-family: var(--font-display); font-size: var(--text-4xl); font-weight: 700; margin: var(--space-2) 0; line-height: var(--leading-tight); }
.module-subtitle { color: var(--color-text-secondary); font-size: var(--text-lg); margin: 0; }
.screen { margin-bottom: var(--space-12); }
.screen-heading { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 600; margin: 0 0 var(--space-4); }
.lead { font-size: var(--text-lg); color: var(--color-text-secondary); max-width: 38em; }
.animate-in { opacity: 0; transform: translateY(16px); transition: opacity var(--duration-slow) var(--ease-out), transform var(--duration-slow) var(--ease-out); }
.animate-in.visible { opacity: 1; transform: translateY(0); }
.term {
  border-bottom: 1.5px dashed var(--color-accent-muted);
  cursor: pointer;
}
.term:hover, .term.active { border-bottom-color: var(--color-accent); color: var(--color-accent); }
.term-tooltip {
  position: fixed;
  background: var(--color-bg-code);
  color: #CDD6F4;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  width: max(200px, min(320px, 80vw));
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--duration-fast);
  z-index: 10000;
}
.term-tooltip.visible { opacity: 1; }
.translation-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  margin: var(--space-8) 0;
}
.translation-code {
  background: var(--color-bg-code);
  color: #CDD6F4;
  padding: var(--space-6);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.7;
  position: relative;
  overflow-x: hidden;
}
.translation-code pre, .translation-code code {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
.translation-english {
  background: var(--color-surface-warm);
  padding: var(--space-6);
  font-size: var(--text-sm);
  line-height: 1.7;
  border-left: 3px solid var(--color-accent);
  position: relative;
}
.translation-label {
  position: absolute;
  top: var(--space-2);
  right: var(--space-3);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.5;
}
.code-keyword { color: #CBA6F7; }
.code-string { color: #A6E3A1; }
.code-function { color: #89B4FA; }
.code-comment { color: #6C7086; }
.callout {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-5);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-accent);
  background: var(--color-accent-light);
  margin: var(--space-6) 0;
}
.callout-icon { font-size: 1.35rem; }
.pattern-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
  margin: var(--space-6) 0;
}
.pattern-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  border-top: 3px solid var(--color-actor-2);
}
.pattern-title { font-family: var(--font-display); font-weight: 600; margin: 0 0 var(--space-2); }
.pattern-desc { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.flow-steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-6) 0;
}
.flow-step {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  flex: 1 1 140px;
  text-align: center;
}
.flow-step-num {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-2);
}
.flow-arrow { font-size: var(--text-xl); color: var(--color-text-muted); }
.flow-animation {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-md);
  margin: var(--space-6) 0;
}
.flow-actors { display: flex; flex-wrap: wrap; justify-content: space-around; gap: var(--space-4); margin-bottom: var(--space-4); }
.flow-actor {
  text-align: center;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 2px solid var(--color-border);
  transition: transform var(--duration-normal) var(--ease-out), box-shadow var(--duration-normal);
  min-width: 120px;
}
.flow-actor.active {
  box-shadow: 0 0 0 3px var(--color-accent), 0 0 20px rgba(217, 79, 48, 0.15);
  transform: scale(1.03);
}
.flow-actor-icon {
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto var(--space-2);
  font-weight: 700;
  color: #fff;
}
.flow-label { text-align: center; font-size: var(--text-sm); color: var(--color-text-secondary); min-height: 2.5em; }
.flow-controls { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; justify-content: center; margin-top: var(--space-4); }
.btn {
  border: none;
  border-radius: var(--radius-full);
  padding: var(--space-3) var(--space-5);
  font-family: var(--font-body);
  font-weight: 600;
  cursor: pointer;
  background: var(--color-accent);
  color: #fff;
}
.btn.secondary { background: var(--color-surface); color: var(--color-text); border: 2px solid var(--color-border); }
.chat-window {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-6);
  margin: var(--space-6) 0;
}
.chat-messages { display: flex; flex-direction: column; gap: var(--space-3); min-height: 120px; }
.chat-message { display: none; gap: var(--space-3); align-items: flex-start; animation: fadeUp 0.35s var(--ease-out); }
.chat-message.show { display: flex; }
.chat-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; font-size: var(--text-sm);
}
.chat-bubble { background: var(--color-surface-warm); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); flex: 1; border: 1px solid var(--color-border-light); }
.chat-sender { font-size: var(--text-xs); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
.chat-controls { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; margin-top: var(--space-4); }
.chat-typing { display: none; align-items: center; gap: var(--space-3); }
.chat-typing.show { display: flex; }
.typing-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-text-muted); animation: bounce 1.2s infinite; }
.typing-dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.file-tree {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--color-bg-code);
  color: #CDD6F4;
  padding: var(--space-5);
  border-radius: var(--radius-md);
  line-height: 1.6;
}
.file-tree .note { color: #A6E3A1; }
.quiz-container { margin-top: var(--space-6); }
.quiz-question-block { margin-bottom: var(--space-6); }
.quiz-question { font-family: var(--font-display); font-size: var(--text-lg); margin: 0 0 var(--space-3); }
.quiz-options { display: flex; flex-direction: column; gap: var(--space-2); }
.quiz-option {
  display: flex; align-items: flex-start; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  text-align: left;
  font-family: var(--font-body);
  font-size: var(--text-sm);
}
.quiz-option:hover { border-color: var(--color-accent-muted); }
.quiz-option.selected { border-color: var(--color-accent); background: var(--color-accent-light); }
.quiz-option.correct { border-color: var(--color-success); background: var(--color-success-light); }
.quiz-option.incorrect { border-color: var(--color-error); background: var(--color-error-light); }
.quiz-feedback { display: none; margin-top: var(--space-2); padding: var(--space-3); border-radius: var(--radius-sm); font-size: var(--text-sm); }
.quiz-feedback.show { display: block; }
.quiz-feedback.success { background: var(--color-success-light); color: var(--color-success); }
.quiz-feedback.error { background: var(--color-error-light); color: var(--color-error); }
.quiz-actions { display: flex; gap: var(--space-3); margin-top: var(--space-4); flex-wrap: wrap; }
.hero-pill {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: var(--color-accent-light);
  color: var(--color-accent);
  margin-bottom: var(--space-4);
}
@media (max-width: 768px) {
  .translation-block { grid-template-columns: 1fr; }
  .translation-english { border-left: none; border-top: 3px solid var(--color-accent); }
  .module { padding: var(--space-10) var(--space-4); }
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: var(--radius-full); }
pre, code { white-space: pre-wrap; word-break: break-word; }
"""


def common_js(module_ids: list[str]) -> str:
    mids = ",".join(f'"{m}"' for m in module_ids)
    return f"""
(function() {{
  const moduleIds = [{mids}];

  function initTooltips() {{
    let active = null;
    document.querySelectorAll('.term').forEach(function(term) {{
      term.addEventListener('mouseenter', function() {{
        if (active && active.el !== term) {{
          active.tip.classList.remove('visible');
          active.tip.remove();
        }}
        const tip = document.createElement('div');
        tip.className = 'term-tooltip';
        tip.textContent = term.getAttribute('data-definition') || '';
        document.body.appendChild(tip);
        const rect = term.getBoundingClientRect();
        const tw = Math.min(320, window.innerWidth - 16);
        let left = rect.left + rect.width / 2 - tw / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
        tip.style.width = tw + 'px';
        const th = tip.offsetHeight;
        let top = rect.top - th - 10;
        if (top < 8) top = rect.bottom + 10;
        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
        requestAnimationFrame(function() {{ tip.classList.add('visible'); }});
        active = {{ el: term, tip: tip }};
      }});
      term.addEventListener('mouseleave', function() {{
        if (active && active.tip) {{
          active.tip.classList.remove('visible');
          setTimeout(function() {{ if (active && active.tip) active.tip.remove(); active = null; }}, 120);
        }}
      }});
      term.addEventListener('click', function(e) {{
        e.preventDefault();
        term.classList.toggle('active');
      }});
    }});
  }}

  function scrollToModule(id) {{
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  function updateNav() {{
    const bar = document.querySelector('.progress-bar');
    const h = document.documentElement;
    const pct = (h.scrollTop / (h.scrollHeight - h.clientHeight)) * 100;
    if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    const dots = document.querySelectorAll('.nav-dot');
    let current = 0;
    moduleIds.forEach(function(id, i) {{
      const sec = document.getElementById(id);
      if (!sec) return;
      const r = sec.getBoundingClientRect();
      if (r.top <= 120) current = i;
    }});
    dots.forEach(function(d, i) {{
      d.classList.toggle('current', i === current);
      d.classList.toggle('visited', i < current);
    }});
  }}

  let ticking = false;
  window.addEventListener('scroll', function() {{
    if (!ticking) {{
      ticking = true;
      requestAnimationFrame(function() {{ updateNav(); ticking = false; }});
    }}
  }}, {{ passive: true }});

  document.querySelectorAll('.nav-dot').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      scrollToModule(btn.getAttribute('data-target'));
    }});
  }});

  document.addEventListener('keydown', function(e) {{
    if (['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
    const i = moduleIds.findIndex(function(id) {{
      const el = document.getElementById(id);
      return el && el.getBoundingClientRect().top >= -40 && el.getBoundingClientRect().top < window.innerHeight / 2;
    }});
    const idx = i < 0 ? 0 : i;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {{
      e.preventDefault();
      const n = Math.min(moduleIds.length - 1, idx + 1);
      scrollToModule(moduleIds[n]);
    }}
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {{
      e.preventDefault();
      const n = Math.max(0, idx - 1);
      scrollToModule(moduleIds[n]);
    }}
  }});

  const io = new IntersectionObserver(function(entries) {{
    entries.forEach(function(en) {{
      if (en.isIntersecting) en.target.classList.add('visible');
    }});
  }}, {{ rootMargin: '0px 0px -8% 0px', threshold: 0.12 }});
  document.querySelectorAll('.animate-in').forEach(function(el) {{ io.observe(el); }});

  window.initFlow = function(domPrefix, steps, fnPrefix) {{
    fnPrefix = fnPrefix || String(domPrefix).replace(/-/g, '_');
    const label = document.getElementById(domPrefix + '-label');
    let step = 0;
    window[fnPrefix + '_next'] = function() {{
      if (step >= steps.length) return;
      for (let k = 1; k <= 12; k++) {{
        const el = document.getElementById(domPrefix + '-actor-' + k);
        if (el) el.classList.remove('active');
      }}
      const s = steps[step];
      const hi = document.getElementById(domPrefix + '-actor-' + s.hi);
      if (hi) hi.classList.add('active');
      if (label) label.textContent = s.text;
      step++;
    }};
    window[fnPrefix + '_reset'] = function() {{
      step = 0;
      for (let k = 1; k <= 12; k++) {{
        const el = document.getElementById(domPrefix + '-actor-' + k);
        if (el) el.classList.remove('active');
      }}
      if (label) label.textContent = '点击下方「下一步」开始';
    }};
  }};

  window.playChat = function(chatId, fnPrefix) {{
    fnPrefix = fnPrefix || String(chatId).replace(/-/g, '_');
    const root = document.getElementById(chatId);
    if (!root) return;
    const msgs = root.querySelectorAll('.chat-message');
    const typing = root.querySelector('.chat-typing');
    let i = 0;
    window[fnPrefix + '_next'] = function() {{
      if (i >= msgs.length) return;
      if (typing) {{
        typing.classList.add('show');
        setTimeout(function() {{
          typing.classList.remove('show');
          msgs[i].classList.add('show');
          i++;
        }}, 500);
      }} else {{
        msgs[i].classList.add('show');
        i++;
      }}
    }};
    window[fnPrefix + '_reset'] = function() {{
      msgs.forEach(function(m) {{ m.classList.remove('show'); }});
      if (typing) typing.classList.remove('show');
      i = 0;
    }};
  }};

  window.quizSelect = function(btn) {{
    const block = btn.closest('.quiz-question-block');
    block.querySelectorAll('.quiz-option').forEach(function(o) {{ o.classList.remove('selected'); }});
    btn.classList.add('selected');
  }};

  window.quizCheck = function(containerId) {{
    const root = document.getElementById(containerId);
    if (!root) return;
    root.querySelectorAll('.quiz-question-block').forEach(function(q) {{
      const sel = q.querySelector('.quiz-option.selected');
      const correct = q.getAttribute('data-correct');
      const fb = q.querySelector('.quiz-feedback');
      if (!sel) {{
        if (fb) {{ fb.textContent = '先选一个答案再检查哦。'; fb.className = 'quiz-feedback show error'; }}
        return;
      }}
      q.querySelectorAll('.quiz-option').forEach(function(o) {{ o.disabled = true; }});
      if (sel.getAttribute('data-value') === correct) {{
        sel.classList.add('correct');
        if (fb) {{ fb.innerHTML = q.getAttribute('data-exp-ok') || '很好。'; fb.className = 'quiz-feedback show success'; }}
      }} else {{
        sel.classList.add('incorrect');
        const ok = q.querySelector('[data-value=\"' + correct + '\"]');
        if (ok) ok.classList.add('correct');
        if (fb) {{ fb.innerHTML = q.getAttribute('data-exp-bad') || '再想想。'; fb.className = 'quiz-feedback show error'; }}
      }}
    }});
  }};

  window.quizReset = function(containerId) {{
    const root = document.getElementById(containerId);
    if (!root) return;
    root.querySelectorAll('.quiz-option').forEach(function(o) {{
      o.classList.remove('selected','correct','incorrect');
      o.disabled = false;
    }});
    root.querySelectorAll('.quiz-feedback').forEach(function(f) {{ f.className = 'quiz-feedback'; f.textContent = ''; }});
  }};

  initTooltips();
  updateNav();
}})();
"""


def translation_block(code_html: str, lines_zh: list[str]) -> str:
    zh = "".join(f'<p class="tl">{esc(l)}</p>' for l in lines_zh)
    return f"""
<div class="translation-block animate-in">
  <div class="translation-code">
    <span class="translation-label">CODE</span>
    <pre><code>{code_html}</code></pre>
  </div>
  <div class="translation-english">
    <span class="translation-label">白话</span>
    <div class="translation-lines">{zh}</div>
  </div>
</div>"""


def quiz_block(qid: str, questions: list[dict[str, Any]]) -> str:
    parts = [f'<div class="quiz-container" id="{esc(qid)}">']
    for i, q in enumerate(questions):
        opts = []
        for j, (val, label) in enumerate(q["options"]):
            opts.append(
                f'<button type="button" class="quiz-option" data-value="{esc(val)}" onclick="quizSelect(this)"><span>{esc(label)}</span></button>'
            )
        parts.append(
            f"""
<div class="quiz-question-block" data-correct="{esc(q["correct"])}" data-exp-ok="{esc(q.get("ok", ""))}" data-exp-bad="{esc(q.get("bad", ""))}">
  <h3 class="quiz-question">{esc(q["q"])}</h3>
  <div class="quiz-options">{"".join(opts)}</div>
  <div class="quiz-feedback"></div>
</div>"""
        )
    parts.append(
        f"""
<div class="quiz-actions">
  <button type="button" class="btn" onclick="quizCheck('{esc(qid)}')">检查答案</button>
  <button type="button" class="btn secondary" onclick="quizReset('{esc(qid)}')">重来</button>
</div>
</div>"""
    )
    return "\n".join(parts)


def render_course(
    slug: str,
    title: str,
    pill: str,
    accent: str,
    intro: str,
    modules: list[dict[str, Any]],
) -> str:
    module_ids = [m["id"] for m in modules]
    css = COMMON_CSS.replace("#D94F30", accent).replace("rgba(217, 79, 48", "rgba(217, 79, 48")  # keep rgba for glow or adjust
    # simple accent replace for root --color-accent
    css = css.replace("--color-accent: #D94F30;", f"--color-accent: {accent};")
    dots = "".join(
        f'<button type="button" class="nav-dot" data-target="{esc(mid)}" aria-label="第{i+1}章"></button>'
        for i, mid in enumerate(module_ids)
    )
    bodies = []
    for i, m in enumerate(modules):
        bg = "var(--color-bg)" if i % 2 == 0 else "var(--color-bg-warm)"
        bodies.append(
            f"""
<section class="module" id="{esc(m['id'])}" style="background:{bg}">
  <div class="module-content">
    <header class="module-header animate-in">
      <span class="module-number">{i+1:02d}</span>
      <h1 class="module-title">{esc(m['title'])}</h1>
      <p class="module-subtitle">{esc(m.get('subtitle',''))}</p>
    </header>
    <div class="module-body">
      {m['html']}
    </div>
  </div>
</section>"""
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)} — 交互式导读</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>{css}</style>
</head>
<body>
  <nav class="nav" aria-label="章节导航">
    <div class="progress-bar" role="progressbar" aria-valuenow="0"></div>
    <div class="nav-inner">
      <span class="nav-title">{esc(title)}</span>
      <div class="nav-dots">{dots}</div>
    </div>
  </nav>
  <section class="module" id="intro" style="background:var(--color-bg);min-height:85vh;min-height:85dvh;padding-top:calc(var(--nav-height) + var(--space-12))">
    <div class="module-content">
      <div class="hero-pill">{esc(pill)}</div>
      <h1 class="module-title" style="font-size:var(--text-5xl)">{esc(title)}</h1>
      <p class="lead animate-in">{intro}</p>
      <p style="color:var(--color-text-muted);font-size:var(--text-sm);margin-top:var(--space-8)">向下滚动进入第 1 章 · 键盘方向键也可切换章节</p>
    </div>
  </section>
  {''.join(bodies)}
  <script>{common_js(module_ids)}</script>
</body>
</html>"""


# --- 项目数据：真实代码片段保持仓库原样（pre 内使用 HTML 转义） ---

CODE_DAC = """<span class="code-keyword">app</span> = FastAPI(
    title=<span class="code-string">"Data-Agent Connector"</span>,
    description=<span class="code-string">"孵化器统一数据出口：多源连接、Schema 发现、查询与 NL2SQL 在安全边界内可审计、可限流"</span>,
    version=<span class="code-string">"1.3.0"</span>
)"""

CODE_MINER = """<span class="code-keyword">app</span> = FastAPI(
    title=<span class="code-string">"AI Opportunity Miner"</span>,
    description=<span class="code-string">"AI 商机挖掘系统 - 基于 DeerFlow 2.0 Agent 编排，集成 CB Insights 风格商业情报功能，支持真实数据源接入"</span>,
    version=<span class="code-string">"0.9.0"</span>,
)"""

CODE_CU = """<span class="code-keyword">app</span> = FastAPI(
    title=<span class="code-string">"AI Code Understanding"</span>,
    description=<span class="code-string">"AI 代码理解助手 — 解释代码、模块摘要、语义问答、全局地图、任务引导，助力大仓库开发"</span>,
    version=<span class="code-string">"0.5.0-P5"</span>,
)"""

CODE_RT = """<span class="code-keyword">app</span> = FastAPI(
    title=<span class="code-string">"AI Runtime Optimizer"</span>,
    description=<span class="code-string">"AI 运行态优化器 — 指标与用户行为综合分析、优化建议与代码提案（需评审/CI）"</span>,
    version=<span class="code-string">"2.2.0"</span>,
)"""

CODE_TRAFFIC = """<span class="code-keyword">logger</span>.info(f<span class="code-string">"Starting {settings.APP_NAME} v{settings.APP_VERSION}"</span>)"""

CODE_COMM = """<span class="code-keyword">from</span> api.community <span class="code-keyword">import</span> router <span class="code-keyword">as</span> community_router"""

CODE_EMP = """<span class="code-keyword">from</span> api.employees <span class="code-keyword">import</span> router <span class="code-keyword">as</span> employees_router"""

CODE_HIRE = """<span class="code-string">\"\"\"</span>
AI 雇佣真人平台 — 当 AI 无法独立完成（尤其真实世界交互）时，雇佣真人执行并回传结果。
<span class="code-string">\"\"\"</span>"""

CODE_MATCH = """<span class="code-keyword">app</span> = FastAPI(
    title=<span class="code-string">"Matchmaker Agent"</span>,
    description=<span class="code-string">"AI 红娘匹配系统（带 JWT 认证和 SQLite 持久化）"</span>,
    version=<span class="code-string">"1.0.0"</span>,
)"""

CODE_BUY = """<span class="code-keyword">from</span> api.products <span class="code-keyword">import</span> router <span class="code-keyword">as</span> products_router"""


def main() -> None:
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from incubator_courses_data import PROJECTS  # noqa: WPS433

    for p in PROJECTS:
        out = os.path.join(ROOT, p["folder"], "COURSE.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        html = render_course(
            p["slug"],
            p["title"],
            p["pill"],
            p["accent"],
            p["intro"],
            p["modules"],
        )
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote", out)


if __name__ == "__main__":
    main()
