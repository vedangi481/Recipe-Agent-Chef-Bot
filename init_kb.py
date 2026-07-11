# Application startup helper — initializes RAG before first request
# Import and call startup() in app.py already handles this.
# This file can be used to pre-warm the ChromaDB index.

from app import startup
startup()
print("Knowledge base initialized. Start with: python app.py")
