from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
import os
from dotenv import load_dotenv

# We use ChatGroq from langchain_groq to interact with the Groq API model
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables from the Agent/.env file
# 'load_dotenv' reads key-value pairs from a .env file and can set them as environment variables.
# Inputs: Filepath to the .env file. Outputs: Boolean (True if file was found and loaded).
load_dotenv(dotenv_path="Agent/.env")

# 1. Define the State dictionary
# 'TypedDict' allows us to declare the structure of our state dictionary that passes through nodes.
class AgentState(TypedDict):
    """
    This dictionary defines the data that flows through our Graph.
    - prompt: A string representing the text given by the user at the get-text endpoint.
    - rules: A list of strings representing the extracted rules.
    """
    prompt: str
    rules: List[str]


# 2. Define our Node function
def extract_rules_node(state: AgentState):
    """
    This function acts as a Node in our LangGraph workflow.
    It takes the current state containing the 'prompt', calls the LLM, extracts the rules,
    and returns an updated dictionary indicating the new 'rules'.

    Input: 
      - state (AgentState): A dictionary containing the current execution state (prompt and rules).
    Output: 
      - dict: A dictionary with the key 'rules' corresponding to the updated data 
        (LangGraph will automatically merge this into State).
    """

    # Retrieve the text prompt from the state
    prompt = state["prompt"]

    # Ensure the Groq API key is present
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY environment variable is not set. Using mock rules.")
        return {"rules": ["Mock Rule 1", "Mock Rule 2 due to missing API key"]}

    # Initialize the Language Model using LangChain's ChatGroq integration
    # ChatGroq class creates an interface to Groq's fast LLM endpoints.
    # Inputs: model_name (string), temperature (float, 0-1)
    # Output: An instantiated ChatGroq object that can process messages.
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

        # Prepare messages for the LLM
        # SystemMessage sets the behavior of the AI.
        # HumanMessage contains the user's specific request.
        messages = [
            SystemMessage(content="You are an expert rule extractor. Convert the following text into a list of concise, strict behavioral rules for our system. Return ONLY the rules as plain text, one per line. Do not use emojis, special bullet points, or markdown. Start each line with a standard hyphen '-'."),
            HumanMessage(content=prompt)
        ]

        # invoke() calls the model to generate a response.
        # Input: List of message objects. Output: AIMessage object containing the text response.
        response = llm.invoke(messages)

        # Split the resulting text string into a list of lines using Python's inbuilt split()
        # Input: string separator (here '\n'). Output: List of split strings.
        lines = response.content.split('\n')

        # Clean the extracted lines (strip whitespace and bullet points)
        rules_list = []
        for line in lines:
            cleaned_line = line.strip().lstrip('-').lstrip('*').strip() # strip() removes spaces, lstrip() removes specific characters at the start
            # Ensure it's ascii plain string for Windows terminal compatibility
            cleaned_line = cleaned_line.encode('ascii', 'ignore').decode('ascii')
            if cleaned_line:  # If line is not empty
                rules_list.append(cleaned_line)
    except Exception as e:
        print(f"Error calling LLM: {str(e)}")
        rules_list = ["Error extracting rules"]

    # Print the rules to the terminal as requested
    print("\n" + "="*40)
    print(" EXTRACTED RULES FROM AGENT:")
    print("="*40)
    for index, rule in enumerate(rules_list, start=1):
        print(f"{index}. {rule}")
    print("="*40 + "\n")

    # Return a dictionary with the property we wish to update in the State
    return {"rules": rules_list}


# 3. Build the workflow graph
# StateGraph initializes a new state machine workflow based on our TypedDict architecture.
# Input: Type definition schema (AgentState). Output: StateGraph object.
workflow = StateGraph(AgentState)

# add_node() registers a new node (step) in the graph.
# Inputs: node name (string), node function (callable).
# Outputs: None.
workflow.add_node("extract_rules", extract_rules_node)

# add_edge() defines a path transition from one node to another.
# Inputs: from_node (string), to_node (string).
# START defines the graph's entry point, END defines its exit.
# Outputs: None.
workflow.add_edge(START, "extract_rules")
workflow.add_edge("extract_rules", END)

# compile() finalizes the Graph builder into a Runnable application that can be executed.
# Inputs: None. Output: CompiledGraph runnable.
rule_agent_app = workflow.compile()


def process_prompt_with_agent(prompt_text: str) -> List[str]:
    """
    A helper function to run the compiled graph with the provided user text.
    
    Input:
      - prompt_text (str): The initial user input instruction.
    Output:
      - List[str]: The final list of rules extracted by the agent.
    """
    # Create the initial state dictionary that the graph needs to start processing.
    initial_state = {"prompt": prompt_text, "rules": []}

    # invoke() triggers the execution of the entire graph from START to END.
    # Input: dictionary mapping to AgentState. Output: dictionary of the final computed AgentState.
    final_state = rule_agent_app.invoke(initial_state)

    # We return just the 'rules' key from the final computed state dictionary.
    return final_state["rules"]
