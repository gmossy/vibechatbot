import sys
import os

# Add the project root to path so we can import app services
sys.path.append(os.getcwd())

from app.services.rag_service import RAGService

def sync_obsidian():
    """
    Triggers a bulk ingestion of the mounted Obsidian vault.
    Registers it under the 'Obsidian_Knowledge' project in the Master Index.
    """
    VAULT_DIR = "/app/obsidian_vault"
    
    if not os.path.exists(VAULT_DIR):
        print(f"❌ Error: Obsidian vault not found at {VAULT_DIR}")
        return

    # Initialize RAG service for the Obsidian bucket
    rag = RAGService(user_id="default_user", project_id="Obsidian_Knowledge")
    
    print(f"🚀 Syncing Obsidian Vault: {VAULT_DIR}...")
    
    # Bulk ingest using Docling (which handles Markdown perfectly)
    results = rag.bulk_ingest(VAULT_DIR, recursive=True)
    
    print("\n✅ Sync Complete!")
    print(f"   Documents Indexed: {len(results['ingested'])}")

if __name__ == "__main__":
    sync_obsidian()
