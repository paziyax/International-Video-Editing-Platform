<div align="center">

# International Freelance Video Editing Platform

**An AI-powered video project assistant built with Python, Gradio, Pydantic, LiteLLM and Ollama.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio&logoColor=white)
![Pydantic](https://img.shields.io/badge/Data-Pydantic-E92063?logo=pydantic)
![LiteLLM](https://img.shields.io/badge/LLM-LiteLLM-111827)
![Ollama](https://img.shields.io/badge/Local%20AI-Ollama-black?logo=ollama)
![Demo](https://img.shields.io/badge/Project-Synthetic%20Demo-blueviolet)

*Configure a video project, discover a matching editor, estimate production costs and prepare a project handoff in one Project conversation.*

</div>

> **Synthetic-data demo:** Editor names, profiles and contact details are fictional or placeholders. This project demonstrates an AI-assisted workflow; it is not a live freelance marketplace.

## Overview

The **International Freelance Video Editing Platform** is a Gradio app for configuring a video-editing project, receiving a synthetic editor recommendation, reviewing an indicative estimate and preparing a project handoff.

### Main features

- One interactive chat interface and a project form for category, content type, editor location, duration and description.
- LLM extraction of requested editing techniques.
- Pydantic-validated project and editor data.
- Synthetic editor recommendations, with select or try-another options.
- Indicative production hours, software, delivery time, complexity and cost.
- Python-generated Markdown report and project reference token.
- Local Ollama or cloud models through LiteLLM.

## How the Workflow Works

1. **Welcome:** The customer starts the conversation and chooses to configure a project.
2. **Configure project:** They select the video category, content type and editor region/country, enter the desired final duration (for example, `45 seconds`), and describe the editing they want.
3. **Analyse requirements:** The model reads the full description and identifies the requested editing techniques. Python keeps the customer's selected values and the `VideoEditingRequirement` and `EditorLocation` models organize the data.
4. **Recommend an editor:** The model generates a fictional `EditorProfile`. Its specializations describe the editor's professional skills (such as podcast editing or multicamera editing), not simply a copy of the customer's requested techniques. The customer can choose the profile or request another.
5. **Estimate production:** The model creates `ProductionDetails`, including estimated working hours, software, delivery days, complexity and cost, using the project details and configured pricing reference.
6. **Create report:** Python formats the requirements, selected editor and estimate into one Markdown report. No LLM call is needed just to assemble the report.
7. **Project handoff:** The customer enters their name. Python generates a reference token, and the assistant explains how to submit project files or links with that token.

## Architecture

```text
Gradio UI (one Interactive chat interface, forms and buttons)
                    |
             handle_workflow()
                    |
          Python workflow functions
             /             \
   Pydantic data models    Python report + token
             |
       LiteLLM completion()
             |
   Ollama / OpenAI / OpenRouter
```

| Component | Role |
|---|---|
| Gradio | chat interface, forms, buttons and session state |
| Python | Workflow control, formatting, calculations and token generation |
| Pydantic | Defines and validates structured project data |
| LiteLLM SDK | Provides one Python interface to supported LLM providers |
| Ollama | Runs downloaded models locally |

**LiteLLM note:** The app uses the LiteLLM **Python SDK** (`completion()`), not a separately deployed LiteLLM Proxy. The Proxy/AI Gateway is optional.

## Data Models

- `VideoEditingRequirement` — category, content type, requested duration and editing techniques.
- `EditorLocation` — selected editor region and country.
- `EditorProfile` — fictional editor name, country, professional specializations and synthetic-profile flag.
- `ProductionDetails` — estimated hours, software, delivery time, complexity, cost and currency.

Pydantic validates structure, not the factual accuracy of generated profiles or estimates.

## AI Setup: Local or Cloud

The app calls models through LiteLLM's `completion()`. To switch providers, change the model identifier and configure the required credentials or endpoint.

### Option 1: Ollama (local)

Ollama runs models on your computer. After download, local inference has no per-request hosted-model API fee; speed and capacity depend on your hardware. Model downloads require disk space and internet.

## This project currently uses Llama 3.2 with Ollama for local AI processing.

**You can download and run any compatible model from the [Ollama Library](https://ollama.com/library). Simply change the model name in the configuration. Results depend on the model you choose.**



1. Install [Ollama](https://ollama.com/download).
2. Download a model:

   ```bash
   ollama pull llama3.2:latest
   ```

3. Configure LiteLLM:

   ```python
   from litellm import completion

   MODEL = "ollama/llama3.2:latest"
   OLLAMA_API_BASE = "http://localhost:11434"

   response = completion(
       model=MODEL,
       messages=messages,
       api_base=OLLAMA_API_BASE,
   )
   ```

   For structured Pydantic output, pass the relevant class with `response_format=YourPydanticModel`. Structured-output support can vary by model, so test the model you choose.

## This project uses *LiteLLM*, allowing you to connect to many AI providers, not just OpenAI or OpenRouter. Choose any supported provider and configure your preferred model.

### Option 2: OpenAI or OpenRouter

LiteLLM supports multiple providers through the same `completion()` interface. Change the model name and set the required API key as an environment variable:

```python
# OpenAI
MODEL = "openai/<your-model-id>"

# OpenRouter
MODEL = "openrouter/<provider>/<model-id>"

response = completion(model=MODEL, messages=messages)
```

Set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in your environment (or a local `.env` file). Cloud API usage may incur charges based on the provider and model. LiteLLM is open-source; using its SDK does not make third-party model APIs free.

## Installation and Run

**Requirements:** Python 3.11+, Git, and Ollama with a model or a cloud-provider API key.

1. Clone the repository and enter the project folder:

   ```bash
   git clone <your-repository-url>
   cd <your-project-folder>
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell: `.venv\Scripts\Activate.ps1`  
   macOS/Linux: `source .venv/bin/activate`

3. Install dependencies:

   ```bash
   pip install gradio litellm pydantic python-dotenv
   ```

   Or use `pip install -r requirements.txt` if the repository includes that file.

4. Configure the model and keep any API keys in environment variables. Never commit secrets; add `.env` to `.gitignore`.
5. Start Ollama if using a local model, then launch the Gradio app (replace `app.py` if your entry-point filename differs):

   ```bash
   python app.py
   ```

## Demo Scope and Future Work

This is a demo, not a live marketplace. Editor profiles and `example.com` addresses are placeholders and cannot receive files. Estimates are not binding quotations; tokens are not database-backed IDs. The app does not send emails or transfer files.

A production version needs verified editors, persistent storage, database-backed IDs, real email/file handling, validated pricing, authentication, privacy controls and tests.

## Documentation

- [Gradio](https://www.gradio.app/docs) · [Pydantic](https://docs.pydantic.dev/)
- [LiteLLM Python SDK](https://docs.litellm.ai/docs/python_sdk) · [LiteLLM providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM with Ollama](https://docs.litellm.ai/docs/providers/ollama) · [Ollama](https://docs.ollama.com/)
- [OpenRouter](https://openrouter.ai/docs)

---

<div align="center">

**International Freelance Video Editing Platform**  
*An AI-assisted workflow demonstration using synthetic editor data.*

</div>
