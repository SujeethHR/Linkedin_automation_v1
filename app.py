"""
LinkedIn AI Post Studio
Powered by Abacus.AI ChatLLM (RouteLLM API)
============================================
Run:  python app.py
Open: http://localhost:5001

Features:
  - AI trend fetching (DuckDuckGo + RSS + Google Trends + Twitter/X)
  - Post drafting with hashtags
  - Calendar + scheduler (APScheduler auto-publishes)
  - LinkedIn publishing (text + image posts)
  - Post analytics (memberCreatorPostAnalytics)
  - Seen-articles cache (no repeated content)
  - Custom topic search (news + research papers)
"""

import os, json, re, uuid, requests, time
from datetime import datetime, timedelta
from urllib.parse import quote as url_quote
from xml.etree import ElementTree as ET
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

try:
    from ddgs import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

load_dotenv()

import os as _os
_template_folder = _os.environ.get("LINKEDIN_STUDIO_TEMPLATE_FOLDER", "templates")
_data_dir        = _os.environ.get("LINKEDIN_STUDIO_DATA_DIR", ".")
app = Flask(__name__, template_folder=_template_folder)

# ── Config ─────────────────────────────────────────────────────────────────────
ABACUS_API_KEY    = os.getenv("ABACUS_API_KEY",    "")
ABACUS_BASE_URL   = os.getenv("ABACUS_BASE_URL",   "https://routellm.abacus.ai/v1")
ABACUS_MODEL      = os.getenv("ABACUS_MODEL",      "route-llm")
LINKEDIN_API_URL  = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_TOKEN    = os.getenv("LINKEDIN_TOKEN",    "")
LINKEDIN_URN      = os.getenv("LINKEDIN_URN",      "")
SCHEDULE_FILE     = _os.path.join(_data_dir, "schedule.json")
SEEN_FILE         = _os.path.join(_data_dir, "seen_articles.json")

# ── RSS feeds ──────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    # AI & Tech
    "TechCrunch AI":          "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI":           "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MIT Tech Review":        "https://www.technologyreview.com/feed/",
    "Wired AI":               "https://www.wired.com/feed/tag/ai/latest/rss",
    "VentureBeat AI":         "https://venturebeat.com/category/ai/feed/",
    "ArXiv CS.AI":            "https://rss.arxiv.org/rss/cs.AI",
    "ArXiv CS.LG":            "https://rss.arxiv.org/rss/cs.LG",
    # Chemistry & Computational
    "ArXiv Chemistry":        "https://rss.arxiv.org/rss/physics.chem-ph",
    "ArXiv q-bio.BM":         "https://rss.arxiv.org/rss/q-bio.BM",
    "RSC News":               "https://www.rsc.org/news-events/articles/rss/",
    "C&EN News":              "https://cen.acs.org/rss/latest.xml",
    "Nature Chemistry":       "https://www.nature.com/nchem.rss",
    "ChemRxiv":               "https://chemrxiv.org/engage/chemrxiv/rss",
    "J. Chem. Inf. (ACS)":   "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=jcisd8",
    # Pharma & Life Sciences
    "FiercePharma":           "https://www.fiercepharma.com/rss/xml",
    "BioPharma Dive":         "https://www.biopharmadive.com/feeds/news/",
    "STAT News Pharma":       "https://www.statnews.com/feed/",
    "Nature Drug Discovery":  "https://www.nature.com/nrd.rss",
    "Nature Biotech":         "https://www.nature.com/nbt.rss",
    "Drug Discovery Today":   "https://www.sciencedirect.com/journal/drug-discovery-today/rss",
    "FDA News":               "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "EMA News":               "https://www.ema.europa.eu/en/news-events/news/rss",
    "Regulatory Affairs":     "https://www.raps.org/news-and-articles/rss",
    # Patents & Legal
    "IPWatchdog":             "https://ipwatchdog.com/feed/",
    "Patent Docs":            "https://www.patentdocs.org/atom.xml",
    "Managing IP":            "https://www.managingip.com/rss",
    "IP Watch":               "https://www.ip-watch.org/feed/",
    "Law360 IP":              "https://www.law360.com/rss/intellectual_property",
    # ── Cybersecurity ─────────────────────────────────────────────────────────
    "Krebs on Security":      "https://krebsonsecurity.com/feed/",
    "The Hacker News":        "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer":       "https://www.bleepingcomputer.com/feed/",
    "Threatpost":             "https://threatpost.com/feed/",
    "Dark Reading":           "https://www.darkreading.com/rss.xml",
    "SecurityWeek":           "https://feeds.feedburner.com/securityweek",
    "ArXiv CS.CR":            "https://rss.arxiv.org/rss/cs.CR",
    "SANS ISC":               "https://isc.sans.edu/rssfeed_full.xml",
    "Naked Security":         "https://nakedsecurity.sophos.com/feed/",
    # ── Cloud — AWS · Azure · GCP ─────────────────────────────────────────────
    "AWS News":               "https://aws.amazon.com/blogs/aws/feed/",
    "Azure Updates":          "https://azurecomcdn.azureedge.net/en-us/updates/feed/",
    "GCP Blog":               "https://cloudblog.withgoogle.com/rss/",
    "The New Stack":          "https://thenewstack.io/feed/",
    "InfoQ Cloud":            "https://feed.infoq.com/",
    "Cloud Security Alliance":"https://cloudsecurityalliance.org/feed",
    "ArXiv CS.NI":            "https://rss.arxiv.org/rss/cs.NI",
    # ── GRC ───────────────────────────────────────────────────────────────────
    "ISACA News":             "https://www.isaca.org/rss-feeds/isaca-now-blog",
    "IAPP News":              "https://iapp.org/news/rss/",
    "Risk.net":               "https://www.risk.net/rss",
    "Compliance Week":        "https://www.complianceweek.com/rss/news",
    "NIST News":              "https://www.nist.gov/news-events/cybersecurity/rss.xml",
}

