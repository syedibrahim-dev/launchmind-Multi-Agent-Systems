import json
import os
import requests
from google import genai
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from message_bus import bus
from llm_helper import call_llm


class MarketingAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.name = "marketing"

    def _call_llm(self, prompt):
        return call_llm(self.client, prompt, "MARKETING AGENT")

    def _send_email(self, subject, body):
        to_email = os.environ["TEST_EMAIL"]
        from_email = os.environ["SENDGRID_FROM_EMAIL"]
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=f"<p>{body.replace(chr(10), '<br>')}</p>"
        )
        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        response = sg.send(message)
        print(f"[MARKETING AGENT] Email sent. Status: {response.status_code}")
        return response.status_code

    def _post_to_slack(self, tagline, description, pr_url):
        payload = {
            "channel": os.environ.get("SLACK_CHANNEL", "#launches"),
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"New Launch: {tagline}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": description}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
                        {"type": "mrkdwn", "text": "*Status:* Ready for review"}
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "Posted by *MarketingAgent* | LaunchMind MAS"}
                    ]
                }
            ]
        }
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
            json=payload
        )
        result = r.json()
        if result.get("ok"):
            print(f"[MARKETING AGENT] Slack message posted successfully.")
        else:
            print(f"[MARKETING AGENT] Slack error: {result.get('error')}")
        return result.get("ok", False)

    def run(self, task_message, pr_url):
        print("\n[MARKETING AGENT] Received product spec. Generating marketing copy...")

        spec = task_message["payload"]["product_spec"]
        features_text = "\n".join([f"- {f['name']}: {f['description']}" for f in spec["features"]])
        personas_text = "\n".join([f"- {p['name']} ({p['role']}): {p['pain_point']}" for p in spec["personas"]])

        copy_prompt = f"""
You are a growth marketer for a startup called "HisaabPro" - a WhatsApp-based sales tracker for Pakistani shopkeepers.

Value Proposition: {spec['value_proposition']}
Target Users:
{personas_text}
Core Features:
{features_text}

Generate marketing copy and return ONLY a valid JSON object with this exact structure:
{{
    "tagline": "Under 10 words, punchy and memorable",
    "description": "2-3 sentences for a landing page, highlighting the main benefit",
    "cold_email": {{
        "subject": "Email subject line in English",
        "body": "Cold outreach email body in ENGLISH only (150-200 words) addressed to a kiryana store owner, friendly professional tone, clear CTA. Do NOT use Urdu or Roman Urdu."
    }},
    "social_posts": {{
        "twitter": "Tweet under 280 chars with relevant hashtags",
        "linkedin": "LinkedIn post 3-4 sentences, professional tone",
        "instagram": "Instagram caption with emojis and hashtags"
    }}
}}

Write everything in English only. Make it specific to Pakistani small business owners but keep all text in English.
Return ONLY the JSON, no markdown, no explanation.
"""
        raw = self._call_llm(copy_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        copy = json.loads(raw)

        print(f"[MARKETING AGENT] Tagline: {copy['tagline']}")
        print(f"[MARKETING AGENT] Sending email...")

        # Send real email
        self._send_email(copy["cold_email"]["subject"], copy["cold_email"]["body"])

        # Post to Slack
        print(f"[MARKETING AGENT] Posting to Slack...")
        self._post_to_slack(copy["tagline"], copy["description"], pr_url)

        # Report back to CEO
        bus.send(
            from_agent="marketing",
            to_agent="ceo",
            message_type="result",
            payload={
                "status": "success",
                "copy": copy,
                "email_sent": True,
                "slack_posted": True
            },
            parent_message_id=task_message["message_id"]
        )

        print("[MARKETING AGENT] Done.")
        return copy
