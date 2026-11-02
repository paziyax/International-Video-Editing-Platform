from Backend import *
from pathlib import Path
from copy import deepcopy
import gradio as gr

CUSTOM_CSS = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")

# ====================================================
# 1. INITIAL SESSION STATE
# ====================================================

WELCOME_MESSAGE = """
Welcome! Choose one of the options below to get started.
"""

def initial_workflow_state():
    return {"stage": "welcome","history": [{"role": "assistant", "content": WELCOME_MESSAGE}],
        "video_request": None,
        "editor_location": None,
        "editor_profile": None,
        "selected_editor": None,
        "production_details": None,
        "report": None,
        "seen_editors": [],
        "project_token": None,
        "editor_email": None,}

# =========================================================
# 2. CHAT AND FORMATTING HELPERS
# =========================================================

def add_chat_message(chat, state, role, content):
    chat = list(chat or [])
    chat.append({"role": role, "content": content})
    return chat


def format_video_request(request):
    techniques = ", ".join(request.editing_techniques)

    return f"""
### Your video requirements

| Field | Details |
|---|---|
| Video category | {request.video_category} |
| Content type | {request.content_type} |
| Duration | {request.duration} |
| Editing techniques | {techniques} |

Your project requirements have been recorded.

Would you like me to find the best-matching editor for your project?
"""


def format_editor_profile(profile):
    specializations = ", ".join(profile.specialization)

    return f"""
### Your Recommended Editor

**{profile.editor_name}**

| Field | Details |
|---|---|
| Country | {profile.editor_country} |
| Specializations | {specializations} |
| Synthetic Profile | {profile.is_synthetic} |

Would you like to select this editor or explore another editor?"""


def format_production_details(details):
    software = ", ".join(details.software)

    return f"""
### Your production estimate

| Production detail | Estimate |
|---|---|
| Editing hours | {details.estimated_editing_hours} hours |
| Software | {software} |
| Delivery time | {details.delivery_days} days |
| Complexity | {details.complexity_level} |
| Estimated cost | {details.currency} {details.estimated_cost:,.2f} |

Your production estimate is ready!

Would you like me to generate your complete project report?
"""


# =========================================================
# 3. MAIN WORKFLOW CONTROLLER
# =========================================================

