@echo off
REM Create folders if they don't exist
mkdir app
mkdir backend
mkdir chatbot
mkdir nlp_preprocessing
mkdir models
mkdir utils
mkdir .streamlit

REM Move Python files to their respective folders
move main.py app\ 2>nul
move database.py app\ 2>nul
move google_api_validator.py app\ 2>nul
move model.py app\ 2>nul
move pdf_extractor.py app\ 2>nul

move intent_classifier.py backend\ 2>nul
move query_executor.py backend\ 2>nul
move sql_generator.py backend\ 2>nul

move bot.py chatbot\ 2>nul

move dynamic_synonym_generator.py nlp_preprocessing\ 2>nul
move text_preprocessor.py nlp_preprocessing\ 2>nul

move logger.py utils\ 2>nul

REM Move __init__.py files if found in root
move __init__.py app\ 2>nul

REM Move README.md to root if not already there
move README.md .\ 2>nul

REM Move requirements.txt to root if not already there
move requirements.txt .\ 2>nul

REM Move test_api.py to root if not already there
move test_api.py .\ 2>nul

REM Move .streamlit config if found in root
move secrets.toml .streamlit\ 2>nul

echo Project files have been organized!
pause
