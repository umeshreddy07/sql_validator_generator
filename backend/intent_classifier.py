def classify_intent(nl_query):
    """Classify the intent of the query as SELECT/INSERT/UPDATE/DELETE."""
    # Placeholder: simple keyword-based intent classification
    q = nl_query.lower()
    if any(word in q for word in ["get", "show", "find", "select"]):
        return "SELECT"
    elif any(word in q for word in ["add", "insert", "create"]):
        return "INSERT"
    elif any(word in q for word in ["update", "change", "modify"]):
        return "UPDATE"
    elif any(word in q for word in ["delete", "remove"]):
        return "DELETE"
    else:
        return "SELECT"  # Default fallback 