import os
import subprocess
import json
import mimetypes
from datetime import datetime
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import docx
from pptx import Presentation
import logfire
from tenacity import retry, stop_after_attempt, wait_exponential
from app.services.rag_service import RAGService
from app.core.config import settings

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
            base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
            if base:
                url = f"{base}{settings.API_V1_STR}/generated_files/{filename}"
                return f"Successfully created PDF: [{filename}]({url})"
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
            base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
            if base:
                url = f"{base}{settings.API_V1_STR}/generated_files/{filename}"
                return f"Successfully created Word Document: [{filename}]({url})"
            return f"Successfully created Word Document at {filepath}"
        except Exception as e:
            logfire.error("Word creation failed: {e}", e=e)
            return f"Error creating Word Document: {str(e)}"

@tool
def create_pptx(text: str, filename: str) -> str:
    """
    Generates a Microsoft PowerPoint (.pptx) presentation.

    Format:
    - Slides are separated by a blank line.
    - For each slide, the first line is the title.
    - Remaining lines become bullet points.
    """
    with logfire.span("tool_create_pptx", filename=filename):
        if not filename.endswith(".pptx"):
            filename += ".pptx"

        filepath = os.path.join(GENERATED_DIR, filename)
        try:
            prs = Presentation()
            slide_layout = prs.slide_layouts[1]

            stripped = (text or "").strip()
            slides_data = None
            if stripped.startswith("[") or stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict) and isinstance(parsed.get("slides"), list):
                        slides_data = parsed.get("slides")
                    elif isinstance(parsed, list):
                        slides_data = parsed
                except Exception:
                    slides_data = None

            if slides_data is not None:
                for item in slides_data:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title", "")).strip() or "Slide"
                    bullets = item.get("bullets", [])
                    if bullets is None:
                        bullets = []
                    if isinstance(bullets, str):
                        bullets = [bullets]
                    if not isinstance(bullets, list):
                        bullets = []

                    slide = prs.slides.add_slide(slide_layout)
                    slide.shapes.title.text = title
                    body = slide.shapes.placeholders[1].text_frame
                    body.clear()

                    bullet_items = [str(b).strip() for b in bullets if str(b).strip()]
                    if bullet_items:
                        for i, bullet in enumerate(bullet_items):
                            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
                            p.text = bullet
                    else:
                        body.text = ""
            else:
                blocks = [b.strip() for b in (text or "").split("\n\n") if b.strip()]
                if not blocks:
                    blocks = ["Presentation"]

                for block in blocks:
                    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
                    if not lines:
                        continue

                    title = lines[0]
                    bullets = lines[1:]

                    slide = prs.slides.add_slide(slide_layout)
                    slide.shapes.title.text = title

                    body = slide.shapes.placeholders[1].text_frame
                    body.clear()
                    if bullets:
                        for i, bullet in enumerate(bullets):
                            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
                            p.text = bullet
                    else:
                        body.text = ""

            prs.save(filepath)
            base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
            if base:
                url = f"{base}{settings.API_V1_STR}/generated_files/{filename}"
                return f"Successfully created PowerPoint: [{filename}]({url})"
            return f"Successfully created PowerPoint at {filepath}"
        except Exception as e:
            logfire.error("PPTX creation failed: {e}", e=e)
            return f"Error creating PowerPoint: {str(e)}"

@tool
def list_generated_files() -> str:
    """Lists files in the generated_files directory with metadata and download links."""
    with logfire.span("tool_list_generated_files"):
        try:
            if not os.path.isdir(GENERATED_DIR):
                return "No generated files directory found."

            names = []
            for name in sorted(os.listdir(GENERATED_DIR)):
                if name.startswith("."):
                    continue
                full_path = os.path.join(GENERATED_DIR, name)
                if os.path.isfile(full_path):
                    names.append(name)

            if not names:
                return "No generated files found."

            base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
            lines = ["Generated files:"]
            for name in names:
                full_path = os.path.join(GENERATED_DIR, name)
                st = os.stat(full_path)
                mime, _ = mimetypes.guess_type(full_path)
                modified = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
                size = st.st_size

                if base:
                    url = f"{base}{settings.API_V1_STR}/generated_files/{name}"
                    lines.append(
                        f"- [{name}]({url}) ({mime or 'application/octet-stream'}, {size} bytes, {modified})"
                    )
                else:
                    lines.append(
                        f"- {name} ({mime or 'application/octet-stream'}, {size} bytes, {modified})"
                    )

            return "\n".join(lines)
        except Exception as e:
            logfire.error("List generated files failed: {e}", e=e)
            return f"Error listing generated files: {str(e)}"

@tool
def discover_knowledge_bases(user_id: str = "default_user") -> str:
    """
    Lists all available knowledge bases (projects) and their descriptions.
    Use this to find out which local database might contain the answer to a query.
    """
    projects = RAGService.list_available_projects(user_id)
    if not projects:
        return "No local knowledge bases found. You may need to upload documents first."
    
    output = "Available Knowledge Bases:\n"
    for p_id, data in projects.items():
        files = ", ".join(data.get("files", []))
        desc = data.get("description", "No description")
        output += f"- {p_id}: {desc} (Files: {files})\n"
    return output

@tool
def rag_search(query: str, project_id: str = "default_project", user_id: str = "default_user") -> str:
    """
    Searches a specific local knowledge base for relevant context.
    REQUIRED: You must get the 'project_id' from discover_knowledge_bases first.
    """
    rag = RAGService(user_id=user_id, project_id=project_id)
    context = rag.retrieve_context(query)
    if not context:
        return f"No relevant information found in project '{project_id}'."
    return context

# Master list of all tools
agent_tools = [
    calculator, 
    create_pdf, 
    create_word, 
    create_pptx,
    list_generated_files,
    web_search, 
    execute_terminal, 
    read_local_file, 
    write_local_file,
    discover_knowledge_bases,
    rag_search
]
