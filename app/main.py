import sys
import os
import streamlit as st
import pandas as pd
import graphviz  # For visualizing the database schema
from pdf_extractor import extract_sql_from_pdf
from google_api_validator import grade_student_sql_with_google_api, validate_and_score_sql_with_google_api
# You may need to adjust these imports based on your actual model/database module names
from model import generate_multiple_sql
from database import get_database_schema_string, get_foreign_key_relationships, validate_sql_query, execute_pg_query
import time  # Add this at the top of the file

# Add the project root directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Optional: Spell correction
try:
    from spellchecker import SpellChecker
    def correct_spelling(text):
        spell = SpellChecker()
        words = text.split()
        corrected_words = [spell.correction(word) or word for word in words]
        return " ".join(corrected_words)
    SPELLCHECK_ENABLED = True
except ImportError:
    SPELLCHECK_ENABLED = False

# --- Utility: Clean duplicate columns from SELECT clause ---
def clean_select_clause(sql_query: str) -> str:
    """
    Removes duplicate columns from a SQL SELECT statement while preserving order.
    Example: "SELECT a, b, a FROM t" becomes "SELECT a, b FROM t"
    """
    if not sql_query.upper().strip().startswith("SELECT"):
        return sql_query
    from_position = sql_query.upper().find(" FROM ")
    if from_position == -1:
        return sql_query
    select_part = sql_query[:from_position]
    from_part = sql_query[from_position:]
    columns_str = select_part[len("SELECT "):].strip()
    columns = [col.strip() for col in columns_str.split(',')]
    unique_columns = []
    seen_columns = set()
    for col in columns:
        if col not in seen_columns:
            unique_columns.append(col)
            seen_columns.add(col)
    cleaned_select_part = "SELECT " + ", ".join(unique_columns)
    final_query = cleaned_select_part + from_part
    return final_query

# --- The 20 Ground Truth Questions ---
GROUND_TRUTH_QUESTIONS = [
    "How many employees are there in the company?",
    "What is the total revenue from all completed orders?",
    "What is the average salary of an employee?",
    "Show me the price of the cheapest and the most expensive product.",
    "Count the number of products in each category.",
    "What is the average salary for each department?",
    "List each product's name and its category name.",
    "Show me the first name of customers and the date of the orders they placed.",
    "What are the names of products supplied by a supplier from 'USA'?",
    "Find all employees who earn more than the average salary.",
    "List all customers who have never placed an order.",
    "Show me all products that have never been reviewed.",
    "Who are the top 3 customers by total amount spent? Show their full name and the total they spent.",
    "Find the name of the product with the highest average review rating."
    # Add the rest of your 20 questions here
]

st.set_page_config(layout="wide", page_title="SQL Grader & Validator")

# --- Caching Data ---
# Cache the schema and FK relationships so they are only fetched once per session
@st.cache_data
def load_db_info():
    schema = get_database_schema_string()
    fk_rels = get_foreign_key_relationships()
    return schema, fk_rels

db_schema, fk_relationships = load_db_info()

# The get_foreign_key_relationships() function should return a list of strings.
# We will format this list into a single multi-line string for the prompt.
if isinstance(fk_relationships, list) and fk_relationships:
    fk_relationships_str = "\n".join([f"-- {rel}" for rel in fk_relationships])
else:
    # This is a fallback in case the function returns an error or an empty list
    fk_relationships_str = "-- No foreign key relationships were found or an error occurred."

# --- Main App ---
st.title("🚀 SQL Validator and Automatic Grader")
st.write("An AI-powered tool to generate, validate, and grade SQL queries.")

# --- Tabbed Interface ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗃️ Database Schema", "🤖 AI Query Generator", "🎓 Student Grader", "💬 Chatbot", "📊 Results"])