def handle_workflow(action, state, chat, **data):

    state = deepcopy(state or initial_workflow_state())
    chat = list(chat or [])

    try:

        # -----------------------------------------
        # STAGE 1: WELCOME
        # -----------------------------------------

        if action == "welcome":

            first_message = data["first_message"]

            response = user_first_approach(first_message)

            chat = add_chat_message(
                chat, state, "user", first_message
            )

            chat = add_chat_message(
                chat, state, "assistant", response
            )

            state["history"].extend([
                {"role": "user", "content": first_message},
                {"role": "assistant", "content": response}
            ])

            state["stage"] = "start"


        # -----------------------------------------
        # OPEN PROJECT CONFIGURATION
        # -----------------------------------------

        elif action == "open_config":

            response = "Great! Let's configure your video project."

            chat = add_chat_message(
                chat, state, "assistant", response
            )

            state["history"].append({
                "role": "assistant",
                "content": response
            })

            state["stage"] = "configure"


        # -----------------------------------------
        # STAGE 2: PROCESS VIDEO REQUEST
        # -----------------------------------------

        elif action == "submit_project":

            category = data["video_category"]
            content = data["content_type"]
            region = data["editor_region"]
            country = data["editor_country"]
            duration = data["duration"]
            description = data["description"]

            if not duration or not duration.strip():
               raise ValueError("Please enter your desired video duration.")

            if not description.strip():
                raise ValueError("Please describe your video project.")

            project_description = f"""
            Requested final video duration: {duration} .

            Additional project requirements:
            {description}
            """

            # Existing function: Llama + VideoEditingRequirement
            video_request, location = process_video_request(
                category,
                content,
                region,
                country,
                duration,
                project_description,
                state["history"]
            )

            # Save structured results
            state["video_request"] = video_request.model_dump()
            state["editor_location"] = location.model_dump()
            state["video_duration"] = duration

            # Update history
            user_context = f"""
            Video category: {category}
            Content type: {content}
            Editor region: {region}
            Editor country: {country}
            Duration: {duration} 
            Requirements: {description}
            """

            state["history"].extend([
                {"role": "user", "content": user_context},
                {
                    "role": "assistant",
                    "content": video_request.model_dump_json()
                }
            ])

            # Display results
            chat = add_chat_message(
                chat, state, "user",
                f"Project submitted: {content}, {duration} ."
            )

            chat = add_chat_message(
                chat, state, "assistant",
                format_video_request(video_request)
            )

            state["stage"] = "discovery"


        # -----------------------------------------
        # STAGE 3: RECOMMEND EDITOR
        # -----------------------------------------

        elif action in ["find_editor", "another_editor"]:

            video_request = VideoEditingRequirement.model_validate(
                state["video_request"]
            )

            location = EditorLocation.model_validate(
                state["editor_location"]
            )

            # Avoid recommending an already rejected editor
            if action == "another_editor":
                previous_name = state["editor_profile"]["editor_name"]

                state["history"].append({
                    "role": "user",
                    "content": (
                        f"I want another editor. Do not recommend "
                        f"{previous_name} or previously rejected editors."
                    )
                })

                chat = add_chat_message(
                    chat, state, "user",
                    "I'd like to explore another editor."
                )

            else:
                chat = add_chat_message(chat, state, "user",
                    "Let's find the best-matching editor for my project.")
                
                state["history"].append({
                    "role": "user",
                    "content": "Please recommend a matching editor."})
                
            # Existing function: Llama + EditorProfile
            editor_profile = recommend_editors_generate(
                video_request,
                location,
                state["history"]
            )

            state["editor_profile"] = editor_profile.model_dump()

            state["seen_editors"].append(
                editor_profile.editor_name
            )

            state["history"].append({
                "role": "assistant",
                "content": editor_profile.model_dump_json()
            })

            chat = add_chat_message(
                chat, state, "assistant",
                format_editor_profile(editor_profile)
            )

            state["stage"] = "editor_choice"


        # -----------------------------------------
        # STAGE 4: SELECT EDITOR
        # -----------------------------------------

        elif action == "select_editor":

            profile = EditorProfile.model_validate(
                state["editor_profile"]
            )

            state["selected_editor"] = profile.model_dump()

            chat = add_chat_message(
                chat, state, "user",
                f"I choose {profile.editor_name}."
            )

            response = f"""
Excellent choice!

You've selected {profile.editor_name}
from {profile.editor_country}.

Would you like me to prepare your complete production estimate?
"""

            chat = add_chat_message(
                chat, state, "assistant", response
            )

            state["history"].extend([
                {"role": "user", "content": f"I choose {profile.editor_name}."},
                {"role": "assistant", "content": response}
            ])

            state["stage"] = "estimate_choice"


        # -----------------------------------------
        # STAGE 5: GENERATE PRODUCTION ESTIMATE
        # -----------------------------------------

        elif action == "generate_estimate":

            video_request = VideoEditingRequirement.model_validate(
                state["video_request"]
            )

            editor_profile = EditorProfile.model_validate(
                state["selected_editor"]
            )

            state["history"].append({
                "role": "user",
                "content": "Please generate my full production estimate."
            })

            # Existing function: Llama + ProductionDetails
            production_details = generate_production_estimate(
                video_request,
                editor_profile,
                state["history"]
            )

            state["production_details"] = (
                production_details.model_dump()
            )

            state["history"].append({
                "role": "assistant",
                "content": production_details.model_dump_json()
            })

            chat = add_chat_message(
                chat, state, "user",
                "Please prepare my production estimate."
            )

            chat = add_chat_message(
                chat, state, "assistant",
                format_production_details(production_details)
            )

            state["stage"] = "report_choice"


        # -----------------------------------------
        # STAGE 6: FINALIZE PROJECT REPORT
        # -----------------------------------------

        elif action == "generate_report":

            video_request = VideoEditingRequirement.model_validate(
                state["video_request"]
            )

            editor_profile = EditorProfile.model_validate(
                state["selected_editor"]
            )

            production_details = ProductionDetails.model_validate(
                state["production_details"]
            )

            # Existing function:
            # Python assembles report.
            # Llama generates the next-step message.
            report, next_message, updated_history = (
                finalize_project_report(
                    video_request,
                    editor_profile,
                    production_details,
                    state["history"]
                )
            )

            state["report"] = report
            state["history"] = updated_history

            chat = add_chat_message(
                chat, state, "user",
                "Please generate my complete project report."
            )

            chat = add_chat_message(
                chat, state, "assistant",
                f"{report}\n\n{next_message}"
            )

            state["stage"] = "handoff"


        # -----------------------------------------
        # STAGE 7: CUSTOMER HANDOFF
        # -----------------------------------------

        elif action == "handoff":

            customer_name = data["customer_name"].strip()

            if not customer_name:
                raise ValueError("Please enter your name.")

            editor_profile = EditorProfile.model_validate(
                state["selected_editor"]
            )

            # Existing function: Python token + Llama message
            reply, token, email, updated_history = (
                generate_project_handoff(
                    customer_name,
                    editor_profile,
                    state["history"]
                )
            )

            state["customer_name"] = customer_name
            state["project_token"] = token
            state["editor_email"] = email
            state["history"] = updated_history

            chat = add_chat_message(
                chat, state, "user",
                f"My name is {customer_name}."
            )

            chat = add_chat_message(
             chat, state, "assistant",reply)

            state["stage"] = "completed"


        # -----------------------------------------
        # EDIT REQUIREMENTS
        # -----------------------------------------

        elif action == "edit_requirements":

            response = "No problem! Let's update your project requirements."

            chat = add_chat_message(
                chat, state, "assistant", response
            )

            state["history"].append({
                "role": "assistant",
                "content": response
            })

            # Clear all downstream results
            state["video_request"] = None
            state["editor_location"] = None
            state["editor_profile"] = None
            state["selected_editor"] = None
            state["production_details"] = None
            state["report"] = None
            state["stage"] = "configure"


        # -----------------------------------------
        # START A NEW PROJECT
        # -----------------------------------------

        elif action == "reset":

            state = initial_workflow_state()

            chat = [
                {"role": "assistant", "content": WELCOME_MESSAGE}
            ]

            state["stage"] = "welcome"


        else:
            raise ValueError(f"Unknown workflow action: {action}")

    except Exception as error:

        chat = add_chat_message(
            chat, state, "assistant",
            f"Something went wrong: {error}"
        )

    return render_ui(chat, state)


