#!/usr/bin/env python3
"""Build the LeadGenAI blog: blog/posts/*.md -> blog/<slug>/index.html, blog/index.html, sitemap.xml.

Post file format (blog/posts/YYYY-MM-DD-slug.md):
---
title: Post title (under 60 chars works best)
description: Meta description, 120-155 chars
date: 2026-11-19
slug: url-slug
keywords: main keyword, second keyword
---
Markdown body. Supported: ## and ### headings, paragraphs, - and 1. lists,
> quotes, **bold**, *italic*, `code`, [text](url). No raw HTML.
Run: python3 tools/build_blog.py   (from the repo root)
"""
import html, json, os, re, sys, glob, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://leadgenai.io"
MARK = ('<svg viewBox="0 0 48 48" aria-hidden="true"><g fill="#0a0a0a"><circle cx="9" cy="9" r="6.5"/>'
        '<circle cx="9" cy="23.5" r="6.5"/><circle cx="9" cy="38" r="6.5"/><circle cx="23.5" cy="38" r="6.5"/>'
        '<circle cx="38" cy="38" r="6.5"/></g></svg>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230a0a0a'/%3E"
           "%3Cg fill='%23fff'%3E%3Ccircle cx='18' cy='16' r='7'/%3E%3Ccircle cx='18' cy='30' r='7'/%3E%3Ccircle cx='18' cy='44' r='7'/%3E"
           "%3Ccircle cx='32' cy='44' r='7'/%3E%3Ccircle cx='46' cy='44' r='7'/%3E%3C/g%3E%3C/svg%3E")

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", t)
    def link(m):
        url = m.group(2).strip()
        if not re.match(r"^(https?://|/|#|mailto:)", url):
            return m.group(1)
        ext = url.startswith("http") and not url.startswith(SITE)
        rel = ' rel="noopener"' if ext else ""
        return f'<a href="{html.escape(url, quote=True)}"{rel}>{m.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)

def markdown(md):
    out, para, lst, kind = [], [], [], None
    def flush():
        nonlocal para, lst, kind
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
        if lst: out.append(f"<{kind}>" + "".join(f"<li>{inline(i)}</li>" for i in lst) + f"</{kind}>"); lst = []; kind = None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip(): flush(); continue
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush(); lvl = max(2, len(m.group(1)))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if para or kind == "ol": flush()
            kind = "ul"; lst.append(m.group(1)); continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)", line)
        if m:
            if para or kind == "ul": flush()
            kind = "ol"; lst.append(m.group(1)); continue
        if line.startswith(">"):
            flush(); out.append("<blockquote>" + inline(line.lstrip("> ")) + "</blockquote>"); continue
        if lst: lst[-1] += " " + line.strip(); continue
        para.append(line.strip())
    flush()
    return "\n".join(out)

def read_post(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m: sys.exit(f"{path}: missing front matter")
    meta = {}
    for l in m.group(1).splitlines():
        if ":" in l:
            k, v = l.split(":", 1); meta[k.strip()] = v.strip()
    for k in ("title", "description", "date", "slug"):
        if not meta.get(k): sys.exit(f"{path}: front matter needs {k}")
    if not re.match(r"^[a-z0-9-]+$", meta["slug"]): sys.exit(f"{path}: slug must be lowercase letters, digits, hyphens")
    datetime.date.fromisoformat(meta["date"])
    meta["body"] = markdown(m.group(2))
    return meta

def nice(d): return datetime.date.fromisoformat(d).strftime("%B %-d, %Y")

def page(title, desc, canonical, body, extra_head="", og_type="website"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="LeadGenAI">
<meta property="og:image" content="https://leadgenai.io/assets/og-image.png?v=2">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="627">
<meta property="og:image:alt" content="LeadGenAI: We build B2B lead systems">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a0a0a">
<link rel="icon" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/icon-512.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css">
{extra_head}
</head>
<body>
<div class="nav"><div class="in">
  <a class="logo" href="/"><span class="mark">{MARK}</span><span>LeadGen<span class="ai">AI</span></span></a>
  <nav><a href="/#how">How it works</a><a href="/blog/">Blog</a><a class="btn" href="/#audit">Get a free audit</a></nav>
</div></div>
{body}
<footer><div class="in"><span><a href="/">LeadGenAI</a><a href="/blog/">Blog</a><a href="mailto:contact@leadgenai.io">contact@leadgenai.io</a></span><span>© {datetime.date.today().year} Duerr Imports, LLC. LeadGenAI is operated by Duerr Imports, LLC.</span></div></footer>
</body>
</html>
"""

CTA = """<section class="cta"><div class="box">
  <h2>See your market first</h2>
  <p>Get a free pipeline audit: how many companies fit your profile, the signals worth tracking and 25 accounts showing them right now. Delivered within 48 hours.</p>
  <a class="btn" href="/#audit">Get a free audit</a>
</div></section>"""

def main():
    posts = sorted((read_post(p) for p in glob.glob(os.path.join(ROOT, "blog/posts/*.md"))), key=lambda p: p["date"], reverse=True)
    slugs = [p["slug"] for p in posts]
    if len(slugs) != len(set(slugs)): sys.exit("duplicate slug")
    for p in posts:
        url = f"{SITE}/blog/{p['slug']}/"
        ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "description": p["description"],
              "datePublished": p["date"], "dateModified": p["date"], "mainEntityOfPage": url,
              "author": {"@type": "Organization", "name": "LeadGenAI", "url": SITE},
              "publisher": {"@type": "Organization", "name": "LeadGenAI", "url": SITE}}
        if p.get("keywords"): ld["keywords"] = p["keywords"]
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": url}]}
        head = (f'<meta property="article:published_time" content="{p["date"]}">\n'
                f'<script type="application/ld+json">{json.dumps(ld)}</script>\n'
                f'<script type="application/ld+json">{json.dumps(crumbs)}</script>')
        body = f"""<header class="hero"><div class="in"><p class="kicker"><i></i>LeadGenAI blog</p><h1>{html.escape(p['title'])}</h1>
<p>{html.escape(p['description'])}</p><div class="meta">{nice(p['date'])}</div></div></header>
<article>
{p['body']}
</article>
{CTA}"""
        d = os.path.join(ROOT, "blog", p["slug"]); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page(f"{p['title']} | LeadGenAI", p["description"], url, body, head, og_type="article"))
    cards = "\n".join(f'<a class="card" href="/blog/{p["slug"]}/"><small>{nice(p["date"])}</small><h2>{html.escape(p["title"])}</h2><p>{html.escape(p["description"])}</p></a>' for p in posts) \
        or '<p class="empty">The first posts are on their way.</p>'
    body = f"""<header class="hero"><div class="in"><p class="kicker"><i></i>Blog</p><h1>Finding buyers in niche B2B markets</h1>
<p>How to map a small market, read buying signals and reach the people who decide, when ads and generic outreach don’t work.</p></div></header>
<section class="list">
{cards}
</section>"""
    open(os.path.join(ROOT, "blog/index.html"), "w", encoding="utf-8").write(
        page("Blog | LeadGenAI: niche B2B lead systems", "Guides on market mapping, buying signals and direct outreach for niche B2B companies whose buyers ignore ads.", f"{SITE}/blog/", body))
    today = datetime.date.today().isoformat()
    urls = [(f"{SITE}/", today), (f"{SITE}/blog/", posts[0]["date"] if posts else today)] + [(f"{SITE}/blog/{p['slug']}/", p["date"]) for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
         "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(sm)
    print(f"built {len(posts)} posts")

if __name__ == "__main__":
    main()
