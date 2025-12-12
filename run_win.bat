@echo off
if not exist .venv (
  echo Creating virtualenv...
  py -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
python bot.py
