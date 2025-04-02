@echo off
cd /d %~dp0
py -3.11 -m venv venv
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python wsgi.py 