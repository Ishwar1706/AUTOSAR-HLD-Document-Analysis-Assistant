AutoHLD Insight - Quick Start After Extraction
1. Move the project to a short path

Keep the complete extracted folder at:

C:

2. Open the Code folder in VS Code

Open:

C:\Code

3. Open a PowerShell terminal

Verify that the terminal is inside the Code folder:

Get-Location

4. Create a Python 3.12 virtual environment
py -3.12 -m venv .venv

5. Activate the environment
.\.venv\Scripts\Activate.ps1


The prompt should begin with:

(.venv) PS

6. Install dependencies
python -m pip install -r requirements.txt


Wait until Successfully installed appears.

7. Create the environment file
Copy-Item .env.example .env


Open .env and replace only:

GROQ_API_KEY=replace_with_your_groq_api_key


with the actual Groq API key.

8. Verify Tesseract OCR
tesseract --version


A Tesseract version number should appear.

9. Start the backend

In the first terminal:

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload


Keep this terminal running.

10. Start the frontend

Open a second VS Code terminal and activate the environment:

.\.venv\Scripts\Activate.ps1


Then run:

python -m streamlit run .\frontend\app.py

11. Open the application

Open:

http://localhost:8501

12. Upload the knowledge documents

Open Upload & Ingest, then upload all PDFs from:

Input_Data\Synthetic_HLD_Documents


After ingestion, use Grounded Q&A, Architecture Inventory, Dependency Map, Revision Comparison, Engineer Review, Audit History, Export Center, and Evaluation.