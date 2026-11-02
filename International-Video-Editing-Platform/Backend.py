# 1. STANDARD LIBRARY

import json
import os
import re
import secrets

from copy import deepcopy
from typing import Literal

# 2. EXTERNAL DEPENDENCIES

from dotenv import load_dotenv

from litellm import completion
from pydantic import BaseModel, Field, model_validator

Ollama_Model = "ollama/llama3.2:latest"
OLLAMA_API_BASE = "http://localhost:11434"

def user_first_approach(first_message):

    response = """Hello! Thank you for reaching out!

    I'd be happy to help you with your video editing project.

    Are you ready to configure your project?
    """

    return response

VIDEO_CONTENT_TYPES = {
    "Long-form": ["Talking Head","YouTube Video","Documentary","Podcast / Interview","Music Video","Corporate / Business Video",
                  "Educational / Tutorial","Product Review","Webinar / Online Course","Event Coverage","Cinematic Storytelling",
                  "Motion Graphics / Explainer","Commercial / Branded Content","Gaming Video","Travel / Lifestyle Video",],

    "Short-form": ["Instagram Reels","TikTok Videos","YouTube Shorts",  "Talking Head Clips","Podcast Clips","Mini-Documentary",
                   "Short Advertisement","Product Promotion","Animated Explainer","Teaser / Trailer","Event Highlights",
                   "UGC Videos","Testimonial Videos","Gaming Highlights","Sports Highlights","Travel / Lifestyle Reels",
                   "Music Video Snippets","Meme / Trend Editing",]}


class VideoEditingRequirement(BaseModel):

    video_category: Literal["Long-form", "Short-form"]
    content_type: str
    duration: str
    editing_techniques: list[str] = Field(description="Editing techniques relevant to the requested video.")

    #This checks whether the generated content type belongs to the selected video category.
    @model_validator(mode="after")
    def validate_content_type(self):
        available_types = VIDEO_CONTENT_TYPES[self.video_category]

        if self.content_type not in available_types:
            raise ValueError("Invalid content type")

        return self

EDITOR_COUNTRIES_BY_REGION = {
    "North America": ["United States","Canada",],

    "Latin America": ["Brazil","Mexico","Argentina","Colombia","Chile","Peru","Ecuador","Uruguay","Costa Rica","Panama","Guatemala","Dominican Republic",],

    "Europe":        ["United Kingdom","Germany","France","Italy","Spain","Netherlands","Switzerland","Sweden","Norway","Denmark","Finland",
    "Ireland","Belgium","Austria","Portugal","Poland","Czechia","Greece","Romania","Ukraine",],

    "Africa":        ["South Africa","Nigeria","Kenya","Ghana","Egypt","Morocco","Ethiopia","Tanzania","Uganda","Tunisia",],

    "East Asia":     ["China","Japan","South Korea","Mongolia",],

    "South Asia":    ["India","Pakistan","Bangladesh","Sri Lanka","Nepal","Bhutan","Maldives","Afghanistan",],

    "Southeast Asia":["Philippines","Indonesia","Vietnam","Thailand","Malaysia","Singapore","Cambodia","Laos","Myanmar","Brunei","Timor-Leste",],

    "Middle East / "
    "West Asia":     ["United Arab Emirates","Saudi Arabia","Qatar","Kuwait","Bahrain","Oman","Israel","Jordan","Lebanon","Turkey",],

    "Central Asia":  ["Kazakhstan","Uzbekistan","Kyrgyzstan","Tajikistan","Turkmenistan",],

    "Oceania":       ["Australia","New Zealand","Fiji",],}

class EditorLocation(BaseModel):
    editor_region: str
    editor_country: str

location = EditorLocation(editor_region="Europe",editor_country="Germany")   

def process_video_request(video_category,content_type,editor_region,editor_country,duration,project_description, history):

    SYSTEM_PROMPT = """
You are a professional AI video editing assistant.

Analyze the user's video editing requirements and identify:
- Video category
- Content type
- Relevant editing techniques

Use the user's selected options and understand their
additional requirements.

Suggest relevant editing techniques based on the project.

After identifying the requirements, confirm that the
project information has been saved.

Then ask the user:

"Would you like me to find the best-matching video editor
for your current project?"

Return the structured VideoEditingRequirement output, including
the confirmation message and next-step question.
"""


 # 1. Validate editor location
    location = EditorLocation(editor_region=editor_region,editor_country=editor_country)

