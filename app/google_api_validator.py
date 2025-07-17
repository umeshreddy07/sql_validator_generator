import streamlit as st
import google.generativeai as genai
import json
import time
import re

# --- Constants for the retry logic ---
MAX_RETRIES = 5
INITIAL_WAIT_SECONDS = 2
FORCED_WAIT_SECONDS = 20  # Always wait 20 seconds between queries as requested

def _call_gemini_with_retry(prompt_text: str):
    """
    A private helper function that calls the Gemini API with exponential backoff and a forced wait.
    """
    for i in range(MAX_RETRIES):
        try:
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content(prompt_text)
            # Success! Clean and return the JSON.
            json_text = response.text.strip().replace("```json", "").replace("```", "")
            try:
                return json.loads(json_text)
            except Exception as e:
                print("Gemini raw response:", json_text)
                return {"error": f"Gemini returned invalid JSON. Raw response: {json_text[:500]}... Error: {e}"}
            # Always wait 20 seconds after a successful call
            time.sleep(FORCED_WAIT_SECONDS)
            return json.loads(json_text)
        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error (429)
            if "429" in error_str:
                print(f"API rate limit hit. Attempt {i + 1} of {MAX_RETRIES}.")
                # Check if the API suggests a specific retry delay
                match = re.search(r"retry_delay {\s*seconds: (\d+)\s*}", error_str)
                if match:
                    wait_time = int(match.group(1)) + 1 # Add 1 second buffer
                    print(f"API suggested waiting {wait_time} seconds.")
                else:
                    # If no suggestion, use exponential backoff
                    wait_time = INITIAL_WAIT_SECONDS * (2 ** i)
                    print(f"No specific delay suggested. Waiting for {wait_time} seconds.")
                # If this is the last attempt, don't wait, just fail.
                if i < MAX_RETRIES - 1:
                    time.sleep(wait_time)
                continue # Go to the next iteration of the loop
            else:
                # If it's a different error (e.g., 404, 500), fail immediately.
                print(f"A non-retryable API error occurred: {e}")
                return {"error": f"A non-retryable API error occurred: {e}"}
    # If the loop finishes without a successful return, it means all retries failed.
    return {"error": f"Failed to get a response from the API after {MAX_RETRIES} attempts due to persistent rate limiting."}


def grade_student_sql_with_google_api(db_schema: str, fk_relationships: str, user_question: str, expert_sql: str, student_sql: str):
    """
    Uses Google's Gemini API to grade a student's SQL query.
    Now uses the robust retry mechanism.
    """
    try:
        genai.configure(api_key=st.secrets.google_ai.api_key)
    except (AttributeError, KeyError):
        return {"error": "Google API key not found in secrets.toml."}

    grading_prompt = f"""
    You are an expert PostgreSQL Teaching Assistant. Your task is to grade a student's SQL query.
    You will be given the database schema, the original question, a correct "expert" SQL query, and the student's submitted SQL query.

    **Evaluation Context:**
    1.  **Database Schema:**
        {db_schema}

    2.  **Foreign Key Relationships (for JOINs):**
        {fk_relationships}

    3.  **The Original Question:**
        "{user_question}"

    4.  **The Expert's Correct SQL Query (for reference):**
        ```sql
        {expert_sql}
        ```

    5.  **The Student's SQL Query (to be graded):**
        ```sql
        {student_sql}
        ```

    **Your Grading Task:**
    Compare the student's query to the expert's query. The student's query does not need to be identical, but it MUST be **semantically equivalent** (i.e., it must produce the exact same result set).
    Respond ONLY with a valid JSON object in the following format. Do not add any text before or after the JSON object.

    {{
      "is_semantically_correct": <true if the student's query produces the same result as the expert's, otherwise false>,
      "score": <An integer score from 1 to 10. 10 for a perfect, semantically correct answer. 5-9 for a query that is close but has minor errors. 1-4 for a query that is fundamentally wrong.>,
      "feedback": "<A brief, helpful, one-sentence feedback for the student. Explain what they did right or what their primary mistake was. For example: 'Great use of JOIN! However, your WHERE clause is missing a condition.' or 'Perfect! This is an excellent and correct query.'>"
    }}
    """
    return _call_gemini_with_retry(grading_prompt)


