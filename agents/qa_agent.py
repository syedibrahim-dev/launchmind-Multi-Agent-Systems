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


class QAAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.name = "qa"

    def _call_llm(self, prompt):
        return call_llm(self.client, prompt, "QA AGENT")

    def _get_pr_number(self, pr_url):
        return int(pr_url.rstrip("/").split("/")[-1])

    def _get_commit_id(self, pr_number):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        commits = r.json()
        return commits[-1]["sha"] if commits else None

    def _post_pr_review(self, pr_number, commit_id, html_content, comments_data):
        review_comments = []
        lines = html_content.split("\n")

        for comment in comments_data[:2]:
            # Find a relevant line number for each comment
            search_term = comment.get("search_for", "<body")
            line_num = 1
            for i, line in enumerate(lines, 1):
                if search_term.lower() in line.lower():
                    line_num = i
                    break

            review_comments.append({
                "path": "index.html",
                "position": line_num,
                "body": comment["body"]
            })

        url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
        payload = {
            "commit_id": commit_id,
            "body": "QA Agent automated review of the landing page.",
            "event": "COMMENT",
            "comments": review_comments
        }
        r = requests.post(url, headers=HEADERS, json=payload)
        if r.status_code in (200, 201):
            print(f"[QA AGENT] PR review posted with {len(review_comments)} inline comments.")
        else:
            print(f"[QA AGENT] PR review error: {r.status_code} {r.text}")

    def run(self, task_message):
        print("\n[QA AGENT] Starting review of HTML and marketing copy...")

        html_content = task_message["payload"]["html_content"]
        copy = task_message["payload"]["copy"]
        spec = task_message["payload"]["product_spec"]
        pr_url = task_message["payload"]["pr_url"]

        features_text = "\n".join([f"- {f['name']}" for f in spec["features"]])

        html_review_prompt = f"""
You are a QA engineer reviewing a startup landing page.

Product Spec:
- Value Proposition: {spec['value_proposition']}
- Features: {features_text}

HTML Landing Page:
{html_content[:3000]}

Review this landing page and return ONLY a valid JSON object:
{{
    "verdict": "pass" or "fail",
    "headline_matches_value_prop": true or false,
    "features_mentioned": true or false,
    "has_cta": true or false,
    "issues": ["issue 1", "issue 2"],
    "pr_comments": [
        {{"search_for": "html element to find", "body": "inline review comment text"}},
        {{"search_for": "another html element", "body": "second inline review comment text"}}
    ],
    "summary": "One paragraph overall assessment"
}}

Be critical but fair. Pass only if headline clearly reflects value prop AND at least 3 features are visible AND a CTA button exists.
Return ONLY the JSON.
"""
        raw_html_review = self._call_llm(html_review_prompt)
        raw_html_review = raw_html_review.strip()
        if raw_html_review.startswith("```"):
            raw_html_review = raw_html_review.split("```")[1]
            if raw_html_review.startswith("json"):
                raw_html_review = raw_html_review[4:]
        html_review = json.loads(raw_html_review.strip())

        copy_review_prompt = f"""
You are a marketing QA reviewer.

Marketing Copy to review:
- Tagline: {copy['tagline']}
- Description: {copy['description']}
- Email Subject: {copy['cold_email']['subject']}
- Email Body: {copy['cold_email']['body']}

Return ONLY a valid JSON object:
{{
    "tagline_compelling": true or false,
    "email_has_cta": true or false,
    "tone_appropriate": true or false,
    "issues": ["issue 1", "issue 2"],
    "verdict": "pass" or "fail",
    "summary": "One paragraph assessment"
}}

Return ONLY the JSON.
"""
        raw_copy_review = self._call_llm(copy_review_prompt)
        raw_copy_review = raw_copy_review.strip()
        if raw_copy_review.startswith("```"):
            raw_copy_review = raw_copy_review.split("```")[1]
            if raw_copy_review.startswith("json"):
                raw_copy_review = raw_copy_review[4:]
        copy_review = json.loads(raw_copy_review.strip())

        overall_verdict = "pass" if html_review["verdict"] == "pass" and copy_review["verdict"] == "pass" else "fail"

        print(f"[QA AGENT] HTML review: {html_review['verdict'].upper()}")
        print(f"[QA AGENT] Copy review: {copy_review['verdict'].upper()}")
        print(f"[QA AGENT] Overall verdict: {overall_verdict.upper()}")

        # Post inline comments on the PR
        try:
            pr_number = self._get_pr_number(pr_url)
            commit_id = self._get_commit_id(pr_number)
            if commit_id and html_review.get("pr_comments"):
                self._post_pr_review(pr_number, commit_id, html_content, html_review["pr_comments"])
        except Exception as e:
            print(f"[QA AGENT] Could not post PR review: {e}")

        report = {
            "verdict": overall_verdict,
            "html_review": html_review,
            "copy_review": copy_review,
            "issues": html_review.get("issues", []) + copy_review.get("issues", [])
        }

        bus.send(
            from_agent="qa",
            to_agent="ceo",
            message_type="result",
            payload={"review_report": report},
            parent_message_id=task_message["message_id"]
        )

        return report
