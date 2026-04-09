import base64
import json
import os
import requests
from google import genai
from message_bus import bus
from llm_helper import call_llm


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
BRANCH_NAME = "agent-landing-page"


class EngineerAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.name = "engineer"

    def _call_llm(self, prompt):
        return call_llm(self.client, prompt, "ENGINEER AGENT")

    def _get_main_sha(self):
        # Use branches API which is more reliable than git/refs
        url = f"https://api.github.com/repos/{GITHUB_REPO}/branches/main"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()["commit"]["sha"]

    def _create_branch(self, sha):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs"
        # Delete branch if it already exists
        del_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{BRANCH_NAME}"
        requests.delete(del_url, headers=HEADERS)

        r = requests.post(url, headers=HEADERS, json={
            "ref": f"refs/heads/{BRANCH_NAME}",
            "sha": sha
        })
        if r.status_code not in (200, 201):
            print(f"[ENGINEER] Branch creation response: {r.status_code} {r.text}")
        return r.status_code in (200, 201)

    def _commit_file(self, html_content):
        encoded = base64.b64encode(html_content.encode()).decode()
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html"

        # Check if file already exists on branch
        existing = requests.get(url, headers=HEADERS, params={"ref": BRANCH_NAME})
        payload = {
            "message": "Add landing page [EngineerAgent]",
            "content": encoded,
            "branch": BRANCH_NAME,
            "author": {
                "name": "EngineerAgent",
                "email": "agent@launchmind.ai"
            }
        }
        if existing.status_code == 200:
            payload["sha"] = existing.json()["sha"]

        r = requests.put(url, headers=HEADERS, json=payload)
        r.raise_for_status()
        return r.json()

    def _create_issue(self, title, body):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        r = requests.post(url, headers=HEADERS, json={"title": title, "body": body})
        r.raise_for_status()
        return r.json()["html_url"]

    def _open_pr(self, title, body):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
        # Check if PR already exists
        existing = requests.get(url, headers=HEADERS, params={
            "head": f"{GITHUB_REPO.split('/')[0]}:{BRANCH_NAME}",
            "state": "open"
        })
        if existing.status_code == 200 and existing.json():
            return existing.json()[0]["html_url"]

        r = requests.post(url, headers=HEADERS, json={
            "title": title,
            "body": body,
            "head": BRANCH_NAME,
            "base": "main"
        })
        r.raise_for_status()
        return r.json()["html_url"]

    def run(self, task_message):
        print("\n[ENGINEER AGENT] Received product spec. Generating landing page...")

        spec = task_message["payload"]["product_spec"]

        features_text = "\n".join([
            f"- {f['name']}: {f['description']}" for f in spec["features"]
        ])
        personas_text = ", ".join([p["name"] for p in spec["personas"]])

        html_prompt = f"""
You are a frontend developer. Generate a complete, beautiful, modern HTML landing page for this startup.

Startup Name: HisaabPro
Tagline: Your WhatsApp-powered business ledger
Value Proposition: {spec['value_proposition']}
Target Users: {personas_text}
Core Features:
{features_text}

Requirements:
- Single HTML file with embedded CSS (no external dependencies)
- Modern design with a clean color scheme (use greens and whites, WhatsApp-inspired)
- Use the brand name "HisaabPro" prominently in the header/navbar and hero section
- Sections: Hero (headline + subheadline + CTA button), Features (all 5 features as cards), How It Works (3 steps), Footer
- Headline must reflect the value proposition
- CTA button says "Start Free on WhatsApp"
- Mobile responsive using CSS flexbox/grid
- Professional and polished — this is a real landing page
- All text must be in English only

Return ONLY the complete HTML code, nothing else. Start with <!DOCTYPE html>.
"""
        html_content = self._call_llm(html_prompt)
        html_content = html_content.strip()
        if html_content.startswith("```"):
            lines = html_content.split("\n")
            html_content = "\n".join(lines[1:-1])

        print("[ENGINEER AGENT] HTML generated. Pushing to GitHub...")

        try:
            sha = self._get_main_sha()
            self._create_branch(sha)
            self._commit_file(html_content)

            issue_body_prompt = f"""
Write a GitHub issue description for the initial landing page of a startup called "HisaabPro" -
a WhatsApp-based sales tracker for Pakistani shopkeepers.
Value proposition: {spec['value_proposition']}
Keep it under 150 words, professional, mention the tech stack (pure HTML/CSS).
"""
            issue_body = self._call_llm(issue_body_prompt)

            pr_body_prompt = f"""
Write a GitHub pull request description for adding the initial landing page of "HisaabPro"
- a WhatsApp sales tracker for Pakistani shopkeepers.
Value proposition: {spec['value_proposition']}
Mention: landing page created by EngineerAgent, features included, responsive design.
Keep it under 200 words.
"""
            pr_body = self._call_llm(pr_body_prompt)

            issue_url = self._create_issue("Initial landing page", issue_body)
            pr_url = self._open_pr("Initial landing page", pr_body)

            print(f"[ENGINEER AGENT] GitHub Issue: {issue_url}")
            print(f"[ENGINEER AGENT] GitHub PR:    {pr_url}")

            bus.send(
                from_agent="engineer",
                to_agent="ceo",
                message_type="result",
                payload={
                    "status": "success",
                    "pr_url": pr_url,
                    "issue_url": issue_url,
                    "html_content": html_content
                },
                parent_message_id=task_message["message_id"]
            )
            return pr_url, issue_url, html_content

        except Exception as e:
            print(f"[ENGINEER AGENT] Error: {e}")
            bus.send(
                from_agent="engineer",
                to_agent="ceo",
                message_type="result",
                payload={"status": "error", "error": str(e)}
            )
            raise

    def handle_revision(self, revision_message, spec):
        print("\n[ENGINEER AGENT] Received revision request. Updating landing page...")
        feedback = revision_message["payload"]["feedback"]

        prompt = f"""
You are a frontend developer. Revise the HTML landing page based on this feedback:
{feedback}

Startup: WhatsApp Sales Tracker for Pakistani shopkeepers
Value Proposition: {spec['value_proposition']}

Generate a complete revised HTML landing page addressing all feedback points.
Return ONLY the complete HTML code, nothing else.
"""
        html_content = self._call_llm(prompt)
        html_content = html_content.strip()
        if html_content.startswith("```"):
            lines = html_content.split("\n")
            html_content = "\n".join(lines[1:-1])

        self._commit_file(html_content)
        print("[ENGINEER AGENT] Revised HTML committed.")

        bus.send(
            from_agent="engineer",
            to_agent="ceo",
            message_type="result",
            payload={"status": "revised", "html_content": html_content},
            parent_message_id=revision_message["message_id"]
        )
        return html_content
