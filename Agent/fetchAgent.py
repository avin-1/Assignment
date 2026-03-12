import os.path
from typing import TypedDict, List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from langgraph.graph import StateGraph, START, END

# We need both responses readonly and body readonly (to get the Question titles)
SCOPES = [
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/forms.body.readonly'
]

def get_forms_service():
    """Authenticate returning the Google Forms API service instance."""
    creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Agent/service_account.json')
    if not os.path.exists(creds_file):
        creds_file = 'Agent/service_account.json'
        if not os.path.exists(creds_file):
            raise Exception(f"Service account file {creds_file} missing. Please configure GOOGLE_APPLICATION_CREDENTIALS in .env.")
    
    creds = ServiceAccountCredentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build('forms', 'v1', credentials=creds)

# ----------------------------------------------------
# 1. Define the Agent State Memory
# ----------------------------------------------------
class FetchAgentState(TypedDict):
    form_id: str
    raw_responses: List[Dict[str, Any]]
    formatted_responses: List[Dict[str, Any]]

# ----------------------------------------------------
# 2. API Node: Fetch Responses from Google Forms
# ----------------------------------------------------
def fetch_responses_node(state: FetchAgentState):
    """Hits the Google Forms API to retrieve all current submissions for the given form_id."""
    form_id = state["form_id"]
    service = get_forms_service()
    
    try:
        # Get the actual responses
        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        # We also need to fetch the form definition to map Question IDs to Question Titles
        form_definition = service.forms().get(formId=form_id).execute()
        
        # Build a lookup dictionary for question ID -> Question Title
        question_lookup = {}
        for item in form_definition.get('items', []):
            if 'questionItem' in item:
                q_id = item['questionItem']['question']['questionId']
                question_lookup[q_id] = item['title']
                
        # Attach the lookup so the formatting node can use it
        return {"raw_responses": [{"submission": r, "lookup": question_lookup} for r in responses]}
    except Exception as e:
        print(f"Error fetching responses: {str(e)}")
        return {"raw_responses": []}

# ----------------------------------------------------
# 3. Formatting Node: Parse and Print Responses
# ----------------------------------------------------
def format_responses_node(state: FetchAgentState):
    """Turns the raw Google API JSON into a list of dictionaries and prints to the terminal."""
    raw_data = state.get("raw_responses", [])
    
    if not raw_data:
        print("\n" + "="*50)
        print(" NO RESPONSES FOUND (OR HTTP ERROR)")
        print("="*50 + "\n")
        return {"formatted_responses": []}
        
    formatted_list = []
    
    print("\n" + "="*50)
    print(f" FETCHED {len(raw_data)} RESPONSES FROM FORM:")
    print("="*50)
    
    for idx, data in enumerate(raw_data, 1):
        submission = data["submission"]
        lookup = data["lookup"]
        submit_time = submission.get("createTime", "Unknown Time")
        answers = submission.get("answers", {})
        
        response_dict = {"Submit Time": submit_time}
        
        print(f"--- Response #{idx} (Submitted: {submit_time}) ---")
        
        if not answers:
            print("  [Empty Submission]")
        
        for q_id, answer_obj in answers.items():
            question_title = lookup.get(q_id, f"Unknown Question ({q_id})")
            
            # Google Forms answers are nested inside textAnswers.answers[0].value
            val_list = answer_obj.get('textAnswers', {}).get('answers', [])
            answer_values = [v.get('value', '') for v in val_list]
            final_answer = ", ".join(answer_values)
            
            response_dict[question_title] = final_answer
            print(f"  Q: {question_title}\n  A: {final_answer}\n")
            
        formatted_list.append(response_dict)
        
    print("="*50 + "\n")
    
    return {"formatted_responses": formatted_list}

# ----------------------------------------------------
# 4. Build and Compile the Workflow
# ----------------------------------------------------
workflow = StateGraph(FetchAgentState)

workflow.add_node("fetch_responses", fetch_responses_node)
workflow.add_node("format_responses", format_responses_node)

workflow.add_edge(START, "fetch_responses")
workflow.add_edge("fetch_responses", "format_responses")
workflow.add_edge("format_responses", END)

fetch_agent_app = workflow.compile()

# ----------------------------------------------------
# 5. Helper Invoker
# ----------------------------------------------------
def fetch_and_print_responses(form_id: str) -> List[Dict[str, Any]]:
    """
    Triggers the fetchAgent workflow for a specific Google Form ID.
    Returns the parsed strings for the endpoint to return as JSON.
    """
    initial_state = {"form_id": form_id, "raw_responses": [], "formatted_responses": []}
    final_state = fetch_agent_app.invoke(initial_state)
    return final_state["formatted_responses"]
