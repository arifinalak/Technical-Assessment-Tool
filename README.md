# Technical Assessment Tool

A powerful, AI-driven Sales Intelligence Dashboard and Chatbot built with Python. 

This platform allows users to view high-level sales data, access role-based information, and interact with a highly capable AI assistant that uses Retrieval-Augmented Generation (RAG) and Google Gemini to answer complex business questions.

## Features
- **Interactive AI Chatbot:** Uses Local Vector Search (ChromaDB) on permitted data summaries.
- **Smart Fallback:** Integrates the modern Google GenAI SDK (`gemini-3.8-flash`) for fallback when local context doesn't have the answer.
- **Role-Based Access Control (RBAC):** Users only see the rows and columns they are authorized to view.
- **SQLite Database:** Lightweight and embedded database (`sales.db`), meaning no complex database servers to set up.
- **Dynamic Frontend:** Built with clean, vanilla JS/CSS for maximum performance and a beautiful user experience.

## Tech Stack
- **Backend:** Python, FastAPI, Uvicorn
- **AI/LLM:** Google Gemini API, ChromaDB, Local Text-to-SQL logic
- **Database:** SQLite, Pandas (Data Manipulation)
- **Frontend:** HTML, CSS, JavaScript

## How to Run Locally
1. Clone this repository.
2. Ensure you have Python installed.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your Google Gemini API Key:
   - **Windows CMD:** `set GEMINI_API_KEY=your_key_here`
   - **Windows PowerShell:** `$env:GEMINI_API_KEY="your_key_here"`
   - **Mac/Linux:** `export GEMINI_API_KEY="your_key_here"`
5. Run the server:
   ```bash
   uvicorn app:app --host 127.0.0.1 --port 8000
   ```
6. Open `http://127.0.0.1:8000` in your browser.

## Deployment
This application is fully compatible with **Render.com**. 
Simply connect this repository to a Render Web Service, use `pip install -r requirements.txt` as the build command, `uvicorn app:app --host 0.0.0.0 --port $PORT` as the start command, and inject your `GEMINI_API_KEY` into the Render Environment Variables. No manual database deployment is required!