# 2. Prepare information for Llama
    user_message = f"""

    Conversation so far:
    {history}

    project requirements:
    Video category: {video_category}
    Content type: {content_type}

    Editor region: {location.editor_region}
    Editor country: {location.editor_country}

    Requested final video duration: {duration}

    Project requirements: {project_description}

    Identify the relevant editing techniques.
    """

# 3. Call Llama with structured output
    response = completion(
        model=Ollama_Model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}]+history+
        [{"role": "user", "content": user_message}], api_base=OLLAMA_API_BASE,
        response_format=VideoEditingRequirement)

# 4. Validate and create Pydantic object
    reply = response.choices[0].message.content

    video_request = VideoEditingRequirement.model_validate_json(reply)

    video_request = video_request.model_copy(update={"duration": duration})

    return video_request, location

class EditorProfile(BaseModel):
    editor_name: str
    editor_country: str
    specialization: list[str]
    is_synthetic: bool = True


def recommend_editors_generate(video_request,editor_location,history):

    EDITOR_SYSTEM_PROMPT = """
You are an AI assistant for a professional video editing platform.

Generate realistic fictional video editor profiles based
on the customer's project requirements.

Generate culturally appropriate editor names based on
the selected country.

Identify the editor's professional specializations,
skills and areas of expertise based on the video category
and content type.

IMPORTANT:
- Specializations must describe professional editing skills.
- Match skills to the editor's content type expertise.
- Do not simply copy the customer's requested editing techniques.
- Generate relevant professional capabilities and experience.
- Always set is_synthetic to True.
- Never present fictional editors as real people.

    Finally, ask the customer:

    "Would you like to select this editor for your project,
    or would you like to explore other editors?"

    Return the structured EditorProfile output."""

    user_message = f"""
    Generate ONE realistic fictional video editor profile.

    Selected editor country:
    {editor_location.editor_country}

    Project requirements:
    {video_request.model_dump()} """

#Call Llama to generate structured output editor profile
    response = completion(
        model=Ollama_Model,
        messages=[
            {"role": "system", "content": EDITOR_SYSTEM_PROMPT}]+history+[
            {"role": "user", "content": user_message}], 
        response_format=EditorProfile)

    reply = response.choices[0].message.content

    editor_profile = EditorProfile.model_validate_json(reply)

    return editor_profile

def select_editor(editor_profile, state):

    state["selected_editor"] = editor_profile.model_dump()
    state["stage"] = "estimate_confirmation"

    response = f"""
    Excellent choice!

    You've selected {editor_profile.editor_name}
    from {editor_profile.editor_country}.

    Would you like me to prepare your full
    production estimate?
    """

    return response, state


COUNTRY_BASE_HOURLY_RATE_USD = {
    # North America
    "United States": 40,"Canada": 35,

    # Latin America
    "Brazil": 20,"Mexico": 30,"Argentina": 20,"Colombia": 20,"Chile": 25,"Peru": 15,"Ecuador": 15,"Uruguay": 20,"Costa Rica": 20,
    "Panama": 25,"Guatemala": 15,"Dominican Republic": 15,

    # Europe
    "United Kingdom": 40,"Germany": 40,"France": 35,"Italy": 30,"Spain": 30,"Netherlands": 40,"Switzerland": 50,"Sweden": 40,"Norway": 45,
    "Denmark": 40,"Finland": 35,"Ireland": 40,"Belgium": 35,"Austria": 40,"Portugal": 30,"Poland": 30,"Czechia": 30,"Greece": 25,"Romania": 25,"Ukraine": 20,

    # Africa
    "South Africa": 35,"Nigeria": 15,"Kenya": 15,"Ghana": 15,"Egypt": 15,"Morocco": 15,"Ethiopia": 10,"Tanzania": 10,"Uganda": 10,"Tunisia": 15,

    # East Asia
    "China": 25,"Japan": 35,"South Korea": 35,"Mongolia": 15,

    # South Asia
    "India": 15,"Pakistan": 10,"Bangladesh": 10,"Sri Lanka": 10,"Nepal": 10,"Bhutan": 10,"Maldives": 15,"Afghanistan": 10,

    # Southeast Asia
    "Philippines": 15,"Indonesia": 15,"Vietnam": 15,"Thailand": 15,"Malaysia": 20,"Singapore": 35,"Cambodia": 10,"Laos": 10,
    "Myanmar": 10,"Brunei": 15,"Timor-Leste": 10,

    # Middle East / West Asia
    "United Arab Emirates": 35,"Saudi Arabia": 30,"Qatar": 30,"Kuwait": 25,"Bahrain": 25,"Oman": 20,"Israel": 40,"Jordan": 20,"Lebanon": 20,"Turkey": 25,

    # Central Asia
    "Kazakhstan": 20,"Uzbekistan": 15,"Kyrgyzstan": 10,"Tajikistan": 10,"Turkmenistan": 10,

    # Oceania
    "Australia": 40,"New Zealand": 35,"Fiji": 15,}

