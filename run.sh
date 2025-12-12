#!/usr/bin/env bash
set -e
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
