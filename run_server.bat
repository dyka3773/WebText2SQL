@ECHO off
@REM chainlit run app/src/app.py -w --host 0.0.0.0 --port 5500

cd app\src
uvicorn main:app --host 0.0.0.0 --port 80 --reload --reload-delay 1