import os
import json
from typing import List, Dict, TypedDict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------
# 1. Google Forms Authentication & Scopes
# ----------------------------------------------------
# Form CREATION uses personal OAuth (user's Drive quota, no quota limit issues)
# Form READING uses Service Account (no popup for end users)
FORM_SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/drive.file'   # grants access to files created by this app
]
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'Agent/token.json'
SA_FILE = 'Agent/service_account.json'

# The Service Account email that needs reader access to fetch responses
SERVICE_ACCOUNT_EMAIL = "form-automation-bot@eng-handbook-452518-d2.iam.gserviceaccount.com"

def get_forms_service():
    """Authenticate via personal OAuth token for form creation."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, FORM_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception(
                "token.json missing or invalid. Run test_persistent_oauth.py once to authenticate."
            )
    forms_svc = build('forms', 'v1', credentials=creds)
    # drive.file scope is part of forms.body, so we can use same creds for sharing
    drive_svc = build('drive', 'v3', credentials=creds)
    return forms_svc, drive_svc


# ----------------------------------------------------
# 2. Define the Agent State Memory
# ----------------------------------------------------
class FormAgentState(TypedDict):
    rules: List[str]
    questionnaire_schema: List[Dict]
    form_id: str
    form_url: str


# ----------------------------------------------------
# 3. LLM Node: Generate Questionnaire from Rules
# ----------------------------------------------------
def generate_questionnaire_node(state: FormAgentState):
    """
    Reads the HR rules from memory and invokes ChatGroq 
    to create a structured candidate screening questionnaire JSON.
    """
    rules = state.get("rules", [])
    rules_text = "\n".join([f"- {r}" for r in rules])
    
    system_prompt = """
# Instructions for the Question Generator Agent

