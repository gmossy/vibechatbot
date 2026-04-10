import os
import subprocess
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import docx
import logfire
from tenacity import retry, stop_after_attempt, wait_exponential

@tool
def execute_terminal(command: str) -> str:
    """
    Executes a bash terminal command on the host OS and returns output.
    
    BEST PRACTICE: Use this for environment exploration, dependency installation, 
    and running automated tests. The output is monitored by a Verifier node.
    """
    with logfire.span("tool_execute_terminal", command=command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout if result.stdout else result.stderr
            return f"Execution returned:\n{output}" if output else "Command executed silently."
        except Exception as e:
            logfire.error("Terminal execution failed: {e}", e=e)
            return f"Failed to execute command: {str(e)}"

@tool
def read_local_file(filepath: str) -> str:
    """
    Reads the complete UTF-8 content of a specific local file.
    Use this to analyze existing source code or logs.
    """
    with logfire.span("tool_read_file", filepath=filepath):
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except Exception as e:
            logfire.error("File read failed: {e}", e=e)
            return f"Failed to read file: {str(e)}"

@tool
def write_local_file(filepath: str, content: str) -> str:
    """
    Writes or overwrites a local file on the host machine.
    Automatically creates parent directories if they are missing.
    """
    with logfire.span("tool_write_file", filepath=filepath):
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            logfire.error("File write failed: {e}", e=e)
            return f"Failed to write file: {str(e)}"

@tool
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def web_search(query: str) -> str:
    """
    Performs a live search via DuckDuckGo for real-time internet information.
    Best for current events, API documentation lookups, or troubleshooting codes.
    """
    with logfire.span("tool_web_search", query=query):
        try:
            results = DDGS().text(query, max_results=3)
            return "\n".join([f"{r['title']}: {r['body']}" for r in results])
        except Exception as e:
            logfire.error("Web search failed: {e}", e=e)
            raise e # Reraise so tenacity can catch it and retry

GENERATED_DIR = "./generated_files"
os.makedirs(GENERATED_DIR, exist_ok=True)

@tool
def calculator(expression: str) -> str:
    """
    Evaluates a mathematical expression using specialized local logic.
    Supports complex arithmetic and basic math functions.
    """
    try:
        # Safe constraint local evaluation
        allowed_names = {"__builtins__": None}
        result = eval(expression, allowed_names, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

@tool
def create_pdf(text: str, filename: str) -> str:
    """
    Generates a localized PDF report based on the provided text.
    Returns the absolute path to the generated document.
    """
    with logfire.span("tool_create_pdf", filename=filename):
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        
        filepath = os.path.join(GENERATED_DIR, filename)
        try:
            c = canvas.Canvas(filepath, pagesize=letter)
            y = 750
            for line in text.split('\n'):
                c.drawString(50, y, line)
                y -= 15
                if y < 50:
                    c.showPage()
                    y = 750
            c.save()
            return f"Successfully created PDF at {filepath}"
        except Exception as e:
            logfire.error("PDF creation failed: {e}", e=e)
            return f"Error creating PDF: {str(e)}"

@tool
def create_word(text: str, filename: str) -> str:
    """
    Generates a Microsoft Word (.docx) document.
    Ideal for structured reports, articles, or documentation exports.
    """
    with logfire.span("tool_create_word", filename=filename):
        if not filename.endswith(".docx"):
            filename += ".docx"
            
        filepath = os.path.join(GENERATED_DIR, filename)
        try:
            doc = docx.Document()
            doc.add_paragraph(text)
            doc.save(filepath)
            return f"Successfully created Word Document at {filepath}"
        except Exception as e:
            logfire.error("Word creation failed: {e}", e=e)
            return f"Error creating Word Document: {str(e)}"

# Master list of all tools
agent_tools = [calculator, create_pdf, create_word, web_search, execute_terminal, read_local_file, write_local_file]
