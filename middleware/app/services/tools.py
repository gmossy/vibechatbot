import os
import subprocess
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import docx

@tool
def execute_terminal(command: str) -> str:
    """Executes a bash terminal command on the host OS and returns the output. Use this to run code, explore directories, or install dependencies!"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return f"Execution returned:\n{output}" if output else "Command executed silently."
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

@tool
def read_local_file(filepath: str) -> str:
    """Reads the complete content of a specific local file."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Failed to read file: {str(e)}"

@tool
def write_local_file(filepath: str, content: str) -> str:
    """Writes or overwrites a local file on the host machine explicitly with the target content."""
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"

@tool
def web_search(query: str) -> str:
    """Search the global live internet for current web information."""
    try:
        results = DDGS().text(query, max_results=3)
        return "\n".join([f"{r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Web search failed: {e}"

GENERATED_DIR = "./generated_files"
os.makedirs(GENERATED_DIR, exist_ok=True)

@tool
def calculator(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result."""
    try:
        # Safe constraint local evaluation
        allowed_names = {"__builtins__": None}
        result = eval(expression, allowed_names, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

@tool
def create_pdf(text: str, filename: str) -> str:
    """Creates a PDF file with the given text and filename. Returns the file path."""
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    filepath = os.path.join(GENERATED_DIR, filename)
    try:
        c = canvas.Canvas(filepath, pagesize=letter)
        y = 750
        # Exceptionally basic line break generation
        for line in text.split('\n'):
            c.drawString(50, y, line)
            y -= 15
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        return f"Successfully created PDF at {filepath}"
    except Exception as e:
        return f"Error creating PDF: {str(e)}"

@tool
def create_word(text: str, filename: str) -> str:
    """Creates a Microsoft Word (.docx) file with the given text and filename. Returns the file path."""
    if not filename.endswith(".docx"):
        filename += ".docx"
        
    filepath = os.path.join(GENERATED_DIR, filename)
    try:
        doc = docx.Document()
        doc.add_paragraph(text)
        doc.save(filepath)
        return f"Successfully created Word Document at {filepath}"
    except Exception as e:
        return f"Error creating Word Document: {str(e)}"

# Master list of all tools
agent_tools = [calculator, create_pdf, create_word, web_search, execute_terminal, read_local_file, write_local_file]
