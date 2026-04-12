"""
Real PDF Quality Dispatch Test
Tests the Optimal Docling configuration against:
  1. A real structured PDF (with tables + headings)
  2. Source code files (C, Python, CUE)

No mocks. All real ingestion.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DOCLING_ALLOW_EXTERNAL_PLUGINS", "true")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REAL_PDF = os.path.join(_REPO_ROOT, "your_research_paper.pdf")

# ── Create real source code test fixtures ────────────────────────────────────
C_CODE = """\
#include <stdio.h>
// Example: compute factorial
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
int main() {
    printf("10! = %d\\n", factorial(10));
    return 0;
}
"""

PYTHON_CODE = """\
# Example RAG pipeline utility
def compute_embedding_similarity(vec_a, vec_b):
    \"\"\"Cosine similarity between two embedding vectors.\"\"\"
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a ** 2 for a in vec_a) ** 0.5
    norm_b = sum(b ** 2 for b in vec_b) ** 0.5
    return dot / (norm_a * norm_b)
"""

CUE_CODE = """\
// Example CUE configuration schema
#Service: {
    name:    string
    port:    int & >=1024 & <=65535
    replicas: int & >=1
}

middleware: #Service & {
    name:     "api-middleware"
    port:     8001
    replicas: 2
}
"""


def write_tmp(path, content):
    with open(path, "w") as f:
        f.write(content)


def run():
    from app.services.rag_service import RAGService

    print("\n" + "=" * 60)
    print("  🧪 REAL PDF + CODE DISPATCH TEST (Optimal Docling)")
    print("=" * 60)

    rag = RAGService(user_id="pdf_quality_tester", project_id="quality_test_001")

    # ── Test 1: Real structured PDF ──────────────────────────────────────────
    print(f"\n[TEST 1] 📄 Real PDF Ingestion: {os.path.basename(REAL_PDF)}")
    print("         Using: DOC_CHUNKS + HybridChunker + OCR + Table Extraction")
    if not os.path.exists(REAL_PDF):
        print("         ⚠️  PDF not found — skipping")
    else:
        t0 = time.time()
        chunks = rag.ingest_file(REAL_PDF, os.path.basename(REAL_PDF))
        elapsed = time.time() - t0
        print(f"         ✅ Ingested {chunks} structure-aware chunks in {elapsed:.2f}s")
        # Retrieve and show a snippet
        context = rag.retrieve_context("What is the main topic of this paper?")
        preview = context[:300].replace("\n", " ")
        print(f"         Retrieved: \"{preview}...\"")

    # ── Test 2: C Code ───────────────────────────────────────────────────────
    print("\n[TEST 2] 🔧 C Source Code (.c)")
    c_path = "/tmp/rag_dispatch_test.c"
    write_tmp(c_path, C_CODE)
    t0 = time.time()
    chunks = rag.ingest_file(c_path, "rag_dispatch_test.c")
    elapsed = time.time() - t0
    context = rag.retrieve_context("What does the factorial function do?")
    found = "factorial" in context
    print(f"         ✅ {chunks} chunks in {elapsed:.3f}s | Retrieval: {'✅ PASS' if found else '❌ FAIL'}")

    # ── Test 3: Python Code ──────────────────────────────────────────────────
    print("\n[TEST 3] 🐍 Python Source Code (.py)")
    py_path = "/tmp/rag_dispatch_test.py"
    write_tmp(py_path, PYTHON_CODE)
    t0 = time.time()
    chunks = rag.ingest_file(py_path, "rag_dispatch_test.py")
    elapsed = time.time() - t0
    context = rag.retrieve_context("How do you compute cosine similarity?")
    found = "cosine" in context.lower() or "embedding" in context.lower()
    print(f"         ✅ {chunks} chunks in {elapsed:.3f}s | Retrieval: {'✅ PASS' if found else '❌ FAIL'}")

    # ── Test 4: CUE Code ─────────────────────────────────────────────────────
    print("\n[TEST 4] 🏗️  CUE Configuration Language (.cue)")
    cue_path = "/tmp/rag_dispatch_test.cue"
    write_tmp(cue_path, CUE_CODE)
    t0 = time.time()
    chunks = rag.ingest_file(cue_path, "rag_dispatch_test.cue")
    elapsed = time.time() - t0
    context = rag.retrieve_context("What port does the api middleware run on?")
    found = "8001" in context
    print(f"         ✅ {chunks} chunks in {elapsed:.3f}s | Retrieval: {'✅ PASS' if found else '❌ FAIL'}")

    print("\n" + "=" * 60)
    print("  ✅ All dispatch tests complete")
    print("=" * 60)

    # Cleanup temp files
    for p in [c_path, py_path, cue_path]:
        if os.path.exists(p):
            os.remove(p)


if __name__ == "__main__":
    run()
