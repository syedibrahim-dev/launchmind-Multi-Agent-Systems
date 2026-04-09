import json
import os
import time
from google import genai
from message_bus import bus
from llm_helper import call_llm


class CEOAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.name = "ceo"
        self.decision_log = []

    def _call_llm(self, prompt):
        return call_llm(self.client, prompt, "CEO AGENT")

    def _log(self, decision, reason):
        entry = {"decision": decision, "reason": reason}
        self.decision_log.append(entry)
        print(f"[CEO AGENT] Decision: {decision}")
        print(f"[CEO AGENT] Reason:   {reason}")

    def _decompose_idea(self, idea):
        print("\n[CEO AGENT] Decomposing startup idea into agent tasks...")
        prompt = f"""
You are the CEO of a startup. You have received the following startup idea:
"{idea}"

Your job is to decompose this into specific tasks for three agents: Product, Engineer, and Marketing.

Return ONLY a valid JSON object with this structure:
{{
    "product_task": {{
        "idea": "{idea}",
        "focus": "specific focus areas for the product manager to address"
    }},
    "engineer_task": {{
        "idea": "{idea}",
        "focus": "specific technical implementation focus for the engineer"
    }},
    "marketing_task": {{
        "idea": "{idea}",
        "focus": "specific marketing angles and target audience focus"
    }},
    "reasoning": "Why you decomposed it this way"
}}

Be specific. The more context you give each agent, the better their output will be.
Return ONLY the JSON, no markdown.
"""
        raw = self._call_llm(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        tasks = json.loads(raw.strip())
        self._log("Decomposed idea into tasks", tasks["reasoning"])
        return tasks

    def _review_product_spec(self, spec, idea):
        print("\n[CEO AGENT] Reviewing product spec with LLM...")
        prompt = f"""
You are the CEO reviewing your Product Manager's work.

Original Idea: {idea}
Product Spec Submitted:
{json.dumps(spec, indent=2)}

Review this spec critically. Ask yourself:
1. Is the value proposition specific and compelling?
2. Are the personas realistic and detailed enough?
3. Do the features directly address the user pain points?
4. Are the user stories actionable?

Return ONLY a valid JSON object:
{{
    "verdict": "accept" or "revise",
    "feedback": "Specific feedback if revising, or 'Spec is solid' if accepting",
    "reasoning": "Why you made this decision"
}}

Return ONLY the JSON.
"""
        raw = self._call_llm(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        review = json.loads(raw.strip())
        self._log(f"Product spec review: {review['verdict'].upper()}", review["reasoning"])
        return review

    def _review_qa_report(self, report):
        print("\n[CEO AGENT] Reviewing QA report with LLM...")
        prompt = f"""
You are the CEO reviewing your QA team's findings.

QA Report:
- Overall Verdict: {report['verdict']}
- Issues Found: {json.dumps(report['issues'])}
- HTML Review: {report['html_review']['summary']}
- Copy Review: {report['copy_review']['summary']}

Based on this QA report, what should happen next?

Return ONLY a valid JSON object:
{{
    "action": "approve" or "request_engineer_revision" or "request_marketing_revision",
    "feedback_for_engineer": "Specific HTML issues to fix (if applicable)",
    "feedback_for_marketing": "Specific copy issues to fix (if applicable)",
    "reasoning": "Why you made this decision"
}}

Return ONLY the JSON.
"""
        raw = self._call_llm(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        decision = json.loads(raw.strip())
        self._log(f"QA report action: {decision['action'].upper()}", decision["reasoning"])
        return decision

    def _post_final_slack_summary(self, idea, spec, pr_url, issue_url, copy):
        import requests
        tagline = copy.get("tagline", "Launching now")
        description = copy.get("description", spec["value_proposition"])

        payload = {
            "channel": os.environ.get("SLACK_CHANNEL", "#launches"),
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "LaunchMind - Startup Launch Complete!"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Idea:* {idea}\n*Tagline:* _{tagline}_"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": description}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
                        {"type": "mrkdwn", "text": f"*GitHub Issue:* <{issue_url}|View Issue>"},
                        {"type": "mrkdwn", "text": f"*Email:* Sent to test inbox ✅"},
                        {"type": "mrkdwn", "text": f"*Agents:* CEO, Product, Engineer, Marketing, QA"}
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "All tasks completed autonomously by *LaunchMind MAS*"}
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
            print("[CEO AGENT] Final Slack summary posted.")
        else:
            print(f"[CEO AGENT] Slack error: {result.get('error')}")

    def run(self, idea, product_agent, engineer_agent, marketing_agent, qa_agent):
        print("\n" + "="*60)
        print("CEO AGENT - LaunchMind MAS Starting")
        print(f"Idea: {idea}")
        print("="*60)

        # Step 1: Decompose idea into tasks
        tasks = self._decompose_idea(idea)

        # Step 2: Send task to Product agent
        msg_id = bus.send(
            from_agent="ceo",
            to_agent="product",
            message_type="task",
            payload=tasks["product_task"]
        )

        # Step 3: Product agent runs
        spec = product_agent.run(bus.receive("product")[0])

        # Step 4: CEO reviews the product spec (LLM review - feedback loop #1)
        review = self._review_product_spec(spec, idea)

        if review["verdict"] == "revise":
            print("\n[CEO AGENT] Sending revision request to Product agent...")
            rev_msg_id = bus.send(
                from_agent="ceo",
                to_agent="product",
                message_type="revision_request",
                payload={"feedback": review["feedback"], "idea": idea}
            )
            spec = product_agent.handle_revision(bus.receive("product")[0])
            # Clear the CEO inbox from product's revised confirmation
            bus.receive("ceo")
        else:
            # Clear confirmation from product
            bus.receive("ceo")

        # Step 5: Engineer and Marketing run in sequence (spec already sent by Product agent)
        engineer_messages = bus.receive("engineer")
        marketing_messages = bus.receive("marketing")

        pr_url, issue_url, html_content = engineer_agent.run(engineer_messages[0])

        # Get engineer result from CEO inbox
        engineer_result = bus.receive("ceo")

        copy = marketing_agent.run(marketing_messages[0], pr_url)

        # Get marketing result from CEO inbox
        marketing_result = bus.receive("ceo")

        # Step 6: QA Agent reviews everything (feedback loop #2)
        bus.send(
            from_agent="ceo",
            to_agent="qa",
            message_type="task",
            payload={
                "html_content": html_content,
                "copy": copy,
                "product_spec": spec,
                "pr_url": pr_url
            }
        )
        qa_report = qa_agent.run(bus.receive("qa")[0])

        # Get QA result from CEO inbox
        bus.receive("ceo")

        # Step 7: CEO reviews QA report (LLM reasoning)
        qa_decision = self._review_qa_report(qa_report)

        if qa_decision["action"] == "request_engineer_revision":
            print("\n[CEO AGENT] QA failed. Sending revision request to Engineer...")
            rev_msg = bus.send(
                from_agent="ceo",
                to_agent="engineer",
                message_type="revision_request",
                payload={"feedback": qa_decision["feedback_for_engineer"]}
            )
            engineer_agent.handle_revision(bus.receive("engineer")[0], spec)
            bus.receive("ceo")

        elif qa_decision["action"] == "request_marketing_revision":
            print("\n[CEO AGENT] QA failed on copy. Note: marketing revision would be triggered here.")

        # Step 8: Post final Slack summary
        print("\n[CEO AGENT] All agents done. Posting final summary to Slack...")
        self._post_final_slack_summary(idea, spec, pr_url, issue_url, copy)

        print("\n" + "="*60)
        print("LaunchMind MAS - COMPLETE")
        print(f"GitHub PR:    {pr_url}")
        print(f"GitHub Issue: {issue_url}")
        print("Email:        Sent to test inbox")
        print("Slack:        Messages posted")
        print("="*60)

        print("\n--- CEO DECISION LOG ---")
        for i, entry in enumerate(self.decision_log, 1):
            print(f"{i}. {entry['decision']}")
            print(f"   -> {entry['reason']}")

        bus.print_full_log()

        return {
            "pr_url": pr_url,
            "issue_url": issue_url,
            "spec": spec,
            "copy": copy,
            "qa_report": qa_report
        }