CATEGORY_FEEDS = {
    "ai models & releases":       ["TechCrunch AI", "The Verge AI", "VentureBeat AI", "ArXiv CS.AI"],
    "ai tools & products":        ["TechCrunch AI", "VentureBeat AI", "Wired AI"],
    "ai industry news":           ["TechCrunch AI", "MIT Tech Review", "The Verge AI"],
    "ai research papers":         ["ArXiv CS.AI", "ArXiv CS.LG"],
    "ai policy & regulation":     ["MIT Tech Review", "Wired AI", "FDA News", "Regulatory Affairs"],
    "ai startups & funding":      ["TechCrunch AI", "VentureBeat AI", "BioPharma Dive"],
    "prompt engineering":         ["ArXiv CS.AI", "ArXiv CS.LG", "VentureBeat AI"],
    "ai in business":             ["MIT Tech Review", "VentureBeat AI", "Wired AI"],
    "chemistry news":             ["C&EN News", "RSC News", "Nature Chemistry", "ChemRxiv"],
    "chemical research papers":   ["ArXiv Chemistry", "Nature Chemistry", "ChemRxiv", "J. Chem. Inf. (ACS)"],
    "computational chemistry":    ["ArXiv Chemistry", "ArXiv q-bio.BM", "J. Chem. Inf. (ACS)", "ChemRxiv"],
    "chemoinformatics":           ["J. Chem. Inf. (ACS)", "ArXiv q-bio.BM", "ChemRxiv", "ArXiv Chemistry"],
    "drug discovery":             ["Drug Discovery Today", "Nature Drug Discovery", "STAT News Pharma"],
    "pharma news":                ["FiercePharma", "BioPharma Dive", "STAT News Pharma"],
    "pharma research":            ["Nature Biotech", "Nature Drug Discovery", "Drug Discovery Today"],
    "clinical trials":            ["STAT News Pharma", "BioPharma Dive", "FDA News", "FiercePharma"],
    "regulatory & fda":           ["FDA News", "EMA News", "Regulatory Affairs", "FiercePharma"],
    "patents":                    ["IPWatchdog", "Patent Docs", "Managing IP"],
    "ip & intellectual property": ["IPWatchdog", "Managing IP", "IP Watch", "Law360 IP"],
    "legal & compliance":         ["Law360 IP", "IP Watch", "Regulatory Affairs"],
    # ── Cybersecurity ─────────────────────────────────────────────────────────
    "cybersecurity news":          ["Krebs on Security", "The Hacker News", "BleepingComputer", "Dark Reading", "SecurityWeek"],
    "cyber threats & attacks":     ["Krebs on Security", "The Hacker News", "BleepingComputer", "Threatpost", "SANS ISC"],
    "security research":           ["ArXiv CS.CR", "SecurityWeek", "Dark Reading", "Naked Security"],
    "vulnerability & cve":         ["The Hacker News", "BleepingComputer", "SANS ISC", "SecurityWeek"],
    "ai & cybersecurity":          ["ArXiv CS.CR", "ArXiv CS.AI", "Dark Reading", "SecurityWeek"],
    # ── Cloud ─────────────────────────────────────────────────────────────────
    "aws news":                    ["AWS News", "The New Stack", "InfoQ Cloud"],
    "azure news":                  ["Azure Updates", "The New Stack", "InfoQ Cloud"],
    "gcp news":                    ["GCP Blog", "The New Stack", "InfoQ Cloud"],
    "cloud security":              ["Cloud Security Alliance", "Krebs on Security", "Dark Reading", "ArXiv CS.CR"],
    "cloud storage & infra":       ["AWS News", "Azure Updates", "GCP Blog", "The New Stack", "ArXiv CS.NI"],
    "cloud computing":             ["AWS News", "Azure Updates", "GCP Blog", "The New Stack", "InfoQ Cloud"],
    # ── GRC ───────────────────────────────────────────────────────────────────
    "grc news":                    ["ISACA News", "IAPP News", "Compliance Week", "Risk.net"],
    "governance & risk":           ["ISACA News", "Risk.net", "Compliance Week", "NIST News"],
    "data privacy & compliance":   ["IAPP News", "Compliance Week", "Law360 IP", "NIST News"],
    "nist & frameworks":           ["NIST News", "ISACA News", "Cloud Security Alliance"],
}

# ── Seen-articles cache ────────────────────────────────────────────────────────

def load_seen() -> dict:
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE) as f:
            data = json.load(f)
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        return {k: v for k, v in data.items() if v >= cutoff}
    except Exception:
        return {}

def save_seen(seen: dict):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(seen, f, indent=2)
    except Exception as e:
        print(f"[cache] Save error: {e}")

def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()

def mark_seen(titles: list, urls: list):
    seen = load_seen()
    now  = datetime.now().isoformat()
    for t in titles:
        k = title_key(t)
        if k: seen[k] = now
    for u in urls:
        if u: seen[u] = now
    save_seen(seen)

def clear_seen_cache():
    save_seen({})

# ── Schedule persistence ───────────────────────────────────────────────────────

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_schedule(posts):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(posts, f, indent=2)

# ── LinkedIn image upload ──────────────────────────────────────────────────────