class ProductionDetails(BaseModel):
    Video_duration: float = Field(gt=0)
    estimated_editing_hours: float = Field(gt=0)
    software: list[str]
    delivery_days: int = Field(gt=0)
    complexity_level: str
    estimated_cost: float = Field(ge=0)
    currency: str

def generate_production_estimate(video_request,editor_profile,history):

    PRODUCTION_SYSTEM_PROMPT = """
    You are a professional freelance video production estimator.

    Generate realistic production estimates based on:
    - Final video duration.
    - Editing techniques.
    - Project complexity.
    - Selected editor's hourly reference rate.

    IMPORTANT ESTIMATION RULES:

    1. Estimate actual editing working hours, NOT video duration.

    2. Short-form video guidelines:
    - Basic editing: 1-3 hours.
    - Professional editing: 3-6 hours.
    - Advanced editing: 6-12 hours.
    - Heavy VFX or complex animation: 12-20 hours.

    3. Long-form video estimates must consider video duration,
    raw footage, camera angles and editing complexity.

    4. Never inflate editing hours simply because the customer
    requests high-quality editing.

    5. Never assign extremely high working hours without
    specific production requirements that justify them.

    6. Select only the software actually needed for the project.
    Do not list unnecessary alternative software.

    7. Estimate realistic delivery days based on the workload.

    8. Calculate the estimated project cost using:
    Estimated editing hours x Selected editor's hourly rate.

    9. Keep all estimates realistic, consistent and reasonable.

    Return the structured ProductionDetails output only.
    """

    # Get selected editor's country pricing reference
    hourly_rate = COUNTRY_BASE_HOURLY_RATE_USD.get(
        editor_profile.editor_country)

    if hourly_rate is None:
        raise ValueError("Country pricing not available")

    user_message = f"""
    Generate a complete production estimate.

    VIDEO REQUIREMENTS:
    {video_request.model_dump()}

    SELECTED EDITOR:
    {editor_profile.model_dump()}

    PRICING REFERENCE:
    Editor country: {editor_profile.editor_country}
    Reference hourly rate: ${hourly_rate} USD

    Estimate all required production details and
    determine the final project cost.
    """

    # Call Llama for structured production output
    response = completion(model=Ollama_Model,
        messages=[
            {"role": "system", "content": PRODUCTION_SYSTEM_PROMPT},*history,
            {"role": "user", "content": user_message}],response_format=ProductionDetails)

    reply = response.choices[0].message.content

    production_details = ProductionDetails.model_validate_json(reply)

    return production_details

# Generate the complete project report using existing Pydantic data (Python only — no LLM call)