# ======================================================================
# TAB 1: DATABASE SCHEMA
# ======================================================================
with tab1:
    st.header("Database Schema Overview")
    st.info("This is the structure of the database that the AI uses to generate and evaluate queries.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Table Schemas")
        st.code(db_schema, language="text")

    with col2:
        st.subheader("Foreign Key Relationships (JOINs)")
        if fk_relationships:
            # Create a visual graph
            dot = graphviz.Digraph(comment='Database Schema')
            dot.attr('node', shape='box', style='rounded')
            dot.attr('graph', rankdir='LR', splines='ortho')

            tables = set()
            for rel in fk_relationships:
                # Example rel: "orders.customer_id can be joined with customers.customer_id"
                parts = rel.split(' ')
                t1, c1 = parts[0].split('.')
                t2, c2 = parts[5].split('.')
                tables.add(t1)
                tables.add(t2)
                dot.edge(t1, t2, label=f"{c1} → {c2}")
            
            for table in tables:
                dot.node(table, label=table)

            st.graphviz_chart(dot)
            
            # Also display as text
            st.code(fk_relationships_str, language="sql")
        else:
            st.warning("No foreign key relationships were found or could be fetched.")

# ======================================================================
# TAB 2: AI QUERY GENERATOR & VALIDATOR (CORRECTED VERSION)
# ======================================================================
with tab2:
    st.header("AI Query Generator & Validator")
    st.info("Ask a custom question or select a pre-defined one to see how the AI works.")

    # Use a form to group the input widgets and the button together.
    # This prevents the app from rerunning when you type in the text area.
    with st.form(key='query_form'):
        # --- Input Selection ---
        query_type = st.radio(
            "Choose question type:", 
            ["Select from list", "Enter a custom question"], 
            horizontal=True,
            key='query_type_radio' # A key to help manage state
        )

        if query_type == "Select from list":
            question_input = st.selectbox(
                "Select a question to test:", 
                options=GROUND_TRUTH_QUESTIONS,
                key='question_selectbox'
            )
        else:
            question_input = st.text_area(
                "Enter your custom question here:",
                key='question_text_area'
            )

        # --- The Submit Button ---
        # The form's submit button will trigger the rerun.
        submit_button = st.form_submit_button(label="Generate and Validate Query")

    # --- Processing Logic (This runs only after the form is submitted) ---
    if submit_button:
        if not question_input:
            st.warning("Please select or enter a question.")
        else:
            # --- 1. Build the full prompt ---
            full_prompt = f"""-- You are a PostgreSQL expert. Given a database schema and a question, generate a correct PostgreSQL query.
-- Use table aliases for clarity. Pay close attention to the Foreign Key Relationships to construct JOINs.

-- Database Schema:
{db_schema}

-- Foreign Key Relationships (How to JOIN tables):
{fk_relationships_str}

-- Example 1 (Teaches a simple, single-table query):
### Question: Show the name and country of all suppliers.
### SQL: SELECT supplier_name, country FROM suppliers

-- Example 2 (Teaches JOIN and GROUP BY):
### Question: How many products are in each category? Show the category name.
### SQL: SELECT T2.category_name, count(T1.product_id) FROM products AS T1 JOIN categories AS T2 ON T1.category_id = T2.category_id GROUP BY T2.category_name

-- Example 3 (Teaches NOT IN Subquery):
### Question: Find all customers who have not placed an order.
### SQL: SELECT T1.first_name, T1.last_name FROM customers AS T1 WHERE T1.customer_id NOT IN (SELECT T2.customer_id FROM orders AS T2)

-- Example 4 (Teaches Subquery on a SINGLE TABLE):
### Question: List all employees who earn more than the average salary.
### SQL: SELECT T1.first_name, T1.salary FROM employees AS T1 WHERE T1.salary > (SELECT avg(T2.salary) FROM employees AS T2)

-- Example 5 (Teaches MIN/MAX Aggregate Functions):
### Question: What is the lowest and highest price of a product?
### SQL: SELECT MIN(price), MAX(price) FROM products

-- New Task:
### Question: {question_input}
### SQL:"""
            
            # --- 2. Generate and Validate ---
            with st.spinner("Generating query with local model..."):
                potential_queries = generate_multiple_sql(full_prompt)
                local_query = "Error: Local model failed to generate a valid query."
                valid_found = False
                invalid_queries = []
                for q in potential_queries:
                    cleaned_q = q.split('--')[0].strip()
                    if cleaned_q:
                        is_valid, _ = validate_sql_query(cleaned_q)
                        if is_valid and not valid_found:
                            local_query = cleaned_q
                            valid_found = True
                        elif not is_valid:
                            invalid_queries.append(cleaned_q)
            # Show all invalid queries
            if invalid_queries:
                st.subheader("Invalid Model-Generated Queries (not executed)")
                for q in invalid_queries:
                    st.code(q, language="sql")
            st.subheader("Local AI Model's Best Attempt")
            if local_query.startswith("Error:"):
                st.error(local_query)
            else:
                st.code(local_query, language="sql")
                # --- Execute the generated query and show results ---
                start_time = time.time()
                results, error = execute_pg_query(local_query)
                exec_time = time.time() - start_time
                st.subheader("Query Results from Database")
                if error:
                    st.error(error)
                elif results is not None:
                    if isinstance(results, list) and results:
                        st.dataframe(pd.DataFrame(results))
                        row_count = len(results)
                    elif isinstance(results, str):
                        st.success(results)
                        row_count = 0
                    else:
                        st.info("Query executed successfully, but no results to display.")
                        row_count = 0
                    # --- Show evaluation metrics ---
                    st.metric("Execution Time (seconds)", f"{exec_time:.3f}")
                    st.metric("Rows Returned", row_count)
                    st.metric("Query Validity", "Valid" if error is None else "Invalid")
                    # --- Store metrics in session state for results tab ---
                    if 'all_metrics' not in st.session_state:
                        st.session_state['all_metrics'] = []
                    st.session_state['all_metrics'].append({
                        'question': question_input,
                        'query': local_query,
                        'execution_time': exec_time,
                        'rows_returned': row_count,
                        'valid': error is None,
                        'error_message': error if error else "",
                        'results': results if isinstance(results, list) else str(results)
                    })
            
            # --- 3. Get Gemini API Review ---
            st.subheader("Google Gemini API Review")
            with st.spinner("Asking Google Gemini for a second opinion..."):
                # Use the 'validate_and_score' function here
                api_result = validate_and_score_sql_with_google_api(
                    db_schema, 
                    fk_relationships_str, 
                    question_input, 
                    local_query
                )

            if "error" in api_result:
                st.error(f"API Error: {api_result['error']}")
            else:
                score = api_result.get("score", 0)
                explanation = api_result.get("explanation", "No explanation provided.")
                corrected_sql = api_result.get("corrected_sql", local_query)

                st.metric(label="Gemini Correctness Score", value=f"{score}/10")
                st.info(f"**Gemini's Explanation:** {explanation}")
                
                # Only show the correction if it's actually different and necessary
                if score < 10 and corrected_sql != local_query:
                    st.write("**Gemini's Suggested Correction:**")
                    st.code(corrected_sql, language="sql")

