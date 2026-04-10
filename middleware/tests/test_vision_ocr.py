import os
import sys
import asyncio
from PIL import Image, ImageDraw, ImageFont

# Ensure import paths
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

async def test_vision_ocr_integration():
    print("\n--- 👁️ VISION OCR INTEGRATION TEST (NO MOCKS) ---")
    
    # 1. Create a real image with text
    image_path = "ocr_test_image.png"
    text_to_find = "VERIFIED"
    
    print(f"\n[STEP 1] Generating test image with text: '{text_to_find}'...")
    # Huge image size for perfect OCR clarity
    img = Image.new('RGB', (800, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Use default font if custom font not found
    d.text((20, 40), text_to_find, fill=(0, 0, 0))
    img.save(image_path)
    
    # 2. Ingest the image into RAG
    rag = RAGService(user_id="vision_tester", project_id="ocr_verification")
    
    print("\n[STEP 2] Ingesting image into RAG pipeline...")
    try:
        num_chunks = rag.ingest_file(image_path, image_path)
        print(f"   Success! Ingested {num_chunks} chunks from image.")
    except Exception as e:
        print(f"   ❌ OCR Ingestion Failed: {e}")
        if "tesseract" in str(e).lower():
            print("      HINT: Tesseract OCR binary is missing from the system path.")
        return

    # 3. Retrieve and verify context
    print("\n[STEP 3] Verifying retrieval of extracted text...")
    context = rag.retrieve_context("What is the vision token?")
    
    print(f"\n[RESULTS] Retrieved Context:\n\"{context}\"")
    
    if text_to_find in context:
        print("\n✅ SUCCESS: OCR correctly extracted the text from the image and indexed it!")
    else:
        print("\n❌ FAILURE: The text was not found in the retrieved context.")
        
    # Clean up
    if os.path.exists(image_path):
        os.remove(image_path)
    # Optionally clean up the faiss index for this test user
    # shutil.rmtree("./data/projects/vision_tester", ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_vision_ocr_integration())
