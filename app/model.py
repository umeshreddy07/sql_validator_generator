# Import necessary libraries for model loading and file/path handling
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
from pathlib import Path    
import sys # Import sys to exit gracefully

# --- USE THIS MORE POWERFUL MODEL ---
MODEL_ID = "google/flan-t5-large"  # Even more capable, but uses more RAM/disk

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(PROJECT_ROOT, "local_flan_t5_large_model")  # New folder name

tokenizer = None
model = None

if not os.path.isdir(MODEL_PATH):
    print(f"Local model not found. Downloading '{MODEL_ID}' to '{MODEL_PATH}'...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
    print("Saving model locally...")
    tokenizer.save_pretrained(MODEL_PATH)
    model.save_pretrained(MODEL_PATH)
    print("✅ Model downloaded and saved successfully.")
else:
    print(f"Attempting to load model from local path: {MODEL_PATH}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
    print("✅ Model and tokenizer loaded successfully from local folder.")

# --- RELATIONSHIP-AWARE TRIFECTA MASTERCLASS PROMPT ---
def _relationship_aware_prompt(nl_query: str, db_schema: str, fk_relationships: list) -> str:
    fk_string = "\n".join([f"-- {rel}" for rel in fk_relationships if not rel.startswith("Error")])
    return f"""
-- You are a PostgreSQL expert. Given a database schema and a question, generate a correct PostgreSQL query.
-- Use table aliases for clarity. Pay close attention to the Foreign Key Relationships to construct JOINs.

-- Database Schema:
{db_schema}

-- Foreign Key Relationships (How to JOIN tables):
{fk_string}

-- Example 1 (Teaches JOIN and GROUP BY):
### Question: How many products are in each category? Show the category name.
### SQL: SELECT T2.category_name, count(T1.product_id) FROM products AS T1 JOIN categories AS T2 ON T1.category_id = T2.category_id GROUP BY T2.category_name

-- Example 2 (Teaches NOT IN Subquery with a JOIN):
### Question: Find all customers who have not placed an order.
### SQL: SELECT T1.first_name, T1.last_name FROM customers AS T1 WHERE T1.customer_id NOT IN (SELECT T2.customer_id FROM orders AS T2)

-- Example 3 (Teaches Subquery on a SINGLE TABLE):
### Question: List all employees who earn more than the average salary.
### SQL: SELECT T1.first_name, T1.salary FROM employees AS T1 WHERE T1.salary > (SELECT avg(T2.salary) FROM employees AS T2)

-- New Task:
### Question: {nl_query}
### SQL:"""

def generate_sql(nl_query: str, db_schema: str, fk_relationships: list):
    """
    Generates a SQL query from a natural language question using a few-shot prompt.
    """
    prompt = _relationship_aware_prompt(nl_query, db_schema, fk_relationships)
    print("--- Generating SQL with TRIFECTA MASTERCLASS prompt ---")
    print(prompt)
    inputs = tokenizer(prompt, return_tensors="pt", padding="longest", truncation=True, max_length=1024)
    outputs = model.generate(inputs.input_ids, attention_mask=inputs.attention_mask, max_new_tokens=256)
    generated_sql = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if generated_sql.upper().startswith("SQL:"):
        generated_sql = generated_sql[4:].strip()
    cleaned_sql = generated_sql.strip()
    print(f"--- Generated SQL ---")
    print(cleaned_sql)
    return cleaned_sql

def generate_multiple_sql(full_prompt: str, num_beams: int = 5, num_return_sequences: int = 3):
    """
    Generates multiple SQL queries from a single, fully-formed prompt string.
    This function is now a simple wrapper around the model.
    """
    print("--- Generating MULTIPLE SQLs with the following prompt ---")
    print(full_prompt) # This is great for debugging

    inputs = tokenizer(
        full_prompt,
        return_tensors="pt",
        padding="longest",
        truncation=True,
        max_length=2048  # Increased max_length for the large prompt
    )
    
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=256,
        num_beams=num_beams,
        num_return_sequences=num_return_sequences,
        early_stopping=True
    )
    
    generated_queries = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    
    # Clean up the generated queries
    cleaned_queries = [sql.strip() for sql in generated_queries]
    
    print(f"DEBUG: Generated multiple potential queries: {cleaned_queries}")
    return cleaned_queries 