# ======================================================================
# TAB 3: STUDENT GRADER
# ======================================================================
with tab3:
    st.header("Automatic Student Lab Sheet Grader")
    st.info("Upload a student's PDF. The system will extract their answers and grade them one-by-one against AI-generated expert solutions, or you can use Gemini to automatically grade the entire sheet.")
    
    uploaded_file = st.file_uploader("1. Upload a student's PDF lab sheet", type="pdf", key="pdf_uploader")

    if uploaded_file is not None:
        if 'student_queries' not in st.session_state or st.session_state.get('processed_file') != uploaded_file.name:
            with st.spinner("Reading PDF and extracting student's SQL answers..."):
                queries, pdf_error = extract_sql_from_pdf(uploaded_file)
                st.session_state.processed_file = uploaded_file.name
                if pdf_error:
                    st.error(pdf_error)
                    st.session_state.student_queries = []
                ##elif not queries or len(queries) < len(GROUND_TRUTH_QUESTIONS):
                  ##  st.error(f"Could not find the expected {len(GROUND_TRUTH_QUESTIONS)} SQL queries. Found {len(queries)}. Please check PDF format.")
                   ## st.session_state.student_queries = []/*
                else:
                    st.success(f"Successfully extracted the pdf.")
                    st.session_state.student_queries = queries

        # --- New: Gemini Full PDF Grading ---
        st.markdown("---")
        st.info("Let Gemini process and grade the entire PDF in one go. This works even if the PDF is a single block of text, as long as questions and answers are distinguishable.")
        if st.button("Grade the PDF", key="gemini_full_pdf_grade"):
            import fitz  # PyMuPDF
            with st.spinner("Extracting full text from PDF and sending to Gemini..."):
                pdf_file = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                full_text = ""
                for page in pdf_file:
                    full_text += page.get_text()
                pdf_file.close()
            
            with st.spinner("Gemini is analyzing and grading the entire lab sheet..."):
                # Placeholder for the new Gemini grading function
                from google_api_validator import gemini_grade_full_lab_sheet
                gemini_results = gemini_grade_full_lab_sheet(full_text)
            
            if 'error' in gemini_results:
                st.error(f"Gemini API Error: {gemini_results['error']}")
            else:
                st.success("Gemini has graded the entire lab sheet. See results below:")
                for i, result in enumerate(gemini_results.get('questions', [])):
                    st.markdown(f"**Question {i+1}:** {result.get('question', 'N/A')}")
                    st.code(result.get('student_answer', ''), language="sql")
                    st.write(f"**Score:** {result.get('score', 'N/A')}")
                    st.write(f"**Correctness:** {result.get('correctness', 'N/A')}")
                    st.write(f"**Feedback:** {result.get('feedback', 'No feedback provided.')}")
                    st.markdown("---")

        # --- Existing: One-by-one grading ---
        if st.session_state.student_queries:
            st.header("2. Grade Questions One-by-One")
            question_options = [f"Question {i+1}: {q}" for i, q in enumerate(GROUND_TRUTH_QUESTIONS)]
            selected_question_with_index = st.selectbox("Select a question to grade:", options=question_options)
            selected_index = question_options.index(selected_question_with_index)
            
            if st.button(f"Grade Question #{selected_index + 1}", key="grade_single_button"):
                question_text = GROUND_TRUTH_QUESTIONS[selected_index]
                student_sql = st.session_state.student_queries[selected_index]

                with st.spinner("Generating 'expert' answer and grading with Gemini..."):
                    full_prompt = f"""-- You are a PostgreSQL expert. Given a database schema and a question, generate a correct PostgreSQL query.
-- Use table aliases for clarity. Pay close attention to the Foreign Key Relationships to construct JOINs.

-- Database Schema:
{db_schema}

-- Foreign Key Relationships (How to JOIN tables):
{fk_relationships_str}

-- Example 1 (Teaches a simple, single-table query):
### Question: Show the name and country of all suppliers.
### SQL: SELECT supplier_name, country FROM suppliers

-- Example 2 (Teaches JOIN and GROUP BY):
### Question: How many products are in each category? Show the category name.
### SQL: SELECT T2.category_name, count(T1.product_id) FROM products AS T1 JOIN categories AS T2 ON T1.category_id = T2.category_id GROUP BY T2.category_name

-- Example 3 (Teaches NOT IN Subquery):
### Question: Find all customers who have not placed an order.
### SQL: SELECT T1.first_name, T1.last_name FROM customers AS T1 WHERE T1.customer_id NOT IN (SELECT T2.customer_id FROM orders AS T2)

-- Example 4 (Teaches Subquery on a SINGLE TABLE):
### Question: List all employees who earn more than the average salary.
### SQL: SELECT T1.first_name, T1.salary FROM employees AS T1 WHERE T1.salary > (SELECT avg(T2.salary) FROM employees AS T2)

-- Example 5 (Teaches MIN/MAX Aggregate Functions):
### Question: What is the lowest and highest price of a product?
### SQL: SELECT MIN(price), MAX(price) FROM products

-- New Task:
### Question: {question_text}
### SQL:"""
                    potential_queries = generate_multiple_sql(full_prompt)
                    expert_sql = f"Error: Could not generate a valid query for: {question_text}"
                    for option in potential_queries:
                        cleaned_option = option.split('--')[0].strip()
                        if cleaned_option:
                            is_valid, _ = validate_sql_query(cleaned_option)
                            if is_valid:
                                expert_sql = cleaned_option
                                break
                    api_result = grade_student_sql_with_google_api(
                        db_schema, fk_relationships_str, question_text, expert_sql, student_sql
                    )
                st.subheader(f"Grading Result for Question #{selected_index + 1}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Expert (AI-Generated) Query:**")
                    st.code(expert_sql, language="sql")
                with col2:
                    st.write("**Student's Query:**")
                    st.code(student_sql, language="sql")
                if "error" in api_result:
                    st.error(f"API Grading Error: {api_result['error']}")
                else:
                    score = api_result.get("score", 0)
                    feedback = api_result.get("feedback", "No feedback.")
                    st.metric(label="Score", value=f"{score}/10")
                    st.info(f"**Feedback:** {feedback}")