def finalize_project_report(video_request,editor_profile,production_details,history):

    techniques = "\n".join(
        f"- {item}"
        for item in video_request.editing_techniques
    )

    specializations = ", ".join(
        editor_profile.specialization
    )

    software = ", ".join(
        production_details.software
    )

    duration = str(video_request.duration).lstrip(" :").strip()


    report = f"""
# COMPLETE PROJECT REPORT

## 1. Video Requirements

| Field | Details |
|---|---|
| Video Category | {video_request.video_category} |
| Content Type | {video_request.content_type} |
| Duration | {video_request.duration} |
| Editing Techniques | {", ".join(video_request.editing_techniques)} |

## 2. Selected Editor

| Field | Details |
|---|---|
| Editor Name | {editor_profile.editor_name} |
| Editor Country | {editor_profile.editor_country} |
| Specializations | {specializations} |

## 3. Production Estimate

| Field | Estimate |
|---|---|
| Duration | {video_request.duration} |
| Editing Hours | {production_details.estimated_editing_hours} hours |
| Software | {software} |
| Delivery Time | {production_details.delivery_days} days |
| Complexity | {production_details.complexity_level} |

## 4. Estimated Project Cost

# {production_details.currency} {production_details.estimated_cost:,.2f}

---

*This is an AI-generated production estimate.*
"""

    history.append({"role": "assistant","content": report})

    # 3. Ask Llama to generate the next-stage message
    NEXT_STEP_SYSTEM_PROMPT = """
    You are a friendly and professional video editing assistant.

    The customer has already received their complete project report.

    Your next task is to ask the customer for their name
    so you can prepare the final project handoff.

    Explain briefly that after providing their name:
    - A unique project reference token will be generated.
    - The selected editor's email address will be provided.

    STRICT RULES:
    - Never repeat or summarize the project report.
    - Do not mention video requirements, editing techniques,
    editor details or production estimates.
    - Do not generate tables, headings or numbered lists.
    - Do not invent customer information.
    - Keep your response natural, friendly and concise.
    """
    
    user_message = "I've finished reviewing the project report."

    response = completion(
        model=Ollama_Model,
        messages=[
            {"role": "system", "content": NEXT_STEP_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ])

    next_message = response.choices[0].message.content

    history.append({
        "role": "assistant",
        "content": next_message
    })

    return report, next_message, history


def generate_project_handoff(customer_name, editor_profile, history):

    FINAL_HANDOFF_SYSTEM_PROMPT = """
    You are a friendly and professional video editing assistant.

    Generate a short, natural introduction for the customer's
    final project handoff.

    Your message must:
    - Address the customer by their name.
    - Thank them for completing their project setup.
    - Mention their selected editor.

    STRICT RULES:
    - Generate only a short introduction (1-2 sentences).
    - Do not generate a subject line.
    - Do not generate a project token.
    - Do not generate an editor email address.
    - Do not repeat project requirements or production estimates.
    - Do not generate submission instructions.
    - Do not include signatures or placeholders.
    - Do not invent information.
    - Keep the response friendly and professional.
    """

    # 1. Generate customer project token
    clean_name = re.sub(
        r"[^a-zA-Z0-9]", "", customer_name
    ).upper()

    project_token = f"{clean_name}-{secrets.randbelow(9000) + 1000}"

    # 2. Generate fictional editor email for the demo
    editor_slug = re.sub(
        r"[^a-z0-9]+",
        ".",
        editor_profile.editor_name.lower()
    ).strip(".")

    editor_email = f"{editor_slug}@example.com"

    # 3. Prepare information for Llama
    user_message = f"""
    Customer name: {customer_name}

    Selected editor: {editor_profile.editor_name}
    """

    # 4. Generate personalized introduction using Llama
    response = completion(
        model=Ollama_Model,
        messages=[
            {
                "role": "system",
                "content": FINAL_HANDOFF_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        api_base=OLLAMA_API_BASE
    )

    introduction = response.choices[0].message.content.strip()

    # 5. Python assembles the final handoff message
    reply = f"""
{introduction}

## 🔑 {project_token}

**Editor email:** {editor_email}

Please send your project files or links to the editor's email address.
Remember to include your project reference token so your editor
can identify your project.
"""

    # 6. Update conversation history
    history.append({
        "role": "user",
        "content": f"My name is {customer_name}."
    })

    history.append({
        "role": "assistant",
        "content": reply
    })

    return reply, project_token, editor_email, history


def handle_workflow(action, state, data):

    if action == "welcome":
        return user_first_approach(data)

    elif action == "submit_project":
        return process_video_request(data, state)

    elif action == "recommend_editor":
        return recommend_editors_generate(state)

    elif action == "select_editor":
        return select_editor(state, data)

    elif action == "generate_estimate":
        return generate_production_estimate(state)

    elif action == "generate_report":
        return finalize_project_report(state)

    elif action == "handoff":
        return generate_project_handoff(state, data)