def validate_and_score_sql_with_google_api(db_schema: str, fk_relationships: str, user_question: str, generated_sql: str):
    """
    Uses Google's Gemini API to validate a single SQL query.
    Now uses the robust retry mechanism.
    """
    try:
        genai.configure(api_key=st.secrets.google_ai.api_key)
    except (AttributeError, KeyError):
        return {"error": "Google API key not found in secrets.toml."}

    validation_prompt = f"""
    You are an expert PostgreSQL data analyst. Your task is to validate a SQL query generated from a natural language question.
    You will be given the database schema, the original question, and the generated SQL query.

    **Evaluation Context:**
    1.  **Database Schema:**
        {db_schema}

    2.  **Foreign Key Relationships (for JOINs):**
        {fk_relationships}

    3.  **The Original Question:**
        "{user_question}"

    4.  **The Generated SQL Query:**
        ```sql
        {generated_sql}
        ```

    **Your Validation Task:**
    Determine if the generated SQL query is correct for the question and schema. Respond ONLY with a valid JSON object in the following format. Do not add any text before or after the JSON object.

    {{
      "is_correct": <true if the query is correct, otherwise false>,
      "confidence": "<High, Medium, or Low>",
      "score": <an integer score from 1 to 10>,
      "explanation": "<A brief, one-sentence explanation of your reasoning.>",
      "corrected_sql": "<The corrected version of the SQL query.>"
    }}
    """
    return _call_gemini_with_retry(validation_prompt)

def gemini_grade_full_lab_sheet(full_pdf_text: str):
    """
    Uses Gemini to process the entire PDF lab sheet, extract questions and answers, and grade each answer.
    Returns a dictionary with a 'questions' list, each containing question, student_answer, score, correctness, and feedback.
    """
    try:
        genai.configure(api_key=st.secrets.google_ai.api_key)
    except (AttributeError, KeyError):
        return {"error": "Google API key not found in secrets.toml."}

    grading_prompt = f"""
You are an expert SQL instructor. You will be given the full text of a student's lab sheet, which contains both the questions and the student's SQL answers. Your job is to:

1. Identify each individual question and its corresponding student answer.
2. For each question/answer pair:
    - Evaluate the student's answer for correctness.
    - If the answer is incorrect or incomplete, explain why.
    - Provide a score from 0 to 10 (10 = perfect, 5-9 = partially correct, 0-4 = mostly or completely wrong).
    - Provide a brief, clear feedback message for the student.
    - Mark the answer as 'correct', 'incorrect', or 'partial'.

Respond ONLY with a valid JSON object in the following format. Do not add any text before or after the JSON object.

{{
  "questions": [
    {{
      "question": "<The question text>",
      "student_answer": "<The student's SQL answer>",
      "score": <integer 0-10>,
      "correctness": "correct|incorrect|partial",
      "feedback": "<A brief, clear explanation for the student>"
    }},
    ...
  ]
}}

Here is the full lab sheet text:
"""
    grading_prompt += full_pdf_text

    for i in range(MAX_RETRIES):
        try:
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content(grading_prompt)
            json_text = response.text.strip().replace("```json", "").replace("```", "")
            try:
                return json.loads(json_text)
            except Exception as e:
                print("Gemini raw response:", json_text)
                return {"error": f"Gemini returned invalid JSON. Raw response: {json_text[:500]}... Error: {e}"}
            time.sleep(FORCED_WAIT_SECONDS)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                match = re.search(r"retry_delay {\s*seconds: (\d+)\s*}", error_str)
                if match:
                    wait_time = int(match.group(1)) + 1
                else:
                    wait_time = INITIAL_WAIT_SECONDS * (2 ** i)
                if i < MAX_RETRIES - 1:
                    time.sleep(wait_time)
                continue
            else:
                return {"error": f"A non-retryable API error occurred: {e}"}
    return {"error": f"Failed to get a response from the API after {MAX_RETRIES} attempts due to persistent rate limiting."} 