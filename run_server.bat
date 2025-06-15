@ECHO off
cd app\src

uvicorn main:app --host 0.0.0.0 --port 80 --reload --reload-delay 1