# ======================================================================
# TAB 4: CHATBOT (CORRECTED VERSION)
# ======================================================================
with tab4:
    st.header("💬 Chatbot")
    st.info("Ask for help about how to use the application.")

    # This is the text input box that was missing
    user_input = st.text_input("Ask a question about the app:", key="chatbot_input")

    if user_input:
        # Simple rule-based logic for the chatbot's response
        cleaned_input = user_input.lower()
        if "hello" in cleaned_input or "hi" in cleaned_input:
            st.write("Hello! I am an automatic SQL grading assistant. Navigate the tabs to get started.")
        elif "help" in cleaned_input:
            st.write("Use the 'Database Schema' tab to view the data structure. Use the 'AI Query Generator' to test the AI. Use the 'Student Grader' to upload and grade a PDF.")
        elif "schema" in cleaned_input:
            st.write("Navigate to the 'Database Schema' tab to see all table structures and a visual diagram of how they are connected via foreign keys.")
        elif "grade" in cleaned_input or "student" in cleaned_input:
            st.write("Navigate to the 'Student Grader' tab, upload a student's lab sheet in PDF format, and then select questions one-by-one to grade them.")
        else:
            st.write("I'm sorry, I can only answer basic questions about how to use the app. Please try asking 'help'.")

with st.sidebar:
    st.header("Chatbot")
    user_input = st.text_area("Enter your question in natural language:", height=100)
    if user_input:
        bot_reply = chatbot_response(user_input)
        st.write(bot_reply)