# =========================================================
# 4. CONTROL WHICH GRADIO PANELS ARE VISIBLE
# =========================================================

def render_ui(chat, state):

    stage = state["stage"]

    return (
        chat,
        state,

        gr.update(visible=stage == "welcome"),
        gr.update(visible=stage == "start"),
        gr.update(visible=stage == "configure"),
        gr.update(visible=stage == "discovery"),
        gr.update(visible=stage == "editor_choice"),
        gr.update(visible=stage == "estimate_choice"),
        gr.update(visible=stage == "report_choice"),
        gr.update(visible=stage == "handoff"),
        gr.update(visible=stage == "completed"),
    )


# =========================================================
# 5. DYNAMIC DROPDOWNS
# =========================================================

def update_content_types(category):

    choices = VIDEO_CONTENT_TYPES.get(category, [])

    return gr.update(
        choices=choices,
        value=choices[0] if choices else None
    )


def update_editor_countries(region):

    choices = EDITOR_COUNTRIES_BY_REGION.get(region, [])

    return gr.update(
        choices=choices,
        value=choices[0] if choices else None
    )

# =========================================================
# 7. BUILD THE GRADIO APPLICATION
# =========================================================

INITIAL_CHAT = [
    {"role": "assistant", "content": WELCOME_MESSAGE}
]

