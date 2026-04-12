from reportlab.pdfgen import canvas

def create_dummy_pdf():
    c = canvas.Canvas("your_research_paper.pdf")
    c.drawString(100, 750, "Agent Chatbot Architecture — sample paper")
    c.drawString(100, 730, "Abstract:")
    c.drawString(100, 710, "This document outlines the deployment of a Multi-Agent AI system")
    c.drawString(100, 690, "using LangGraph, Gemma 4, and OpenWebUI natively on an M5 Pro Max.")
    c.drawString(100, 670, "The system leverages RAG pipelines with FAISS and OCR for advanced data retrieval.")
    
    c.drawString(100, 630, "1. Vector Analysis")
    c.drawString(100, 610, "The FAISS local index achieves sub-millisecond retrieval latency for complex queries.")
    c.save()

if __name__ == "__main__":
    create_dummy_pdf()