# ======================================================================
# TAB 5: RESULTS (NEW)
# ======================================================================
with tab5:
    st.header("📊 Results: Evaluation Metrics")
    st.info("This page shows evaluation metrics for all AI-generated queries in this session.")
    if 'all_metrics' in st.session_state and st.session_state['all_metrics']:
        import pandas as pd
        df = pd.DataFrame(st.session_state['all_metrics'])
        st.dataframe(df.drop(columns=['results']))
        st.subheader("Query Results for Each Execution")
        for i, row in df.iterrows():
            with st.expander(f"Query {i+1}: {row['question']}"):
                st.code(row['query'], language="sql")
                if row['error_message']:
                    st.error(row['error_message'])
                else:
                    if isinstance(row['results'], list) and row['results']:
                        st.dataframe(pd.DataFrame(row['results']))
                    else:
                        st.write(row['results'])
        st.subheader("Metrics Visualization")
        st.bar_chart(df['execution_time'], use_container_width=True)
        st.bar_chart(df['rows_returned'], use_container_width=True)
        st.bar_chart(df['valid'].astype(int), use_container_width=True)
    else:
        st.warning("No metrics to display yet. Run some queries in the AI Query Generator tab.")
    st.markdown("---")
    st.info("**Gemini API JSON Tip:** When sending data to Gemini, always use `json.dumps()` and ensure all property names are in double quotes.") 