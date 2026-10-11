@echo off
py -3.12 -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo Setup complete. Add GROQ_API_KEY to .env.
