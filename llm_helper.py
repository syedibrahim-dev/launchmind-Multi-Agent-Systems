import time
import re
from google import genai
import os

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def call_llm(client, prompt, agent_name="AGENT"):
    """Call Gemini with automatic fallback between models and retry on errors."""
    time.sleep(13)  # respect 5 RPM limit

    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as e:
                err = str(e)
                if "503" in err:
                    wait = 30 * (attempt + 1)
                    print(f"[{agent_name}] {model} busy (503), retrying in {wait}s...")
                    time.sleep(wait)
                elif "429" in err:
                    # Extract retry delay from error if available
                    match = re.search(r'retry in (\d+)', err)
                    wait = int(match.group(1)) + 5 if match else 60
                    if "limit: 0" in err:
                        # This model has zero quota, skip to next
                        print(f"[{agent_name}] {model} has no quota, trying next model...")
                        break
                    print(f"[{agent_name}] Rate limited on {model}, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        else:
            continue  # model exhausted all retries, try next
        break  # broke out of attempt loop (zero quota), try next model

    raise RuntimeError(f"[{agent_name}] All models failed. Try again later.")
