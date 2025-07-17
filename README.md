# Natural Language to SQL Query Generator and Validator

**Authors:**
- Veena G (veenag@am.amrita.edu)
- Pilli Sarvan Sri Sai (am.en.u4aie22039@am.students.amrita.edu)
- Koraganji Mukesh (am.en.u4aie22029@am.students.amrita.edu)
- Damma Umesh (am.en.u4aie22501@am.students.amrita.edu)

---

## 1. 🚀 Project Overview

Welcome to the Natural Language to SQL Query Generator and Validator! This project bridges the gap between human language and SQL, making it easy for anyone to query databases or learn SQL—no prior SQL knowledge required.

- **Faculty:** Instantly evaluate student SQL lab sheets, provide feedback, and save time.
- **Students:** Practice writing SQL, get instant feedback, and learn with explanations.

---

## 2. 🏗️ Architecture Flow (Step-by-Step)

1. **User Interface (Streamlit Web App):**
   - Enter your question in plain English (e.g., "List all customers who have not placed orders.")
   - See the generated SQL, validation results, and query output.

2. **Backend Modules:**
   - **Schema & Relationship Extractor:**
     - Connects to PostgreSQL, fetches table/column names, and foreign key relationships.
   - **Prompt Generator:**
     - Builds a smart prompt using your question, schema, and relationships.
   - **FLAN-T5 Model (HuggingFace):**
     - Generates SQL from the prompt using a local transformer model.
   - **SQL Validator:**
     - Checks SQL syntax (using EXPLAIN) and provides error messages if any.
   - **Query Executor:**
     - Runs the SQL on the database and returns results or errors.

3. **Output (Streamlit):**
   - Displays the generated SQL, validation status, and query results in a friendly format.

---

## 3. 🧩 Technology Stack

| Layer                | Technology                           |
|----------------------|--------------------------------------|
| UI                   | Streamlit                            |
| AI Model             | HuggingFace Transformers (FLAN-T5)   |
| Tokenizer            | AutoTokenizer                        |
| SQL Database         | PostgreSQL                           |
| Database Access      | psycopg2                             |
| Prompt Engineering   | Python string templates              |
| Validation/Execution | SQL + EXPLAIN + cursor.execute()     |
| Schema Introspection | information_schema tables            |

---

## 4. ✨ Key Features

- **Natural Language to SQL:** Type questions in English, get SQL instantly.
- **Schema Awareness:** Model understands your database structure and relationships.
- **Validation & Feedback:** Checks SQL for errors, explains mistakes, and suggests corrections.
- **Real-Time Execution:** Runs queries and shows results or errors immediately.
- **PDF Lab Sheet Grading:** Faculty can upload student lab sheets (PDF), auto-grade, and provide feedback.
- **Chatbot Assistant:** Ask SQL-related questions and get instant help.

---

## 5. 🎓 How It Helps

- **For Faculty:**
  - Quickly evaluate student SQL assignments and lab sheets.
  - Provide instant, detailed feedback and grades.
  - Save hours of manual checking!

- **For Students:**
  - Practice writing SQL and get real-time feedback.
  - Learn from explanations and corrections.
  - Upload your work and see where you can improve.

---

## 6. 🛠️ Setup Instructions

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/umeshreddy07/Sql_generator_validator.git
   cd sqlgeneratot\ validator
   ```
2. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Secrets:**
   - Add your Google Gemini API key to `.streamlit/secrets.toml` (see Streamlit docs).
4. **Start the App:**
   ```bash
   streamlit run app/main.py
   ```
5. **Enjoy!**
   - Open the Streamlit web app in your browser and start generating SQL from natural language!

---

## 7. 👩‍💻 Credits & Acknowledgements

- Built by students and faculty at Amrita Vishwa Vidyapeetham, Amritapuri, India.
- Powered by HuggingFace Transformers, Streamlit, PostgreSQL, and Google Gemini API.
- Special thanks to all contributors and testers!

---

## 8. 📈 Future Features

- Auto-suggestions for table/column names
- Explain SQL in natural language
- Visual schema explorer
- Save query history
- Multi-language support

---

**Questions? Suggestions?** Open an issue or contact the authors above! 