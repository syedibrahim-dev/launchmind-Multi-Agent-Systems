import json
import os
from google import genai
from message_bus import bus
from llm_helper import call_llm


class ProductAgent:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.name = "product"

    def _call_llm(self, prompt):
        return call_llm(self.client, prompt, "PRODUCT AGENT")

    def run(self, task_message):
        print("\n[PRODUCT AGENT] Received task from CEO. Generating product spec...")

        idea = task_message["payload"]["idea"]
        focus = task_message["payload"].get("focus", "")

        prompt = f"""
You are a senior product manager. Generate a detailed product specification for the following startup idea.

Startup Idea: {idea}
Focus Areas: {focus}

Return ONLY a valid JSON object with exactly this structure:
{{
    "value_proposition": "One sentence describing what the product does and for whom",
    "personas": [
        {{"name": "...", "role": "...", "pain_point": "..."}},
        {{"name": "...", "role": "...", "pain_point": "..."}},
        {{"name": "...", "role": "...", "pain_point": "..."}}
    ],
    "features": [
        {{"name": "...", "description": "...", "priority": 1}},
        {{"name": "...", "description": "...", "priority": 2}},
        {{"name": "...", "description": "...", "priority": 3}},
        {{"name": "...", "description": "...", "priority": 4}},
        {{"name": "...", "description": "...", "priority": 5}}
    ],
    "user_stories": [
        {{"as_a": "...", "i_want": "...", "so_that": "..."}},
        {{"as_a": "...", "i_want": "...", "so_that": "..."}},
        {{"as_a": "...", "i_want": "...", "so_that": "..."}}
    ]
}}

Make the personas specific to Pakistani small shopkeepers and vendors. Use realistic local names and pain points.
Return ONLY the JSON, no markdown, no explanation.
"""
        raw = self._call_llm(prompt)

        # Strip markdown code blocks if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        spec = json.loads(raw)
        print(f"[PRODUCT AGENT] Spec generated. Value prop: {spec['value_proposition']}")

        # Send spec to Engineer and Marketing
        bus.send(
            from_agent="product",
            to_agent="engineer",
            message_type="result",
            payload={"product_spec": spec},
            parent_message_id=task_message["message_id"]
        )
        bus.send(
            from_agent="product",
            to_agent="marketing",
            message_type="result",
            payload={"product_spec": spec},
            parent_message_id=task_message["message_id"]
        )

        # Confirm to CEO
        msg_id = bus.send(
            from_agent="product",
            to_agent="ceo",
            message_type="confirmation",
            payload={"status": "spec_ready", "product_spec": spec},
            parent_message_id=task_message["message_id"]
        )

        print("[PRODUCT AGENT] Spec sent to Engineer, Marketing, and CEO.")
        return spec

    def handle_revision(self, revision_message):
        print("\n[PRODUCT AGENT] Received revision request from CEO. Revising spec...")
        feedback = revision_message["payload"]["feedback"]
        original_idea = revision_message["payload"]["idea"]

        prompt = f"""
You are a senior product manager. Your previous product specification was reviewed and needs revision.

Original Startup Idea: {original_idea}
Feedback from reviewer: {feedback}

Generate an improved product specification addressing all the feedback.

Return ONLY a valid JSON object with exactly this structure:
{{
    "value_proposition": "One sentence describing what the product does and for whom",
    "personas": [
        {{"name": "...", "role": "...", "pain_point": "..."}},
        {{"name": "...", "role": "...", "pain_point": "..."}},
        {{"name": "...", "role": "...", "pain_point": "..."}}
    ],
    "features": [
        {{"name": "...", "description": "...", "priority": 1}},
        {{"name": "...", "description": "...", "priority": 2}},
        {{"name": "...", "description": "...", "priority": 3}},
        {{"name": "...", "description": "...", "priority": 4}},
        {{"name": "...", "description": "...", "priority": 5}}
    ],
    "user_stories": [
        {{"as_a": "...", "i_want": "...", "so_that": "..."}},
        {{"as_a": "...", "i_want": "...", "so_that": "..."}},
        {{"as_a": "...", "i_want": "...", "so_that": "..."}}
    ]
}}

Return ONLY the JSON, no markdown, no explanation.
"""
        raw = self._call_llm(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        spec = json.loads(raw)
        print(f"[PRODUCT AGENT] Revised spec ready.")

        bus.send(
            from_agent="product",
            to_agent="engineer",
            message_type="result",
            payload={"product_spec": spec},
            parent_message_id=revision_message["message_id"]
        )
        bus.send(
            from_agent="product",
            to_agent="marketing",
            message_type="result",
            payload={"product_spec": spec},
            parent_message_id=revision_message["message_id"]
        )
        bus.send(
            from_agent="product",
            to_agent="ceo",
            message_type="confirmation",
            payload={"status": "spec_revised", "product_spec": spec},
            parent_message_id=revision_message["message_id"]
        )
        return spec