def upload_image_to_linkedin(token: str, urn: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple:
    """Upload image to LinkedIn. Returns (asset_urn, error)."""
    li_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    reg_payload = {
        "registerUploadRequest": {
            "owner": urn,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "serviceRelationships": [{"identifier": "urn:li:userGeneratedContent", "relationshipType": "OWNER"}],
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"],
        }
    }
    try:
        r = requests.post("https://api.linkedin.com/v2/assets?action=registerUpload",
                          headers=li_headers, json=reg_payload, timeout=20)
        if not r.ok:
            return "", f"Image register failed {r.status_code}: {r.text[:200]}"
        data       = r.json()["value"]
        upload_url = data["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn  = data["asset"]
    except Exception as e:
        return "", f"Image register error: {e}"

    try:
        r = requests.put(upload_url,
                         headers={"Authorization": f"Bearer {token}", "Content-Type": mime_type},
                         data=image_bytes, timeout=60)
        if r.status_code not in (200, 201):
            return "", f"Image upload failed {r.status_code}: {r.text[:200]}"
        print(f"[image] ✓ Uploaded to LinkedIn — asset: {asset_urn}")
        return asset_urn, ""
    except Exception as e:
        return "", f"Image upload error: {e}"

# ── LinkedIn publish ───────────────────────────────────────────────────────────

def do_publish(token, urn, text, asset_urn: str = "") -> tuple:
    """Publish text or image+text post. Returns (True, post_urn) or (False, error)."""
    if not token: return False, "LinkedIn access token is missing."
    if not urn:   return False, "LinkedIn member URN is missing."
    if not urn.startswith("urn:li:person:"): return False, f"URN format wrong: '{urn}'"
    if not text:  return False, "Post text is empty."

    print(f"[publish] URN: {urn[:30]}... Image: {'yes' if asset_urn else 'no'}")

    if asset_urn:
        payload = {
            "author": urn, "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": asset_urn}],
            }},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
    else:
        payload = {
            "author": urn, "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    try:
        resp = requests.post(LINKEDIN_API_URL, headers=headers, json=payload, timeout=20)
        print(f"[publish] LinkedIn HTTP {resp.status_code}")
        if resp.ok:
            post_urn = resp.headers.get("x-restli-id", "")
            print(f"[publish] ✓ Published — URN: {post_urn}")
            return True, post_urn
        try:
            err  = resp.json()
            msg  = err.get("message") or err.get("serviceErrorCode") or resp.text
        except Exception:
            msg = resp.text
        hint = {
            401: " → Token expired. Regenerate at developer.linkedin.com",
            403: " → Missing w_member_social scope.",
            422: " → Duplicate post or invalid URN.",
            429: " → Rate limited. Wait a few minutes.",
        }.get(resp.status_code, "")
        return False, f"LinkedIn {resp.status_code}: {msg}{hint}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

# ── APScheduler ────────────────────────────────────────────────────────────────

def check_scheduled_posts():
    posts   = load_schedule()
    now     = datetime.now()
    changed = False
    for post in posts:
        if post.get("status") != "scheduled":
            continue
        try:
            due = datetime.fromisoformat(post["scheduled_at"])
        except Exception:
            continue
        if now >= due:
            ok, result = do_publish(post.get("token",""), post.get("urn",""), post.get("text",""))
            post["status"]       = "published" if ok else "failed"
            post["published_at"] = now.isoformat()
            post["post_urn"]     = result if ok else ""
            post["error"]        = "" if ok else result
            changed = True
            print(f"[scheduler] {'✓' if ok else '✗'} {post.get('topic','')[:60]} — {post['status']}")
    if changed:
        save_schedule(posts)

scheduler = BackgroundScheduler()
scheduler.add_job(check_scheduled_posts, "interval", minutes=1, id="publish_check")
scheduler.start()

# ── Abacus ChatLLM ─────────────────────────────────────────────────────────────

def call_chatllm(messages: list, max_tokens: int = 2000) -> str:
    if not ABACUS_API_KEY:
        raise ValueError("ABACUS_API_KEY not set in .env")
    headers = {"Authorization": f"Bearer {ABACUS_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": ABACUS_MODEL, "max_tokens": max_tokens, "messages": messages}
    endpoint = ABACUS_BASE_URL.rstrip("/") + "/chat/completions"
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ── Hashtag generator ──────────────────────────────────────────────────────────

def generate_hashtags(topic: str, post_text: str, count: int = 5) -> list:
    user_msg = (
        "Generate exactly " + str(count) + " relevant LinkedIn hashtags.\n\n"
        "Topic: " + topic + "\nPost excerpt:\n" + post_text[:400] + "\n\n"
        "Rules: start with #, mix 2 broad + 2 niche + 1 trending, "
        "CamelCase multi-word, no duplicates. "
        "Return ONLY hashtags separated by spaces. Nothing else."
    )
    try:
        result = call_chatllm(
            messages=[
                {"role": "system", "content": "You generate concise relevant LinkedIn hashtags."},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=80,
        )
        return [w.strip() for w in result.split() if w.strip().startswith("#")][:count]
    except Exception as e:
        print(f"[hashtags] Error: {e}")
        return []

# ── AI image generation ────────────────────────────────────────────────────────

# ── Web search (DuckDuckGo) ────────────────────────────────────────────────────

def search_ddg(query: str, max_results: int = 8, timelimit: str = "w") -> list:
    if not DDG_AVAILABLE:
        return []
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results, timelimit=timelimit))
    except Exception as e:
        print(f"[ddg] Error: {e}")
        return []

# ── RSS feeds ──────────────────────────────────────────────────────────────────

