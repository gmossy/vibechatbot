"""
RAG Dispatcher Tests
Tests that each file type is routed to the correct ingestion strategy.
Updated to match the optimal Docling configuration (DOC_CHUNKS + HybridChunker).
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# Ensure import paths
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), ".."))

from langchain_core.documents import Document
from app.services.rag_service import RAGService

class TestRAGDispatcher(unittest.TestCase):

    def setUp(self):
        # Mock heavy model loading and Docling converter during unit tests
        with patch('langchain_huggingface.HuggingFaceEmbeddings.__init__', return_value=None), \
             patch('app.services.rag_service._build_docling_converter', return_value=MagicMock()):
            self.rag_service = RAGService(user_id="test_user", project_id="test_project")
            self.rag_service.embeddings = MagicMock()

    @patch('app.services.rag_service.DoclingLoader')
    @patch('app.services.rag_service.FAISS')
    @patch('os.makedirs')
    def test_docx_dispatching(self, mock_makedirs, mock_faiss, mock_docling):
        """Verify .docx is dispatched to DoclingLoader with DOC_CHUNKS + HybridChunker."""
        mock_loader_instance = mock_docling.return_value
        mock_loader_instance.load.return_value = [
            Document(page_content="Word content", metadata={"source": "test.docx"})
        ]
        self.rag_service.vector_store = MagicMock()

        self.rag_service.ingest_file("/fake/path/test.docx", "test.docx")

        # Verify DoclingLoader was called with the optimal config
        mock_docling.assert_called_once()
        call_kwargs = mock_docling.call_args.kwargs
        self.assertEqual(call_kwargs["file_path"], "/fake/path/test.docx")
        from langchain_docling.loader import ExportType
        self.assertEqual(call_kwargs["export_type"], ExportType.DOC_CHUNKS)
        mock_loader_instance.load.assert_called_once()

    @patch('app.services.rag_service.DoclingLoader')
    @patch('app.services.rag_service.FAISS')
    @patch('os.makedirs')
    def test_xlsx_dispatching(self, mock_makedirs, mock_faiss, mock_docling):
        """Verify .xlsx is dispatched to DoclingLoader with DOC_CHUNKS + HybridChunker."""
        mock_loader_instance = mock_docling.return_value
        mock_loader_instance.load.return_value = [
            Document(page_content="Excel table content", metadata={"source": "table.xlsx"})
        ]
        self.rag_service.vector_store = MagicMock()

        self.rag_service.ingest_file("/fake/path/table.xlsx", "table.xlsx")

        mock_docling.assert_called_once()
        call_kwargs = mock_docling.call_args.kwargs
        self.assertEqual(call_kwargs["file_path"], "/fake/path/table.xlsx")
        from langchain_docling.loader import ExportType
        self.assertEqual(call_kwargs["export_type"], ExportType.DOC_CHUNKS)
        mock_loader_instance.load.assert_called_once()

    @patch('app.services.rag_service.DoclingLoader')
    @patch('app.services.rag_service.FAISS')
    @patch('os.makedirs')
    def test_csv_dispatching(self, mock_makedirs, mock_faiss, mock_docling):
        """Verify .csv is dispatched to DoclingLoader with MARKDOWN export."""
        mock_loader_instance = mock_docling.return_value
        mock_loader_instance.load.return_value = [
            Document(page_content="| col1 | col2 |", metadata={"source": "data.csv"})
        ]
        self.rag_service.vector_store = MagicMock()

        self.rag_service.ingest_file("/fake/path/data.csv", "data.csv")

        mock_docling.assert_called_once()
        call_kwargs = mock_docling.call_args.kwargs
        from langchain_docling.loader import ExportType
        self.assertEqual(call_kwargs["export_type"], ExportType.MARKDOWN)
        mock_loader_instance.load.assert_called_once()

    @patch('app.services.rag_service.TextLoader')
    @patch('app.services.rag_service.FAISS')
    @patch('os.makedirs')
    def test_text_dispatching(self, mock_makedirs, mock_faiss, mock_textloader):
        """Verify .txt is dispatched to TextLoader."""
        mock_loader_instance = mock_textloader.return_value
        mock_loader_instance.load.return_value = [
            Document(page_content="Plain text", metadata={"source": "notes.txt"})
        ]
        self.rag_service.vector_store = MagicMock()

        self.rag_service.ingest_file("/fake/path/notes.txt", "notes.txt")

        mock_textloader.assert_called_once_with("/fake/path/notes.txt", autodetect_encoding=True)
        mock_loader_instance.load.assert_called_once()

    @patch('app.services.rag_service.TextLoader')
    @patch('app.services.rag_service.FAISS')
    @patch('os.makedirs')
    def test_cue_dispatching(self, mock_makedirs, mock_faiss, mock_textloader):
        """Verify .cue (CUE lang) is dispatched to TextLoader."""
        mock_loader_instance = mock_textloader.return_value
        mock_loader_instance.load.return_value = [
            Document(page_content="#Service: {}", metadata={"source": "config.cue"})
        ]
        self.rag_service.vector_store = MagicMock()

        self.rag_service.ingest_file("/fake/path/config.cue", "config.cue")

        mock_textloader.assert_called_once_with("/fake/path/config.cue", autodetect_encoding=True)
        mock_loader_instance.load.assert_called_once()


if __name__ == '__main__':
    unittest.main()
