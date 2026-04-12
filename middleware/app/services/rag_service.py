"""
RAG Service — Retrieval-Augmented Generation Pipeline
======================================================
Handles document ingestion and context retrieval for the agent chatbot stack.

Architecture:
  - Multi-tenant: FAISS index scoped per user + project
  - Dispatcher: Routes file types to the optimal loader
  - Docling: Handles structured documents (PDF, DOCX, XLSX, PPTX, HTML)
  - TextLoader: Handles source code and plain text files
  - Tesseract: Handles image files via OCR

Docling Plugin Note:
  `DOCLING_ALLOW_EXTERNAL_PLUGINS` must be set before Docling is imported
  AND via pipeline_options.allow_external_plugins for full coverage.
"""

# ── CRITICAL: Must be set before any Docling import ──────────────────────────
import os
os.environ["DOCLING_ALLOW_EXTERNAL_PLUGINS"] = "true"

# ── Standard Library ─────────────────────────────────────────────────────────
from typing import Optional

# ── LangChain / Vector Store ─────────────────────────────────────────────────
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Docling — Optimal Pipeline ───────────────────────────────────────────────
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from docling.chunking import HybridChunker
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# ── Image OCR ────────────────────────────────────────────────────────────────
from PIL import Image
import pytesseract

# ── Observability (optional — gracefully degrades if logfire not installed) ───
# This makes rag_service.py fully portable to any Python project.
try:
    import logfire
except ImportError:
    import logging as _logging
    import contextlib

    _log = _logging.getLogger(__name__)

    class _NoOpLogfire:
        """Minimal logfire-compatible shim using stdlib logging."""
        @contextlib.contextmanager
        def span(self, name: str, **kwargs):
            yield
        def info(self, msg: str, **kwargs):  _log.info(msg, **kwargs)
        def warn(self, msg: str, **kwargs):  _log.warning(msg, **kwargs)
        def error(self, msg: str, **kwargs): _log.error(msg, **kwargs)

    logfire = _NoOpLogfire()  # type: ignore[assignment]


# ── File Type Dispatch Tables ────────────────────────────────────────────────
# All formats natively supported by Docling's document understanding pipeline.
# Source: docling.datamodel.base_models.MimeTypeToFormat (v2.86.0)
DOCLING_EXTENSIONS = {
    # ── Microsoft Office (Open XML) ──
    ".pdf",
    ".docx",                              # MS Word (Open XML)
    ".pptx", ".ppsx", ".potx",           # MS PowerPoint variants
    ".xlsx",                              # MS Excel (Open XML)
    # ── Web ──
    ".html", ".htm", ".xhtml",
    # ── Scientific / Structured XML ──
    ".xml",                               # JATS, XBRL, USPTO patent XML
    # ── Document Formats ──
    ".asciidoc", ".adoc",                # AsciiDoc
    ".tex",                              # LaTeX
    ".vtt",                              # WebVTT (subtitles/transcripts)
}

CSV_EXTENSIONS = {".csv"}               # Markdown export preserves table rows

# Handled by TextLoader (raw syntax preservation — best for code/config)
TEXT_EXTENSIONS = {
    # Source Code
    ".c", ".cpp", ".h", ".hpp",          # C / C++
    ".py",                               # Python
    ".cue",                              # CUE lang
    ".go",                               # Go
    ".rs",                               # Rust
    ".java",                             # Java
    ".js", ".ts",                        # JavaScript / TypeScript
    ".sh", ".bash", ".zsh",             # Shell scripts
    # Text / Config / Data
    ".txt", ".md",                       # Plain text / Markdown (use TextLoader for code-heavy MD)
    ".json", ".yaml", ".yml",
    ".toml", ".ini",
}

# Images: routed to Docling's IMAGE pipeline (built-in OCR)
# Tesseract kept as fallback if Docling image pipeline unavailable
DOCLING_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}

# ⚠️ LEGACY FORMATS — NOT supported by Docling (binary pre-OOXML specs)
# Docling requires the Open XML format. These are caught early to provide
# a clear, actionable user message instead of a cryptic deep-stack error.
LEGACY_EXTENSIONS = {
    ".doc",  # Word 97-2003 Binary Format  → convert to .docx
    ".xls",  # Excel 97-2003 Binary Format → convert to .xlsx
    ".ppt",  # PowerPoint 97-2003 Binary   → convert to .pptx
    ".wps",  # Kingsoft Writer legacy       → convert to .docx
    ".odt",  # OpenDocument Text            → convert to .docx first
    ".ods",  # OpenDocument Spreadsheet     → convert to .xlsx first
    ".odp",  # OpenDocument Presentation    → convert to .pptx first
}


