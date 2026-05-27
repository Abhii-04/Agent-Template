# Sidekick

Sidekick is a browser-capable AI co-worker that keeps working until your task meets a success criteria you define.

It combines a Gradio chat interface, LangGraph workflow orchestration, browser automation with Playwright, web search, Wikipedia lookup, local file tools, Python execution, and an evaluator loop that checks whether the result is good enough before stopping.

## Why Sidekick?

Most chatbots answer once and wait for you to notice what is missing. Sidekick takes a more practical approach:

- You give it a task.
- You define what success looks like.
- It can use tools to browse, search, write files, run Python, and gather information.
- It evaluates its own work against your success criteria.
- If the answer is not good enough, it loops and improves the result.
- If it needs clarification, it asks instead of guessing.

## Features

- **Agentic task loop**: LangGraph coordinates worker, tool, and evaluator nodes.
- **Success criteria evaluation**: each response is checked before the run ends.
- **Browser automation**: Playwright lets the assistant inspect and navigate web pages.
- **Search and research tools**: Serper search and Wikipedia integration are available to the agent.
- **Local file workspace**: file tools are scoped to the `sandbox/` directory.
- **Python execution**: the assistant can run Python snippets for calculations and data work.
- **Push notifications**: optional Pushover integration for notifications.
- **Simple web UI**: Gradio provides a local chat interface.

## How It Works

```text
User request + success criteria
        |
        v
Worker LLM decides whether to answer or use tools
        |
        v
Tools run when needed: browser, search, files, Python, Wikipedia, notifications
        |
        v
Evaluator checks the latest answer against the success criteria
        |
        v
Finish, ask the user a question, or loop back to improve the answer
```

## Tech Stack

- Python 3.12+
- Gradio
- LangChain
- LangGraph
- Playwright
- DeepSeek via the OpenAI-compatible API
- Serper search API

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/sidekick.git
cd sidekick
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install
```

If you use `uv`:

```bash
uv sync
uv run playwright install
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
SERPER_API_KEY=your_serper_api_key
PUSHOVER_TOKEN=your_pushover_token
PUSHOVER_USER=your_pushover_user
```

Required:

- `DEEPSEEK_API_KEY`: used by the main LLM.
- `SERPER_API_KEY`: used by the search tool.

Optional:

- `PUSHOVER_TOKEN`
- `PUSHOVER_USER`

## Run the App

```bash
python main.py
```

The Gradio app opens in your browser. Enter:

- **Your request**: the task you want Sidekick to complete.
- **Success criteria**: the standard Sidekick should use to decide whether the task is finished.

Example:

```text
Request:
Find 10 recent AI engineer jobs in Bengaluru and save them as a Markdown table.

Success criteria:
The answer must include company, role, location, experience, salary if available, and application link.
```

## Project Structure

```text
.
├── main.py           # Gradio UI and app lifecycle
├── sidekick.py       # LangGraph agent workflow
├── tools.py          # Browser, search, file, Python, Wikipedia, and notification tools
├── sandbox/          # Workspace for agent-created files
├── requirements.txt  # Pinned Python dependencies
├── pyproject.toml    # Project metadata
└── README.md
```

## Notes

- Playwright is launched with a visible Chrome browser window.
- File operations are intentionally scoped to `sandbox/`.
- The project currently uses DeepSeek's OpenAI-compatible API endpoint.
- Do not commit your `.env` file or API keys.

## GitHub Repository Description

Browser-capable AI co-worker built with LangGraph, Playwright, and Gradio. Give it a task, define success criteria, and it loops through tools and self-evaluation until the job is done.

## License

Add a license before publishing if you want others to use, modify, or distribute the project.
