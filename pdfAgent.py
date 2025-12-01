
### google adk specific imports
from google.adk.agents import Agent, LlmAgent
from google.adk.apps.app import App
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin
from google.genai import types
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard, Field

### Misc. imports
from pydantic import BaseModel
from pdfFunctions import get_pdf_text_from_artifact


AGENT_URL = "http://localhost" #Change if needed

# Subdivide the user query into concept and text from the pdf. 
# This is used by the root agent to comunicate with the search agent.
class Query(BaseModel):
    concept:str = Field(description="Concept to be searched for.")
    pdf_text:str = Field(description="Text in which the concept will be searched.")
    
retry_config=types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1, # Initial delay before first retry (in seconds)
    http_status_codes=[429, 500, 503, 504] # Retry on these HTTP errors
)

# Side agent that extracts the text from the pdf.
extractor_agent = LlmAgent(
    name="ExtractorAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction= """
    Your sole purpose is to retrieve the pdf text from your artifacts database.
    You will be given a path to a pdf file. You need to run the get_pdf_text_from_artifact
    function to extract the text. Then, you will need to check the status: if it's 'error',
    you must return the string 'CRITICAL ERROR:' appended to the string in 'error_message'.
    Otherwise, you must return the exact text located in 'result'.
    """,
    tools=[get_pdf_text_from_artifact],
    output_key="pdf-text"
)


# Side agent that defines the concept given.
search_agent = LlmAgent(
    name="SearchAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction= """
    You are a concept finder. 
    You are given a text and a concept and you must find its meaning. 
    Find the concept given to you inside of the {pdf_text}.
    You must return its definition AS IS WRITTEN IN THAT TEXT.
    You are forbidden from making up a definition on your own.
    You can use paraphrasing IF AND ONLY IF the text itself does not give you an exact definition, but alludes this concept.
    If the text has no definition for the concept, and the text does not use it, you must inform the user that this concept is not defined in the text.
    Your methodology should be:
        3. Does this concept appear at all in the text? If not, then return a small phrase stating that the concept does not appear in the text.
        1. Is this concept defined in the text? If so, return the definition.
        2. Is this concept used throughout the text? If so, inquire the definition STRICTLY using the text as a base.
    """,
    input_schema=Query,
    output_key="concept-result"
)


### Coordinator (root) agent.
root_agent = Agent(
    name="RootAgent",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    instruction="""
    You are the coordinator agent for a pdf-concept extraction agent.
    From the given query, you must locate two key components:
    - the name of the file
    - the concept you need to research
    
    First, you need to call the extractor agent with this input:
    {
       "filename": name of the file
    }
    
    If the output of the exctractor agent starts with 'CRITICAL ERROR:',
    then you must inform the user that there has been an error. Tell them exactly what the error was (that is, the text next to 'CRITICAL ERROR'). 
    Otherwise, you will call the search_agent with this input:
    {
       "pdf_text": output of the extractor agent
       "concept": concept given by the query
    }
    
    Finally, you must return the {concept-result} given by the search_agent.
    """,
    tools=[
        AgentTool(extractor_agent),
        AgentTool(search_agent)
    ]
)


app = App(
    name='pdf_data_extraction_agent',
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()],
)

card = AgentCard(
    name="PDF concept definer agent",
    url= AGENT_URL,
    description="Extracts definitions from concepts inside PDF files.",
    version="1.0.0",
    default_input_modes= ["text/plain","application/pdf"],
    default_output_modes= ["text/plain"],
    capabilities={},
    skills= []
)

# Launch the agent!
to_a2a(agent=root_agent, agent_card=card)