def fetch_rss(feed_name: str, url: str, max_items: int = 8) -> list:
    results = []
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "LinkedInPostStudio/1.0"})
        if not resp.ok:
            return []
        root = ET.fromstring(resp.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}

        # RSS 2.0
        for item in root.findall(".//item")[:max_items]:
            title   = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
            link    = (item.findtext("link") or "").strip()
            pub     = (item.findtext("pubDate") or "").strip()
            summary = re.sub(r"<[^>]+>", "", summary)[:300]
            if title:
                results.append({"title": title, "summary": summary, "url": link,
                                 "date": pub[:16], "source": feed_name, "type": "rss"})

        # Atom
        if not results:
            for entry in root.findall("atom:entry", ns)[:max_items]:
                title   = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                summary = (entry.findtext("atom:summary", namespaces=ns) or
                           entry.findtext("atom:content", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link    = link_el.get("href","") if link_el is not None else ""
                pub     = (entry.findtext("atom:published", namespaces=ns) or "").strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                if title:
                    results.append({"title": title, "summary": summary, "url": link,
                                     "date": pub[:16], "source": feed_name, "type": "rss"})
    except Exception as e:
        print(f"[rss] {feed_name}: {e}")
    return results


def fetch_selected_rss(feed_names: list, max_per_feed: int = 6) -> list:
    all_items = []
    for name in feed_names:
        url = RSS_FEEDS.get(name)
        if url:
            all_items.extend(fetch_rss(name, url, max_per_feed))
    return all_items

# ── Google Trends ──────────────────────────────────────────────────────────────

def fetch_google_trends(keywords: list, geo: str = "IN") -> list:
    if not PYTRENDS_AVAILABLE:
        return []
    results = []
    try:
        pt = TrendReq(hl="en-US", tz=330, timeout=(10, 25), retries=2, backoff_factor=0.5)
        try:
            trending = pt.realtime_trending_searches(pn=geo)
            if trending is not None and not trending.empty:
                for _, row in trending.head(10).iterrows():
                    title = str(row.get("title","") or row.iloc[0])
                    if title and len(title) > 3:
                        results.append({
                            "title": title,
                            "summary": f"Trending on Google in {'India' if geo=='IN' else 'US' if geo=='US' else 'worldwide'}.",
                            "url": f"https://trends.google.com/trends/explore?q={url_quote(title)}",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "Google Trends", "type": "trend",
                        })
        except Exception as e:
            print(f"[trends] Realtime error: {e}")
        if keywords:
            try:
                pt.build_payload(keywords[:3], timeframe="now 7-d", geo=geo)
                related = pt.related_queries()
                for kw in keywords[:3]:
                    if kw in related and related[kw].get("rising") is not None:
                        df = related[kw]["rising"]
                        if df is not None and not df.empty:
                            for _, row in df.head(5).iterrows():
                                q = str(row.get("query",""))
                                if q:
                                    results.append({
                                        "title": f"Rising: {q}",
                                        "summary": f"Rising Google search related to '{kw}'.",
                                        "url": f"https://trends.google.com/trends/explore?q={url_quote(q)}",
                                        "date": datetime.now().strftime("%Y-%m-%d"),
                                        "source": "Google Trends", "type": "trend",
                                    })
            except Exception as e:
                print(f"[trends] Related queries error: {e}")
    except Exception as e:
        print(f"[trends] Error: {e}")
    return results

# ── Twitter/X via DuckDuckGo ───────────────────────────────────────────────────

def fetch_twitter_mentions(topic: str, max_results: int = 8) -> list:
    results  = []
    seen_urls = set()
    for q in [f"site:x.com {topic} AI", f"site:twitter.com {topic}"]:
        for r in search_ddg(q, max_results=max_results, timelimit="w"):
            url   = r.get("href","")
            title = r.get("title","").strip()
            if not title or url in seen_urls: continue
            if "x.com" not in url and "twitter.com" not in url: continue
            seen_urls.add(url)
            results.append({"title": title, "summary": r.get("body","")[:300],
                             "url": url, "date": r.get("date",""),
                             "source": "Twitter/X", "type": "twitter"})
    return results

# ── Trend context builder ──────────────────────────────────────────────────────

def build_trend_context(niche: str, categories: list, count: int,
                        use_rss: bool = True, use_trends: bool = True,
                        use_twitter: bool = False) -> str:
    today    = datetime.now()
    month_yr = today.strftime("%B %Y")
    year     = today.strftime("%Y")
    cats     = categories[:5] if categories else ["AI news"]
    seen     = load_seen()
    all_items    = []
    session_keys = set()

    # DDG queries
    ddg_queries = []
    for cat in cats[:4]:
        ddg_queries.append(f"{cat} news {month_yr}")
        ddg_queries.append(f"{cat} latest research {year}")
    ddg_queries.append(f"{niche} latest developments {month_yr}")
    domain_boosters = {
        "chem":   [f"chemistry research breakthrough {month_yr}"],
        "pharma": [f"pharma drug approval {month_yr}"],
        "patent": [f"patent filing IP ruling {month_yr}"],
        "legal":  [f"FDA approval regulatory update {month_yr}"],
        "ai":     [f"artificial intelligence announcement {year}", f"AI model release {month_yr}"],
        "cyber":  [f"cybersecurity breach vulnerability {month_yr}", f"ransomware malware attack {year}"],
        "aws":    [f"AWS Amazon Web Services announcement {month_yr}"],
        "azure":  [f"Microsoft Azure cloud update {month_yr}"],
        "gcp":    [f"Google Cloud Platform GCP release {month_yr}"],
        "cloud":  [f"cloud security incident data breach {month_yr}", f"cloud infrastructure news {year}"],
        "grc":    [f"governance risk compliance regulation {month_yr}", f"NIST framework ISO 27001 update {year}"],
    }
    for keyword, boosters in domain_boosters.items():
        if any(keyword in cat.lower() for cat in cats) or keyword in niche.lower():
            ddg_queries.extend(boosters)
    ddg_queries = list(dict.fromkeys(ddg_queries))

    print(f"[search] DDG: {len(ddg_queries)} queries (past 7 days)...")
    for q in ddg_queries:
        hits = search_ddg(q, max_results=6, timelimit="w")
        if not hits:
            hits = search_ddg(q, max_results=6, timelimit="m")
        for r in hits:
            t    = (r.get("title") or "").strip()
            body = (r.get("body")  or "").strip()
            href = (r.get("href")  or "").strip()
            date = (r.get("date")  or "").strip()
            if not t: continue
            tk = title_key(t)
            if tk in seen or href in seen or tk in session_keys: continue
            session_keys.add(tk)
            all_items.append({"title": t, "summary": body[:250], "url": href,
                               "date": date, "source": "Web", "type": "news"})

    # RSS feeds
    if use_rss:
        feeds_to_use = set()
        for cat in cats:
            cl = cat.lower().strip()
            if cl in CATEGORY_FEEDS:
                feeds_to_use.update(CATEGORY_FEEDS[cl])
            else:
                for key, feeds in CATEGORY_FEEDS.items():
                    if any(w in cl for w in key.split()) or any(w in key for w in cl.split()):
                        feeds_to_use.update(feeds)
                        break
        if not feeds_to_use:
            feeds_to_use = {"TechCrunch AI", "The Verge AI", "VentureBeat AI"}
        for r in fetch_selected_rss(list(feeds_to_use), max_per_feed=5):
            tk = title_key(r["title"])
            if tk in seen or r["url"] in seen or tk in session_keys: continue
            session_keys.add(tk)
            all_items.append(r)

    # Google Trends
    if use_trends and PYTRENDS_AVAILABLE:
        trend_kws = [c.replace("AI ","").replace(" & releases","").strip() for c in cats[:2]]
        trend_kws.append(niche.split()[0] if niche else "AI")
        for r in fetch_google_trends(trend_kws[:3]):
            tk = title_key(r["title"])
            if tk in session_keys: continue
            session_keys.add(tk)
            all_items.append(r)

    # Twitter/X
    if use_twitter:
        for r in fetch_twitter_mentions(niche or "AI", max_results=6):
            tk = title_key(r["title"])
            if tk in seen or r.get("url","") in seen or tk in session_keys: continue
            session_keys.add(tk)
            all_items.append(r)

    print(f"[search] {len(all_items)} fresh items")
    if all_items:
        mark_seen([i["title"] for i in all_items], [i.get("url","") for i in all_items if i.get("url")])

    if not all_items:
        return "All recent results were already shown. Click 'Clear seen cache' to reset."

    lines = []
    for item in all_items[:50]:
        src   = item.get("source","Web")
        t     = item.get("title","")
        summ  = item.get("summary","")
        url   = item.get("url","")
        date  = item.get("date","")
        dtag  = f" [{date[:10]}]" if date else ""
        badge = {"twitter":"[Twitter/X]","trend":"[Google Trends]"}.get(item.get("type",""), f"[{src}]")
        lines.append(f"- {badge} {t}{dtag}: {summ} ({url})")
    return "\n".join(lines)

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/key-check")
def key_check():
    return jsonify({"ok": bool(ABACUS_API_KEY)})

@app.route("/api/li-prefill")
def li_prefill():
    return jsonify({"token": LINKEDIN_TOKEN, "urn": LINKEDIN_URN})

@app.route("/api/sources-status")
def sources_status():
    return jsonify({"ddg": DDG_AVAILABLE, "trends": PYTRENDS_AVAILABLE,
                    "ddg": DDG_AVAILABLE, "trends": PYTRENDS_AVAILABLE})

# Seen cache
@app.route("/api/seen-cache-info")
def seen_cache_info():
    return jsonify({"ok": True, "count": len(load_seen())})

@app.route("/api/clear-seen-cache", methods=["POST"])
def clear_cache_route():
    clear_seen_cache()
    return jsonify({"ok": True, "message": "Seen cache cleared."})

# Fetch trends
@app.route("/api/fetch-trends", methods=["POST"])
def fetch_trends():
    body       = request.json or {}
    niche      = body.get("niche", "AI tools and technology")
    categories = body.get("categories", ["AI models & releases", "AI tools & products"])
    count      = int(body.get("count", 8))
    use_rss    = body.get("use_rss", True)
    use_trends = body.get("use_trends", False)
    use_twitter = body.get("use_twitter", False)

    date_str = datetime.now().strftime("%B %d, %Y")
    context  = build_trend_context(niche, categories, count,
                                   use_rss=use_rss, use_trends=use_trends, use_twitter=use_twitter)
    cats_str = ", ".join(categories) or "AI news"

    system_msg = (
        "You are a research assistant and LinkedIn content strategist. "
        "You ONLY surface news from the past 7 days. "
        "Today is " + date_str + "."
    )
    fmt = ('[{"title":"headline","summary":"Two sentences.","why":"One sentence.","source":"Name","heat":"hot"}]')
    user_msg = (
        "Today is " + date_str + ". Based ONLY on these search results (past 7 days), "
        "identify " + str(count) + " recent AI trends for: " + niche + "\n\n"
        "Categories: " + cats_str + "\n\n"
        "STRICT: only stories from the results, no old news from training data.\n\n"
        "Live results:\n" + context + "\n\n"
        "Return ONLY a JSON array. Format: " + fmt + "\n"
        "heat: hot/rising/new. Return fewer items if less fresh content exists."
    )
    try:
        result = call_chatllm(
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user",   "content": user_msg}],
            max_tokens=3000,
        )
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:].strip()
        trends = json.loads(result)
        return jsonify({"ok": True, "trends": trends})
    except json.JSONDecodeError:
        m = re.search(r"\[.*?\]", result, re.DOTALL)
        if m:
            try: return jsonify({"ok": True, "trends": json.loads(m.group())})
            except Exception: pass
        return jsonify({"ok": False, "error": "Could not parse trends.", "raw": result}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Draft post
@app.route("/api/draft-post", methods=["POST"])
def draft_post():
    body    = request.json or {}
    topic   = body.get("topic", "")
    summary = body.get("summary", "")
    why     = body.get("why", "")
    tone    = body.get("tone", "Conversational & authentic")
    length  = body.get("length", "medium")
    lg      = {"short":"under 300 characters","medium":"300 to 800 characters",
               "long":"800 to 1500 characters"}.get(length,"300 to 800 characters")
    user_msg = (
        "Write a LinkedIn post about this AI trend.\n\nTrend: " + topic +
        "\nContext: " + summary + "\nWhy it matters: " + why +
        "\nTone: " + tone + "\nTarget length: " + lg + "\n\n"
        "Rules: first person, no hashtags, scroll-stopping first line, "
        "genuine not promotional, short paragraphs, end with question or CTA.\n"
        "Return ONLY the post text."
    )
    try:
        text = call_chatllm(
            messages=[
                {"role": "system", "content": "You are a LinkedIn ghostwriter for tech personal brands."},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=1500,
        ).strip()
        hashtags = generate_hashtags(topic, text)
        return jsonify({"ok": True, "text": text, "hashtags": hashtags})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Custom topic search
@app.route("/api/search-topic", methods=["POST"])
def search_topic():
    body        = request.json or {}
    topic       = body.get("topic","").strip()
    source_type = body.get("source_type","all")
    max_results = int(body.get("max_results", 12))
    if not topic:
        return jsonify({"ok": False, "error": "Topic is required."}), 400

    today    = datetime.now()
    month_yr = today.strftime("%B %Y")
    year     = today.strftime("%Y")
    results  = []
    seen_titles = set()

    def add(item):
        k = title_key(item.get("title",""))
        if k and k not in seen_titles:
            seen_titles.add(k)
            results.append({**item, "selected": False})

    if source_type in ("all","news"):
        for q in [f"{topic} {month_yr}", f"{topic} news {year}", f"{topic} update {month_yr}"]:
            for r in search_ddg(q, max_results=6, timelimit="m"):
                t = (r.get("title") or "").strip()
                if t: add({"title":t,"summary":(r.get("body",""))[:300],
                            "url":r.get("href",""),"date":r.get("date",""),"type":"news"})

    if source_type in ("all","research"):
        for q in [f"arxiv {topic} {year}", f"site:arxiv.org {topic}",
                  f"{topic} research paper {month_yr}"]:
            for r in search_ddg(q, max_results=5, timelimit="m"):
                t = (r.get("title") or "").strip()
                if t: add({"title":t,"summary":(r.get("body",""))[:300],
                            "url":r.get("href",""),"date":r.get("date",""),"type":"research"})
        for feed_name in ["ArXiv CS.AI","ArXiv CS.LG","ArXiv Chemistry","ArXiv q-bio.BM"]:
            for r in fetch_rss(feed_name, RSS_FEEDS[feed_name], max_items=8):
                if topic.lower() in r["title"].lower() or topic.lower() in r["summary"].lower():
                    add({**r, "type":"research"})

    return jsonify({"ok": True, "results": results[:max_results], "topic": topic})

# Draft from custom topic
@app.route("/api/draft-from-topic", methods=["POST"])
def draft_from_topic():
    body     = request.json or {}
    topic    = body.get("topic","").strip()
    selected = body.get("selected",[])
    tone     = body.get("tone","Conversational & authentic")
    length   = body.get("length","medium")
    angle    = body.get("angle","")
    if not topic:
        return jsonify({"ok": False, "error": "Topic is required."}), 400
    lg = {"short":"under 300 characters","medium":"300 to 800 characters",
          "long":"800 to 1500 characters"}.get(length,"300 to 800 characters")
    sources_block = ""
    for i, s in enumerate(selected[:8], 1):
        lbl = {"research":"Research paper","twitter":"Tweet","trend":"Google Trend"}.get(s.get("type",""),"Article")
        sources_block += (str(i)+". ["+lbl+"] "+s.get("title","")
            +(" ("+s.get("date","")+")") if s.get("date") else ""
            +"\n   "+s.get("summary","")[:200]
            +("\n   Source: "+s.get("url","") if s.get("url") else "")
            +"\n\n")
    if not sources_block:
        sources_block = "(No sources — use general knowledge about: " + topic + ")"
    user_msg = (
        "Write a LinkedIn post about: " + topic + "\nTone: " + tone +
        "\nTarget length: " + lg +
        ("\nCustom angle: " + angle + "\n" if angle else "") +
        "\nSource material:\n" + sources_block +
        "\nRules: first person, no hashtags, scroll-stopping hook, "
        "reference specific source details, short paragraphs, end with question or CTA.\n"
        "Return ONLY the post text."
    )
    try:
        text = call_chatllm(
            messages=[
                {"role": "system", "content": "You are a LinkedIn ghostwriter for tech personal brands."},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=1500,
        ).strip()
        hashtags = generate_hashtags(topic, text)
        return jsonify({"ok": True, "text": text, "hashtags": hashtags})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Image upload to LinkedIn
@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    token = request.form.get("token","").strip() or LINKEDIN_TOKEN
    urn   = request.form.get("urn","").strip()   or LINKEDIN_URN
    if not token: return jsonify({"ok": False, "error": "LinkedIn token required."}), 400
    if not urn:   return jsonify({"ok": False, "error": "LinkedIn URN required."}), 400
    if "image" not in request.files:
        return jsonify({"ok": False, "error": "No image file provided."}), 400
    file      = request.files["image"]
    mime_type = file.content_type or "image/jpeg"
    img_bytes = file.read()
    if len(img_bytes) > 10 * 1024 * 1024:
        return jsonify({"ok": False, "error": "Image too large. Max 10MB."}), 400
    asset_urn, err = upload_image_to_linkedin(token, urn, img_bytes, mime_type)
    if asset_urn:
        return jsonify({"ok": True, "asset_urn": asset_urn, "filename": file.filename})
    return jsonify({"ok": False, "error": err}), 400

# Publish
@app.route("/api/publish", methods=["POST"])
def publish():
    body      = request.json or {}
    token     = body.get("token","").strip()     or LINKEDIN_TOKEN
    urn       = body.get("urn","").strip()       or LINKEDIN_URN
    text      = body.get("text","").strip()
    asset_urn = body.get("asset_urn","").strip()
    if not token: return jsonify({"ok": False, "error": "LinkedIn access token required."}), 400
    if not urn:   return jsonify({"ok": False, "error": "LinkedIn member URN required."}), 400
    if not text:  return jsonify({"ok": False, "error": "Post text is empty."}), 400

    already = any(p.get("status") == "published" and p.get("text","").strip() == text
                  for p in load_schedule())
    if already:
        return jsonify({"ok": True, "message": "Already published by scheduler.", "skipped": True})

    ok, result = do_publish(token, urn, text, asset_urn)
    if ok:
        posts = load_schedule()
        for p in posts:
            if p.get("text","").strip() == text and not p.get("post_urn"):
                p["post_urn"] = result
        save_schedule(posts)
        return jsonify({"ok": True, "message": "Published!", "post_urn": result, "skipped": False})
    return jsonify({"ok": False, "error": result}), 400

# Debug publish
@app.route("/api/debug-publish", methods=["POST"])
def debug_publish():
    body   = request.json or {}
    token  = body.get("token","").strip() or LINKEDIN_TOKEN
    urn    = body.get("urn","").strip()   or LINKEDIN_URN
    report = {"token_present": bool(token), "urn_present": bool(urn), "checks": []}

    if not token:
        report["checks"].append({"step":"token","ok":False,"msg":"No token."})
        return jsonify(report)
    if not urn:
        report["checks"].append({"step":"urn","ok":False,"msg":"No URN."})
        return jsonify(report)
    if not urn.startswith("urn:li:person:"):
        report["checks"].append({"step":"urn_format","ok":False,
            "msg":f"URN format wrong: '{urn}'. Must be urn:li:person:XXXX"})
        return jsonify(report)
    report["checks"].append({"step":"urn_format","ok":True,"msg":f"URN OK: {urn}"})

    try:
        r = requests.get("https://api.linkedin.com/v2/userinfo",
                         headers={"Authorization":f"Bearer {token}"}, timeout=10)
        if r.ok:
            info = r.json()
            sub  = info.get("sub","")
            report["checks"].append({"step":"token_valid","ok":True,
                "msg":f"Token valid. Logged in as: {info.get('name','?')} ({info.get('email','')})"})
            expected = f"urn:li:person:{sub}"
            if urn == expected:
                report["checks"].append({"step":"urn_match","ok":True,"msg":"URN matches token."})
            else:
                report["checks"].append({"step":"urn_match","ok":False,
                    "msg":f"URN mismatch. Your URN: '{urn}' but token belongs to '{expected}'."})
                return jsonify(report)
        elif r.status_code == 401:
            report["checks"].append({"step":"token_valid","ok":False,
                "msg":"Token expired (401). Regenerate at developer.linkedin.com"})
            return jsonify(report)
        else:
            report["checks"].append({"step":"token_valid","ok":False,
                "msg":f"Unexpected {r.status_code}: {r.text[:200]}"})
            return jsonify(report)
    except Exception as e:
        report["checks"].append({"step":"token_valid","ok":False,"msg":f"Network error: {e}"})
        return jsonify(report)

    try:
        r = requests.post(LINKEDIN_API_URL,
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json",
                     "X-Restli-Protocol-Version":"2.0.0"},
            json={"author":urn,"lifecycleState":"PUBLISHED",
                  "specificContent":{"com.linkedin.ugc.ShareContent":{
                      "shareCommentary":{"text":"API test — safe to delete."},
                      "shareMediaCategory":"NONE"}},
                  "visibility":{"com.linkedin.ugc.MemberNetworkVisibility":"PUBLIC"}},
            timeout=20)
        if r.ok:
            report["checks"].append({"step":"test_publish","ok":True,
                "msg":"Test post published! Everything works. Delete the test post from LinkedIn."})
        else:
            try: msg = r.json().get("message", r.text)
            except Exception: msg = r.text
            report["checks"].append({"step":"test_publish","ok":False,
                "msg":f"Publish failed {r.status_code}: {msg}"})
    except Exception as e:
        report["checks"].append({"step":"test_publish","ok":False,"msg":f"Network error: {e}"})
    return jsonify(report)

# Analytics
@app.route("/api/post-analytics", methods=["POST"])
def post_analytics():
    body     = request.json or {}
    token    = body.get("token","").strip() or LINKEDIN_TOKEN
    post_urn = body.get("post_urn","").strip()
    if not token:    return jsonify({"ok":False,"error":"Token required."}), 400
    if not post_urn: return jsonify({"ok":False,"error":"Post URN required."}), 400

    encoded = url_quote(post_urn, safe="")
    headers = {"Authorization":f"Bearer {token}","X-Restli-Protocol-Version":"2.0.0","LinkedIn-Version":"202501"}
    url = (f"https://api.linkedin.com/rest/memberCreatorPostAnalytics"
           f"?q=entity&entity={encoded}"
           f"&timeIntervals=(timeRange:(start:{int((datetime.now().timestamp()-86400*30)*1000)},"
           f"end:{int(datetime.now().timestamp()*1000)}),timeGranularityType:MONTH)")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.ok:
            totals = {"impressions":0,"clicks":0,"likes":0,"comments":0,"shares":0,"engagement_rate":0}
            for el in resp.json().get("elements",[]):
                s = el.get("totalShareStatistics",{})
                totals["impressions"] += s.get("impressionCount",0)
                totals["clicks"]      += s.get("clickCount",0)
                totals["likes"]       += s.get("likeCount",0)
                totals["comments"]    += s.get("commentCount",0)
                totals["shares"]      += s.get("shareCount",0)
            if totals["impressions"] > 0:
                eng = totals["likes"]+totals["comments"]+totals["shares"]+totals["clicks"]
                totals["engagement_rate"] = round((eng/totals["impressions"])*100, 2)
            return jsonify({"ok":True,"stats":totals,"post_urn":post_urn})
        elif resp.status_code == 403:
            return jsonify({"ok":False,"error":"Access denied. Add r_member_social scope to your token."}), 403
        else:
            try: msg = resp.json().get("message", resp.text)
            except Exception: msg = resp.text
            return jsonify({"ok":False,"error":f"LinkedIn {resp.status_code}: {msg}"}), 400
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 500

@app.route("/api/all-post-analytics", methods=["POST"])
def all_post_analytics():
    body  = request.json or {}
    token = body.get("token","").strip() or LINKEDIN_TOKEN
    if not token: return jsonify({"ok":False,"error":"Token required."}), 400
    published = [p for p in load_schedule() if p.get("status") == "published"]
    if not published:
        return jsonify({"ok":True,"results":[],"message":"No published posts found."})
    headers = {"Authorization":f"Bearer {token}","X-Restli-Protocol-Version":"2.0.0","LinkedIn-Version":"202501"}
    results = []
    for p in published:
        post_urn = p.get("post_urn","")
        if not post_urn:
            results.append({"id":p.get("id"),"topic":p.get("topic"),"published_at":p.get("published_at"),
                             "stats":None,"error":"No post URN stored."})
            continue
        encoded = url_quote(post_urn, safe="")
        url = (f"https://api.linkedin.com/rest/memberCreatorPostAnalytics"
               f"?q=entity&entity={encoded}"
               f"&timeIntervals=(timeRange:(start:{int((datetime.now().timestamp()-86400*30)*1000)},"
               f"end:{int(datetime.now().timestamp()*1000)}),timeGranularityType:MONTH)")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.ok:
                totals = {"impressions":0,"clicks":0,"likes":0,"comments":0,"shares":0,"engagement_rate":0}
                for el in resp.json().get("elements",[]):
                    s = el.get("totalShareStatistics",{})
                    totals["impressions"] += s.get("impressionCount",0)
                    totals["clicks"]      += s.get("clickCount",0)
                    totals["likes"]       += s.get("likeCount",0)
                    totals["comments"]    += s.get("commentCount",0)
                    totals["shares"]      += s.get("shareCount",0)
                if totals["impressions"] > 0:
                    eng = totals["likes"]+totals["comments"]+totals["shares"]+totals["clicks"]
                    totals["engagement_rate"] = round((eng/totals["impressions"])*100, 2)
                results.append({"id":p.get("id"),"topic":p.get("topic"),"published_at":p.get("published_at"),
                                 "post_urn":post_urn,"stats":totals,"error":None})
            else:
                results.append({"id":p.get("id"),"topic":p.get("topic"),"published_at":p.get("published_at"),
                                 "post_urn":post_urn,"stats":None,"error":f"HTTP {resp.status_code}"})
        except Exception as e:
            results.append({"id":p.get("id"),"topic":p.get("topic"),"published_at":p.get("published_at"),
                             "post_urn":post_urn,"stats":None,"error":str(e)})
        time.sleep(0.3)
    return jsonify({"ok":True,"results":results})

# Schedule routes
@app.route("/api/schedule-post", methods=["POST"])
def schedule_post():
    body         = request.json or {}
    token        = body.get("token","").strip() or LINKEDIN_TOKEN
    urn          = body.get("urn","").strip()   or LINKEDIN_URN
    text         = body.get("text","").strip()
    topic        = body.get("topic","")
    scheduled_at = body.get("scheduled_at","")
    if not token:        return jsonify({"ok":False,"error":"Token required."}), 400
    if not urn:          return jsonify({"ok":False,"error":"URN required."}), 400
    if not text:         return jsonify({"ok":False,"error":"Post text empty."}), 400
    if not scheduled_at: return jsonify({"ok":False,"error":"Scheduled time required."}), 400
    try: datetime.fromisoformat(scheduled_at)
    except ValueError: return jsonify({"ok":False,"error":"Invalid date/time."}), 400
    posts = load_schedule()
    entry = {"id":str(uuid.uuid4()),"topic":topic,"text":text,"token":token,"urn":urn,
             "scheduled_at":scheduled_at,"status":"scheduled","created_at":datetime.now().isoformat(),
             "published_at":None,"post_urn":None,"error":None}
    posts.append(entry)
    save_schedule(posts)
    return jsonify({"ok":True,"id":entry["id"],"message":f"Scheduled for {scheduled_at}"})

@app.route("/api/get-schedule")
def get_schedule():
    posts = load_schedule()
    posts.sort(key=lambda p: p.get("scheduled_at",""))
    return jsonify({"ok":True,"posts":posts})

@app.route("/api/delete-scheduled/<post_id>", methods=["DELETE"])
def delete_scheduled(post_id):
    save_schedule([p for p in load_schedule() if p.get("id") != post_id])
    return jsonify({"ok":True})

@app.route("/api/publish-now/<post_id>", methods=["POST"])
def publish_now(post_id):
    posts  = load_schedule()
    target = next((p for p in posts if p.get("id") == post_id), None)
    if not target: return jsonify({"ok":False,"error":"Post not found."}), 404
    ok, result = do_publish(target.get("token",""), target.get("urn",""), target.get("text",""))
    target["status"]       = "published" if ok else "failed"
    target["published_at"] = datetime.now().isoformat()
    target["post_urn"]     = result if ok else ""
    target["error"]        = "" if ok else result
    save_schedule(posts)
    if ok: return jsonify({"ok":True,"message":"Published!"})
    return jsonify({"ok":False,"error":result}), 400

@app.route("/api/reschedule/<post_id>", methods=["POST"])
def reschedule(post_id):
    body     = request.json or {}
    new_time = body.get("scheduled_at","")
    try: datetime.fromisoformat(new_time)
    except ValueError: return jsonify({"ok":False,"error":"Invalid date/time."}), 400
    posts = load_schedule()
    for p in posts:
        if p.get("id") == post_id:
            p["scheduled_at"] = new_time
            p["status"]       = "scheduled"
            p["error"]        = None
            break
    save_schedule(posts)
    return jsonify({"ok":True})

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀  LinkedIn AI Post Studio")
    print(f"   Model  : {ABACUS_MODEL}")
    print(f"   API    : {ABACUS_BASE_URL}")
    print("   Open   →  http://localhost:5001\n")
    if not ABACUS_API_KEY:
        print("⚠️   ABACUS_API_KEY not set — add to .env and restart.\n")
    try:
        app.run(debug=False, port=5001, use_reloader=False)
    finally:
        scheduler.shutdown()