## Objective
Generate a candidate screening questionnaire using the HR rules constraints. 
Return ONLY valid JSON matching the exact schema below. Do not wrap in ```json markdown blocks.

Output an array of JSON objects representing questions. Each object must have:
- "title": (string) The question text
- "type": (string) Must be one of ["SHORT_TEXT", "PARAGRAPH_TEXT", "RADIO", "CHECKBOX"]
- "options": (array of strings) ONLY required if type is RADIO or CHECKBOX. Omit otherwise.
- "required": (boolean) Whether the question is mandatory.

# Question Categories Constraints
1. Basic Information [Compulsory]: Full Name, Phone, Email
2. Employment Status [Compulsory]: Currently employed? (RADIO: Yes, No), Current notice period (RADIO: Immediate, 15 days, 30 days, 60 days)
3. Custom Rules [Conditional]: Create specific questions that enforce the following HR rules:
{HR_RULES}

# Limits
Ensure at least 5 questions and at most 15 questions. 
Respond exclusively with the raw JSON array.
"""
    # Inject the rules dynamically into the prompt
    sys_msg = system_prompt.replace("{HR_RULES}", rules_text)

    # Initialize the LLM (Lower temperature for rigid JSON outputs)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("GROQ_API_KEY not found in environment variables.")
        
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content="Please generate the JSON schema for the candidate screening questionnaire.")
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Clean up markdown if the LLM leaked it despite instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        # Parse the JSON string into standard python lists/dicts
        schema = json.loads(content.strip())
        return {"questionnaire_schema": schema}
        
    except Exception as e:
        print(f"Error generating questionnaire: {e}\nRaw Output: {response.content}")
        # Supply a fallback safe schema if the LLM JSON parsing fails
        fallback_schema = [
            {"title": "Full Name", "type": "SHORT_TEXT", "required": True},
            {"title": "Email Address", "type": "SHORT_TEXT", "required": True},
            {"title": f"Do you agree to: {rules[0] if rules else 'Our rules'}?", "type": "RADIO", "options": ["Yes", "No"], "required": True}
        ]
        return {"questionnaire_schema": fallback_schema}

# ----------------------------------------------------
# 4. API Node: Create Google Form
# ----------------------------------------------------
def create_google_form_node(state: FormAgentState):
    """
    Creates a Google Form under the personal account (uses user's Drive quota),
    then shares it with the Service Account so fetchAgent can read responses.
    """
    service, drive_service = get_forms_service()
    schema = state.get("questionnaire_schema", [])

    # Create the Form using the Forms API (works for personal OAuth accounts)
    form_body = {
        "info": {
            "title": "Initial Candidate Screening",
            "documentTitle": "HR Application Form"
        }
    }
    created_form = service.forms().create(body=form_body).execute()
    form_id = created_form.get('formId')
    responder_url = created_form.get('responderUri')

    # Build the Question Update Requests dynamically
    requests_list = []
    
    for index, q_data in enumerate(schema):
        question_item = {}
        q_type = q_data.get("type", "SHORT_TEXT")
        is_required = q_data.get("required", True)
        
        if q_type == "SHORT_TEXT":
            question_item = { "question": { "required": is_required, "textQuestion": { "paragraph": False } } }
        elif q_type == "PARAGRAPH_TEXT":
            question_item = { "question": { "required": is_required, "textQuestion": { "paragraph": True } } }
        elif q_type == "RADIO":
            choices = [{"value": opt} for opt in q_data.get("options", ["Yes", "No"])]
            question_item = { "question": { "required": is_required, "choiceQuestion": { "type": "RADIO", "options": choices } } }
        elif q_type == "CHECKBOX":
            choices = [{"value": opt} for opt in q_data.get("options", ["Accept"])]
            question_item = { "question": { "required": is_required, "choiceQuestion": { "type": "CHECKBOX", "options": choices } } }
        else:
            question_item = { "question": { "required": is_required, "textQuestion": { "paragraph": False } } }
            
        requests_list.append({
            "createItem": {
                "item": {
                    "title": q_data.get("title", "Question"),
                    "questionItem": question_item
                },
                "location": { "index": index }
            }
        })
    
    if requests_list:
        service.forms().batchUpdate(formId=form_id, body={"requests": requests_list}).execute()
        
    # --- SHARE WITH SERVICE ACCOUNT so it can read responses without popups ---
    try:
        drive_service.permissions().create(
            fileId=form_id,
            body={
                'type': 'user',
                'role': 'reader',
                'emailAddress': SERVICE_ACCOUNT_EMAIL
            },
            fields='id',
            sendNotificationEmail=False
        ).execute()
        print(f"\n[+] Shared form with Service Account: {SERVICE_ACCOUNT_EMAIL}")
    except Exception as e:
        print(f"\n[-] Could not share with Service Account (responses may not be fetchable): {e}")
        
    print("\n" + "*"*50)
    print(" FORM AGENT GENERATION SUCCESS!")
    print(f" Screening Questionnaire URL:\n{responder_url}")
    print("*"*50 + "\n")

    return {"form_id": form_id, "form_url": responder_url}


# ----------------------------------------------------
# 5. Build and Compile the Workflow
# ----------------------------------------------------
workflow = StateGraph(FormAgentState)

workflow.add_node("generate_questionnaire", generate_questionnaire_node)
workflow.add_node("create_google_form", create_google_form_node)

workflow.add_edge(START, "generate_questionnaire")
workflow.add_edge("generate_questionnaire", "create_google_form")
workflow.add_edge("create_google_form", END)

form_agent_app = workflow.compile()

# ----------------------------------------------------
# 6. Helper Invoker
# ----------------------------------------------------
def process_rules_into_form(rules: List[str]) -> Dict[str, str]:
    """
    Pipes the extracted rules into the Form Agent's memory and fully executes it.
    Input: List of rule strings.
    Output: Dictionary with form_id and form_url.
    """
    initial_state = {"rules": rules, "questionnaire_schema": [], "form_id": "", "form_url": ""}
    final_state = form_agent_app.invoke(initial_state)
    
    return {
        "formId": final_state["form_id"],
        "responderUri": final_state["form_url"]
    }
