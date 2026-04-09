# LaunchMind - HisaabPro

**Build a Startup Using a Team of Collaborating AI Agents**

> HisaabPro is a WhatsApp-based daily sales tracker for Pakistani kiryana store owners and street vendors. Shopkeepers send a WhatsApp message to log each sale, and the system automatically tracks inventory, calculates daily profit/loss, and sends a summary report every evening — no app download or technical knowledge required.

---

## What This System Does

LaunchMind is a Multi-Agent System (MAS) that autonomously runs a micro-startup from a single idea. You provide the startup concept and the system does everything else: defines the product, writes a landing page, pushes it to GitHub, sends a marketing email, and posts to Slack — all without human intervention.

---

## Agent Architecture

```
                        You
                         |
                  [Startup Idea]
                         |
                    CEO Agent
                   (Orchestrator)
                         |
              LLM decomposes idea into tasks
                         |
           +-------------+-------------+
           |                           |
    Product Agent              (waits for spec)
    - Generates product spec
    - Personas, features,
      user stories
           |
    CEO Agent reviews spec (LLM)
    [FEEDBACK LOOP 1]
    If poor -> revision_request
    If good -> continue
           |
     +-----+-----+
     |           |
Engineer      Marketing
Agent          Agent
     |           |
 Generates    Generates
 HTML page    copy + email
 GitHub PR    Slack post
 GitHub Issue
     |           |
     +-----+-----+
           |
       QA Agent
   Reviews HTML + copy
   Posts PR comments
   Returns pass/fail
           |
    CEO Agent reviews QA (LLM)
    [FEEDBACK LOOP 2]
    If fail -> revision_request to Engineer
    If pass -> continue
           |
    CEO posts final
    Slack summary
```

### Agent Descriptions

| Agent | File | Role |
|-------|------|------|
| **CEO Agent** | `agents/ceo_agent.py` | Orchestrates all agents, decomposes idea, reviews outputs, drives feedback loops |
| **Product Agent** | `agents/product_agent.py` | Generates product spec with personas, features, and user stories |
| **Engineer Agent** | `agents/engineer_agent.py` | Writes HTML landing page, creates GitHub branch, commits code, opens PR |
| **Marketing Agent** | `agents/marketing_agent.py` | Generates marketing copy, sends cold email, posts to Slack |
| **QA Agent** | `agents/qa_agent.py` | Reviews HTML and copy, posts inline PR comments, returns pass/fail verdict |

---

## Platform Integrations

| Platform | Agent | What it does |
|----------|-------|-------------|
| **GitHub** | Engineer | Creates branch, commits `index.html`, opens Pull Request, creates Issue |
| **GitHub** | QA | Posts 2 inline review comments on the PR |
| **Slack** | Marketing | Posts Block Kit launch announcement to `#launches` |
| **Slack** | CEO | Posts final summary message to `#launches` |
| **Email (SendGrid)** | Marketing | Sends cold outreach email to test inbox |

---

## Message Schema

Every message between agents follows this structure:

```json
{
  "message_id": "uuid",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task | result | revision_request | confirmation",
  "payload": { ... },
  "timestamp": "2026-04-09T08:00:00Z",
  "parent_message_id": "uuid (optional)"
}
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/syedibrahim-dev/launchmind-Multi-Agent-Systems.git
cd launchmind-Multi-Agent-Systems
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=your_username/launchmind-Multi-Agent-Systems
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#launches
SENDGRID_API_KEY=SG.your_sendgrid_key
SENDGRID_FROM_EMAIL=your_verified_sender@email.com
TEST_EMAIL=your_test_inbox@email.com
```

### 4. Platform setup

**GitHub:**
- Create a public repo named `launchmind-Multi-Agent-Systems`
- Generate a PAT at Settings > Developer Settings > Personal Access Tokens with `repo` scope
- Initialize the repo with a README so the `main` branch exists

**Slack:**
- Create a free workspace at slack.com
- Go to api.slack.com/apps > Create New App > From Scratch
- Add Bot Token Scopes: `chat:write`, `channels:read`, `channels:join`
- Install to workspace and copy the `xoxb-` token
- Create a `#launches` channel and invite the bot with `/invite @LaunchMindBot`

**SendGrid:**
- Create a free account at sendgrid.com (100 emails/day, no credit card)
- Create an API key with Mail Send permission
- Verify a sender email address

**Gemini:**
- Get a free API key at aistudio.google.com
- Uses `gemini-2.5-flash` model

### 5. Run the system

```bash
python main.py
```

The system runs end-to-end in approximately 5-10 minutes (rate limit delays between LLM calls).

---

## Demo

- **GitHub PR:** https://github.com/syedibrahim-dev/launchmind-Multi-Agent-Systems/pull/4
- **GitHub Issue:** https://github.com/syedibrahim-dev/launchmind-Multi-Agent-Systems/issues/3
- **Demo Video:** [Link to demo video]
- **Slack:** [Share workspace invite link or screenshot]

---

## Group Members & Agent Ownership

| Member | Agent |
|--------|-------|
| Member 1 | CEO Agent (`agents/ceo_agent.py`) |
| Member 2 | Product Agent + Engineer Agent |
| Member 3 | Marketing Agent + QA Agent |

---

## Project Structure

```
launchmind-Multi-Agent-Systems/
├── agents/
│   ├── ceo_agent.py         # Orchestrator with feedback loops
│   ├── product_agent.py     # Product spec generation
│   ├── engineer_agent.py    # GitHub integration + HTML generation
│   ├── marketing_agent.py   # Email + Slack integration
│   └── qa_agent.py          # HTML/copy review + PR comments
├── main.py                  # Entry point - runs the full pipeline
├── message_bus.py           # Shared JSON message passing between agents
├── llm_helper.py            # Gemini API wrapper with retry logic
├── view_logs.py             # View outputs from the last run
├── requirements.txt
├── .env.example
└── .gitignore
```
