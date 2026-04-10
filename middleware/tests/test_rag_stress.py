import os
import sys
import time
import asyncio
from app.services.rag_service import RAGService

# Ensure import paths
sys.path.append(os.getcwd())

async def run_rag_stress_test(num_docs=50):
    print(f"\n--- 🔋 RAG STRESS TEST: {num_docs} DOCUMENTS ---")
    
    rag = RAGService(user_id="stress_tester", project_id="load_test_001")
    test_data_dir = "./temp_stress_test"
    os.makedirs(test_data_dir, exist_ok=True)
    
    # 1. Generate test files
    print(f"[STEP 1] Generating {num_docs} unique documents...")
    file_paths = []
    for i in range(num_docs):
        path = os.path.join(test_data_dir, f"doc_{i}.txt")
        with open(path, "w") as f:
            f.write(f"This is document number {i}. The secret key for this document is KEY-{i*123}.")
        file_paths.append(path)
        
    # 2. Sequential Ingestion
    print(f"[STEP 2] Ingesting documents...")
    start_time = time.time()
    total_chunks = 0
    
    for i, path in enumerate(file_paths):
        filename = os.path.basename(path)
        try:
            chunks = rag.ingest_file(path, filename)
            total_chunks += chunks
            if (i+1) % 10 == 0:
                print(f"   Progress: {i+1}/{num_docs} files ingested...")
        except Exception as e:
            print(f"   ❌ Error at file {i}: {e}")
            
    end_time = time.time()
    duration = end_time - start_time
    
    # 3. Validation
    print("\n[STEP 3] Validating retrieval speed and accuracy...")
    search_start = time.time()
    # Query for the middle document to ensure index integrity
    mid_index = num_docs // 2
    query = f"What is the secret key for document {mid_index}?"
    context = rag.retrieve_context(query)
    search_duration = time.time() - search_start
    
    # 4. Results
    print("\n--- 📊 STRESS TEST RESULTS ---")
    print(f"Total Files:      {num_docs}")
    print(f"Total Chunks:     {total_chunks}")
    print(f"Ingest Time:      {duration:.2f} seconds ({duration/num_docs:.3f}s per file)")
    print(f"Retrieval Time:   {search_duration:.3f} seconds")
    
    print(f"\nRetrieved Context Snippet:\n\"{context[:200]}...\"")
    
    expected_key = f"KEY-{mid_index*123}"
    if expected_key in context:
        print(f"\n✅ SUCCESS: Retrieval verified key '{expected_key}'.")
    else:
        print(f"\n❌ FAILURE: Could not find key '{expected_key}' in context.")

    # Cleanup
    import shutil
    shutil.rmtree(test_data_dir)
    print("\n[CLEANUP] Temporary test files removed.")

if __name__ == "__main__":
    asyncio.run(run_rag_stress_test(50))
