import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

# We can't replay the message bus since it's in-memory (resets each run)
# But we can show the last GitHub PR, issue, and Slack activity

import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

print("\n" + "="*60)
print("LaunchMind - Last Run Outputs")
print("="*60)

# GitHub Issues
print("\n--- ENGINEER AGENT: GitHub Issues ---")
r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/issues", headers=HEADERS)
for issue in r.json()[:3]:
    print(f"  #{issue['number']} {issue['title']}")
    print(f"  URL: {issue['html_url']}")

# GitHub PRs
print("\n--- ENGINEER AGENT: GitHub Pull Requests ---")
r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/pulls?state=all", headers=HEADERS)
for pr in r.json()[:3]:
    print(f"  #{pr['number']} {pr['title']}")
    print(f"  Branch: {pr['head']['ref']}")
    print(f"  URL: {pr['html_url']}")

# GitHub PR comments (QA agent)
print("\n--- QA AGENT: PR Review Comments ---")
for pr in r.json()[:1]:
    pr_num = pr['number']
    rc = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_num}/comments", headers=HEADERS)
    comments = rc.json()
    if comments:
        for c in comments:
            print(f"  File: {c['path']} (line {c.get('original_line', '?')})")
            print(f"  Comment: {c['body'][:100]}...")
    else:
        print("  No inline comments yet (QA agent didn't finish last run)")

# Landing page content
print("\n--- ENGINEER AGENT: Landing Page (index.html) ---")
r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html",
                 headers=HEADERS, params={"ref": "agent-landing-page"})
if r.status_code == 200:
    import base64
    content = base64.b64decode(r.json()["content"]).decode("utf-8")
    print(f"  File size: {len(content)} characters")
    # Extract title
    import re
    title = re.search(r'<title>(.*?)</title>', content)
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    if title:
        print(f"  Page title: {title.group(1)}")
    if h1:
        print(f"  Main headline: {re.sub('<[^>]+>', '', h1.group(1)).strip()}")
    print(f"  View at: https://github.com/{GITHUB_REPO}/blob/agent-landing-page/index.html")
else:
    print("  Not found (engineer agent may not have completed)")

print("\n" + "="*60)
print("Check your email inbox and Slack #launches for marketing outputs")
print("="*60)
