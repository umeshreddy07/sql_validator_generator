def chatbot_response(user_input):
    """Basic rule-based chatbot for guidance and explanations."""
    user_input = user_input.lower()
    if "hello" in user_input or "hi" in user_input:
        return "Hello! I can help you convert natural language to SQL. Ask me anything!"
    elif "help" in user_input:
        return "Type your question in plain English, and I'll generate the SQL for you."
    elif "example" in user_input:
        return "For example: 'Get all employees in Engineering department'."
    elif "explain" in user_input:
        return "I generate SQL queries using a language model trained on text-to-SQL datasets."
    else:
        return "I'm here to help! Ask me about SQL queries or how to use this app." 