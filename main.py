import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add agents directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

from agents.ceo_agent import CEOAgent
from agents.product_agent import ProductAgent
from agents.engineer_agent import EngineerAgent
from agents.marketing_agent import MarketingAgent
from agents.qa_agent import QAAgent


STARTUP_IDEA = (
    "HisaabPro - A WhatsApp-based daily sales tracker for Pakistani kiryana store owners and street vendors. "
    "Shopkeepers send a WhatsApp message to log each sale, and the system automatically tracks "
    "inventory, calculates daily profit/loss, and sends a summary report every evening - "
    "no app download or technical knowledge required."
)


def main():
    print("\nLaunchMind - Multi-Agent Startup System")
    print("Powered by Gemini Pro\n")

    # Validate required environment variables
    required = ["GEMINI_API_KEY", "GITHUB_TOKEN", "GITHUB_REPO",
                "SLACK_BOT_TOKEN", "SENDGRID_API_KEY",
                "SENDGRID_FROM_EMAIL", "TEST_EMAIL"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    # Initialize all agents
    ceo = CEOAgent()
    product = ProductAgent()
    engineer = EngineerAgent()
    marketing = MarketingAgent()
    qa = QAAgent()

    # Run the full pipeline
    result = ceo.run(STARTUP_IDEA, product, engineer, marketing, qa)

    print("\nDone! Summary:")
    print(f"  PR URL:    {result['pr_url']}")
    print(f"  Issue URL: {result['issue_url']}")


if __name__ == "__main__":
    main()