DEFAULT_REGION = "South Asia"
DEFAULT_COUNTRY = "Sri Lanka"

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="indigo",
        neutral_hue="slate"
    ),
    css=CUSTOM_CSS,
    title="International Freelance Video Editing Platform"
) as demo:

    # MAIN HEADER
    gr.HTML("""
        <div id="hero">
            <h1>International Freelance Video Editing Platform</h1>
            <span id="synthetic-label">
                SYNTHETIC-GENERATED DATASET
            </span>
            <p>AI-powered editor recommendations and production estimates</p>
        </div>
    """)

    # ONE CHATBOT FOR THE ENTIRE APPLICATION
    chatbot = gr.Chatbot(
        value=INITIAL_CHAT,
        type="messages",
        height=560,
        show_label=False,
        layout="bubble",
        group_consecutive_messages=False
    )

    # SESSION STATE
    workflow_state = gr.State(initial_workflow_state())

    # -----------------------------------------------------
    # STAGE 1: THREE CONVERSATION STARTERS
    # -----------------------------------------------------

    with gr.Column(visible=True) as starter_panel:

        gr.Markdown("### How can we help you today?")

        with gr.Row():
            starter_1 = gr.Button(
                "Hi! How can you help me?"
            )

            starter_2 = gr.Button(
                "What editing styles can you do?"
            )

            starter_3 = gr.Button(
                "I need help with my video."
            )


    # LET'S GET STARTED BUTTON

    with gr.Column(visible=False) as start_panel:

        start_button = gr.Button(
            "Let's get started",
            variant="primary",
            size="lg"
        )


    # -----------------------------------------------------
    # STAGE 2: CONFIGURE VIDEO PROJECT
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as project_panel:

        gr.Markdown("## Configure your video project")

        video_category = gr.Dropdown(
            choices=list(VIDEO_CONTENT_TYPES.keys()),
            value="Long-form",
            label="Video category"
        )

        content_type = gr.Dropdown(
            choices=VIDEO_CONTENT_TYPES["Long-form"],
            value="Podcast / Interview",
            label="Content type"
        )

        editor_region = gr.Dropdown(
            choices=list(EDITOR_COUNTRIES_BY_REGION.keys()),
            value=DEFAULT_REGION,
            label="Editor region"
        )

        editor_country = gr.Dropdown(
            choices=EDITOR_COUNTRIES_BY_REGION[DEFAULT_REGION],
            value=DEFAULT_COUNTRY,
            label="Editor country"
        )

        duration = gr.Textbox(
            label="Requested Final Video Duration",
            placeholder="e.g. 2 minutes 30 seconds, 40 seconds, or 1 hour 15 minutes",
            info="Enter the desired length of your finished video.")

        
        project_description = gr.Textbox(
            label="Describe your project",
            placeholder=(
                "Describe your editing requirements, "
                "techniques, audio, visual style and footage..."
            ),
            lines=5
        )

        submit_project = gr.Button(
            "Submit project requirements",
            variant="primary"
        )


    # -----------------------------------------------------
    # STAGE 3: FIND EDITOR
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as discovery_panel:

        find_editor_button = gr.Button(
            "Find my best-matching editor",
            variant="primary"
        )

        edit_from_discovery = gr.Button(
            "Modify my requirements",
            variant="secondary"
        )


    # -----------------------------------------------------
    # STAGE 4: EDITOR SELECTION
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as editor_panel:

        choose_editor_button = gr.Button(
            "Choose this editor",
            variant="primary"
        )

        another_editor_button = gr.Button(
            "Find another editor",
            variant="secondary"
        )

        edit_from_editor = gr.Button(
            "Modify my requirements"
        )


    # -----------------------------------------------------
    # STAGE 5: ESTIMATE CONFIRMATION
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as estimate_panel:

        estimate_button = gr.Button(
            "Generate full production estimate",
            variant="primary"
        )

        edit_from_estimate = gr.Button(
            "Modify my requirements"
        )


    # -----------------------------------------------------
    # STAGE 6: FULL PROJECT REPORT
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as report_panel:

        report_button = gr.Button(
            "Generate full project report",
            variant="primary"
        )

        edit_from_report = gr.Button(
            "Modify my requirements"
        )


    # -----------------------------------------------------
    # STAGE 7: CUSTOMER HANDOFF
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as handoff_panel:

        customer_name = gr.Textbox(
            label="Your full name",
            placeholder="Enter your name"
        )

        handoff_button = gr.Button(
            "Complete project handoff",
            variant="primary"
        )


    # -----------------------------------------------------
    # COMPLETION
    # -----------------------------------------------------

    with gr.Column(visible=False, elem_classes="action-panel") as complete_panel:

        gr.Markdown("### Your project handoff is complete!")

        new_project_button = gr.Button(
            "Start a new project",
            variant="primary"
        )


    # ALL OUTPUTS RETURNED BY THE MAIN CONTROLLER

    UI_OUTPUTS = [
        chatbot,
        workflow_state,
        starter_panel,
        start_panel,
        project_panel,
        discovery_panel,
        editor_panel,
        estimate_panel,
        report_panel,
        handoff_panel,
        complete_panel
    ]


    # =====================================================
    # 8. GRADIO EVENT CONNECTIONS
    # =====================================================

    # STAGE 1: Conversation starters

    starter_1.click(
        fn=lambda chat, state: handle_workflow(
            "welcome", state, chat,
            first_message="Hi! How can you help me?"
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )

    starter_2.click(
        fn=lambda chat, state: handle_workflow(
            "welcome", state, chat,
            first_message="What editing styles can you do?"
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )

    starter_3.click(
        fn=lambda chat, state: handle_workflow(
            "welcome", state, chat,
            first_message="I need help with my video."
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # LET'S GET STARTED

    start_button.click(
        fn=lambda chat, state: handle_workflow(
            "open_config", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # DYNAMIC CONTENT TYPE DROPDOWN

    video_category.change(
        fn=update_content_types,
        inputs=[video_category],
        outputs=[content_type]
    )


    # DYNAMIC COUNTRY DROPDOWN

    editor_region.change(
        fn=update_editor_countries,
        inputs=[editor_region],
        outputs=[editor_country]
    )


    # STAGE 2: SUBMIT PROJECT

    submit_project.click(
        fn=lambda category, content, region, country,
                  duration_value, description, chat, state:

            handle_workflow(
                "submit_project",
                state,
                chat,
                video_category=category,
                content_type=content,
                editor_region=region,
                editor_country=country,
                duration=duration_value,
                description=description
            ),

        inputs=[
            video_category,
            content_type,
            editor_region,
            editor_country,
            duration,
            project_description,
            chatbot,
            workflow_state
        ],

        outputs=UI_OUTPUTS
    )


    # STAGE 3: FIND EDITOR

    find_editor_button.click(
        fn=lambda chat, state: handle_workflow(
            "find_editor", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # STAGE 4: SELECT EDITOR

    choose_editor_button.click(
        fn=lambda chat, state: handle_workflow(
            "select_editor", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # STAGE 4: FIND ANOTHER EDITOR

    another_editor_button.click(
        fn=lambda chat, state: handle_workflow(
            "another_editor", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # STAGE 5: GENERATE ESTIMATE

    estimate_button.click(
        fn=lambda chat, state: handle_workflow(
            "generate_estimate", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # STAGE 6: GENERATE REPORT

    report_button.click(
        fn=lambda chat, state: handle_workflow(
            "generate_report", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # STAGE 7: CUSTOMER HANDOFF

    handoff_button.click(
        fn=lambda name, chat, state: handle_workflow(
            "handoff",
            state,
            chat,
            customer_name=name
        ),
        inputs=[
            customer_name,
            chatbot,
            workflow_state
        ],
        outputs=UI_OUTPUTS
    )


    # MODIFY REQUIREMENTS BUTTONS

    edit_from_discovery.click(
        fn=lambda chat, state: handle_workflow(
            "edit_requirements", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )

    edit_from_editor.click(
        fn=lambda chat, state: handle_workflow(
            "edit_requirements", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )

    edit_from_estimate.click(
        fn=lambda chat, state: handle_workflow(
            "edit_requirements", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )

    edit_from_report.click(
        fn=lambda chat, state: handle_workflow(
            "edit_requirements", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


    # START NEW PROJECT

    new_project_button.click(
        fn=lambda chat, state: handle_workflow(
            "reset", state, chat
        ),
        inputs=[chatbot, workflow_state],
        outputs=UI_OUTPUTS
    )


# =========================================================
# 9. LAUNCH
# =========================================================

demo.queue().launch(inbrowser=True, )