# ── Docling Pipeline Configuration ───────────────────────────────────────────
def _build_pdf_pipeline() -> PdfPipelineOptions:
    """Build the optimal PDF pipeline with OCR and table extraction."""
    opts = PdfPipelineOptions()
    opts.do_ocr = True                  # Extract text from scanned/image-based PDFs
    opts.do_table_structure = True      # Cell-level table understanding
    opts.generate_page_images = False   # Skip page images (saves memory)
    opts.allow_external_plugins = True  # Required for langchain-docling 2.x integration
    return opts


def _build_docling_converter() -> DocumentConverter:
    """Build a reusable DocumentConverter with optimal settings."""
    return DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=_build_pdf_pipeline())}
    )


import json
from pathlib import Path

# ── Project Metadata Configuration ──────────────────────────────────────────
METADATA_PATH = "./data/projects_metadata.json"

class RAGService:
    """
    Multi-tenant RAG service that ingests documents into per-user FAISS indices
    and retrieves relevant context for the LangGraph agent.
    """

    def __init__(self, user_id: str = "default_user", project_id: str = "default_project"):
        # Scoped persistence path per user/project for full multi-tenant isolation
        self.persist_dir = f"./data/projects/{user_id}/{project_id}/faiss_index"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store: Optional[FAISS] = None

        # Build the Docling converter once and reuse across all ingestion calls
        # to avoid re-initialising models on each request (~500ms saved per call)
        self.docling_converter = _build_docling_converter()

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _get_docling_loader(self, file_path: str, export_type: ExportType) -> DoclingLoader:
        """Helper to create a DoclingLoader with consistent optimal settings."""
        return DoclingLoader(
            file_path=file_path,
            converter=self.docling_converter,
            export_type=export_type,
            chunker=HybridChunker(tokenizer="BAAI/bge-small-en-v1.5"),
        )

    def _update_project_metadata(self, filename: str):
        """Updates the master index with project and file metadata."""
        os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
        
        metadata = {}
        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "r") as f:
                    metadata = json.load(f)
            except Exception:
                pass

        user_data = metadata.get(self.user_id, {})
        project_data = user_data.get(self.project_id, {"files": [], "description": f"Documentation and data for project {self.project_id}"})
        
        if filename not in project_data["files"]:
            project_data["files"].append(filename)
            
        user_data[self.project_id] = project_data
        metadata[self.user_id] = user_data

        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)

    @staticmethod
    def list_available_projects(user_id: str) -> dict:
        """Returns the master list of projects and their descriptions for a user."""
        if not os.path.exists(METADATA_PATH):
            return {}
        try:
            with open(METADATA_PATH, "r") as f:
                all_metadata = json.load(f)
                return all_metadata.get(user_id, {})
        except Exception:
            return {}

    def _load_or_create_store(self) -> Optional[FAISS]:
        """Lazy-loads the FAISS index from disk. No-ops if already loaded."""
        if self.vector_store is not None:
            return self.vector_store

        index_file = os.path.join(self.persist_dir, "index.faiss")
        if os.path.exists(self.persist_dir) and os.path.exists(index_file):
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=self.persist_dir,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                logfire.warn("FAISS index could not be loaded: {e}", e=e)

        return self.vector_store

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest_file(self, file_path: str, filename: str, strict: bool = True) -> int:
        """
        Ingests a document file into the FAISS vector store.

        Args:
            file_path: Absolute path to the file on disk.
            filename:  Original filename (used for extension detection and metadata).
            strict:    If True (default), raises ValueError on legacy/unsupported formats.
                       If False (bulk/automated mode), logs a warning and returns -1 to skip.

        Dispatches to the optimal loader based on file extension:
          - PDF / DOCX / XLSX / PPTX / HTML / XHTML / XML    → Docling (DOC_CHUNKS + HybridChunker)
          - AsciiDoc / LaTeX / VTT                            → Docling (DOC_CHUNKS)
          - CSV                                               → Docling (Markdown export)
          - Images (PNG, JPG, TIFF, BMP, GIF, WebP)          → Docling IMAGE pipeline (built-in OCR)
          - Source code / plain text / config                 → TextLoader
          - Legacy binary formats (.doc, .xls, .ppt, etc.)   → ❌ strict=True raises | strict=False skips

        Returns:
            Number of chunks ingested, or -1 if the file was skipped (legacy format, strict=False).
        """
        with logfire.span("rag_ingest_file", filename=filename):
            ext = os.path.splitext(filename)[1].lower()

            # ── Step 1: Load ─────────────────────────────────────────────────
            with logfire.span("load_documents", extension=ext):
                if ext in DOCLING_EXTENSIONS:
                    # DOC_CHUNKS preserves heading/table/caption structure.
                    loader = self._get_docling_loader(file_path, ExportType.DOC_CHUNKS)
                    documents = loader.load()

                elif ext in CSV_EXTENSIONS:
                    # Markdown export for tables
                    loader = self._get_docling_loader(file_path, ExportType.MARKDOWN)
                    documents = loader.load()

                elif ext in TEXT_EXTENSIONS:
                    # Source code / text preservations
                    loader = TextLoader(file_path, autodetect_encoding=True)
                    documents = loader.load()

                elif ext in DOCLING_IMAGE_EXTENSIONS:
                    # Native Docling IMAGE pipeline with Tesseract fallback
                    try:
                        loader = self._get_docling_loader(file_path, ExportType.MARKDOWN)
                        documents = loader.load()
                        if not documents or not documents[0].page_content.strip():
                            raise ValueError("Empty OCR result")
                    except Exception:
                        logfire.warn("Docling OCR failed, using Tesseract", filename=filename)
                        extracted_text = pytesseract.image_to_string(Image.open(file_path))
                        documents = [Document(page_content=extracted_text, metadata={"source": filename})]

                elif ext in LEGACY_EXTENSIONS:
                    # Legacy binary Office formats predate the Open XML (OOXML) spec.
                    # In strict mode (user-facing API): raise with an actionable message.
                    # In non-strict mode (bulk pipeline): log and signal caller to skip.
                    _CONVERT_HINT = {
                        ".doc":  "Open in Microsoft Word → Save As → .docx",
                        ".xls":  "Open in Microsoft Excel → Save As → .xlsx",
                        ".ppt":  "Open in Microsoft PowerPoint → Save As → .pptx",
                        ".wps":  "Open in Word or LibreOffice → Save As → .docx",
                        ".odt":  "Open in LibreOffice → Save As → Microsoft Word (.docx)",
                        ".ods":  "Open in LibreOffice → Save As → Microsoft Excel (.xlsx)",
                        ".odp":  "Open in LibreOffice → Save As → Microsoft PowerPoint (.pptx)",
                    }
                    hint = _CONVERT_HINT.get(ext, f"Convert '{ext}' to an Open XML format")
                    user_message = (
                        f"⚠️  '{filename}' uses a legacy binary format ('{ext}') that cannot be parsed.\n"
                        f"   Docling requires the modern Open XML format.\n"
                        f"   📋 How to fix: {hint}."
                    )
                    logfire.warn(
                        "Legacy format skipped: {filename} ({ext}). Hint: {hint}",
                        filename=filename, ext=ext, hint=hint
                    )
                    if strict:
                        raise ValueError(user_message)
                    else:
                        print(f"[RAG SKIP] {user_message}")
                        return -1

                else:
                    raise ValueError(f"Unsupported file type: '{ext}'. Check DOCLING_EXTENSIONS or TEXT_EXTENSIONS.")


            # ── Step 2: Chunk ─────────────────────────────────────────────────
            # DOC_CHUNKS from Docling are already semantically chunked.
            # TextLoader / OCR output still needs splitting.
            with logfire.span("split_documents"):
                if ext in DOCLING_EXTENSIONS | DOCLING_IMAGE_EXTENSIONS:
                    chunks = documents  # Already split by HybridChunker / Docling pipeline
                else:
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200,
                        separators=["\n\n", "\n", " ", ""],
                    )
                    chunks = splitter.split_documents(documents)

            if not chunks:
                logfire.warn("No chunks generated for {filename}", filename=filename)
                return 0

            # ── Step 3: Embed + Store ─────────────────────────────────────────
            with logfire.span("add_to_vector_store", chunk_count=len(chunks)):
                self._load_or_create_store()
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(chunks, self.embeddings)
                else:
                    self.vector_store.add_documents(chunks)

            # ── Step 4: Persist ───────────────────────────────────────────────
            with logfire.span("save_vector_store"):
                os.makedirs(self.persist_dir, exist_ok=True)
                self.vector_store.save_local(self.persist_dir)

            logfire.info("Ingested {n} chunks from {f}", n=len(chunks), f=filename)
            
            # ── Step 5: Master Index Update ──────────────────────────────────
            self._update_project_metadata(filename)
            
            return len(chunks)

    def retrieve_context(self, query: str, k: int = 4) -> str:
        """
        Retrieves the top-k most relevant document chunks for a given query.

        Returns:
            Formatted string of retrieved context, or empty string if no index exists.
        """
        with logfire.span("rag_retrieve_context", query=query):
            self._load_or_create_store()

            if self.vector_store is None:
                return ""

            with logfire.span("similarity_search", k=k):
                docs = self.vector_store.similarity_search(query, k=k)

            if not docs:
                return ""

            return "\n\n".join(
                f"--- Document Content from {os.path.basename(doc.metadata.get('source', 'Unknown'))} ---\n{doc.page_content}"
                for doc in docs
            )

    def bulk_ingest(self, directory: str, recursive: bool = False) -> dict:
        """
        Automated bulk ingestion of all files in a directory.

        Designed for pipeline use: legacy and unsupported files are skipped
        with a warning message rather than halting the batch.

        Args:
            directory:  Path to the folder containing documents to ingest.
            recursive:  If True, walks all subdirectories. Default: False.

        Returns:
            A summary dict with keys:
              - ingested:      list of (filename, chunk_count)
              - skipped:       list of (filename, reason)
              - failed:        list of (filename, error_message)
              - total_chunks:  int
        """
        from pathlib import Path
        results: dict = {"ingested": [], "skipped": [], "failed": [], "total_chunks": 0}

        root = Path(directory)
        files = list(root.rglob("*") if recursive else root.glob("*"))
        files = [f for f in files if f.is_file()]

        print(f"\n[RAG BULK INGEST] Starting — {len(files)} file(s) found in '{directory}'")
        logfire.info("Bulk ingest started: {n} files in {dir}", n=len(files), dir=directory)

        for file_path in sorted(files):
            filename = file_path.name
            ext = file_path.suffix.lower()

            # Pre-flight: announce legacy files before attempting ingest
            if ext in LEGACY_EXTENSIONS:
                hint_map = {
                    ".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx",
                    ".wps": ".docx", ".odt": ".docx", ".ods": ".xlsx", ".odp": ".pptx",
                }
                target = hint_map.get(ext, "an Open XML format")
                reason = f"Legacy binary format '{ext}' — convert to {target} first."
                print(f"[RAG SKIP] ⚠️  '{filename}' — {reason}")
                logfire.warn("Bulk ingest skip: {f} ({ext})", f=filename, ext=ext)
                results["skipped"].append((filename, reason))
                continue

            try:
                chunks = self.ingest_file(str(file_path), filename, strict=False)
                if chunks == -1:
                    results["skipped"].append((filename, f"Unsupported extension '{ext}'"))
                else:
                    results["ingested"].append((filename, chunks))
                    results["total_chunks"] += chunks
            except Exception as e:
                error_msg = str(e)
                print(f"[RAG ERROR] ❌  '{filename}' — {error_msg}")
                logfire.error("Bulk ingest error: {f} — {err}", f=filename, err=error_msg)
                results["failed"].append((filename, error_msg))

        # ── Summary Report ────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  RAG BULK INGEST — COMPLETE")
        print(f"{'='*60}")
        print(f"  ✅ Ingested : {len(results['ingested'])} files  ({results['total_chunks']} chunks)")
        print(f"  ⚠️  Skipped  : {len(results['skipped'])} files")
        print(f"  ❌ Failed   : {len(results['failed'])} files")
        if results["skipped"]:
            print(f"\n  Skipped files (convert and re-run):")
            for fname, reason in results["skipped"]:
                print(f"    • {fname}: {reason}")
        if results["failed"]:
            print(f"\n  Failed files (check logs):")
            for fname, err in results["failed"]:
                print(f"    • {fname}: {err}")
        print(f"{'='*60}\n")

        logfire.info(
            "Bulk ingest complete: {ok} ingested, {skip} skipped, {fail} failed, {chunks} chunks",
            ok=len(results["ingested"]), skip=len(results["skipped"]),
            fail=len(results["failed"]), chunks=results["total_chunks"]
        )
        return results
