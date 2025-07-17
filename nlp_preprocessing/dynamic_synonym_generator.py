# nlp_preprocessing/dynamic_synonym_generator.py
import re

def _generate_synonym_map(schema_string: str) -> dict:
    """
    Automatically generates a synonym map from a database schema string.
    It finds all column names with underscores and creates synonyms.
    """
    synonym_map = {}
    # Regex to find all words that are likely column names inside the schema string.
    # It looks for words before an opening parenthesis or at the start of the column list.
    all_columns = re.findall(r'(\w+)\s*\(|\[\s*(\w+)|,\s*(\w+)', schema_string)
    # The regex returns tuples of capture groups, so we flatten the list and get unique names
    flat_columns = [item for sublist in all_columns for item in sublist if item]
    unique_columns = sorted(list(set(flat_columns)))
    for column in unique_columns:
        if '_' in column:
            # Create synonym by removing underscore (e.g., 'first_name' -> 'firstname')
            synonym_no_underscore = column.replace('_', '')
            if synonym_no_underscore:
                synonym_map[synonym_no_underscore] = column
            # Create synonym by replacing underscore with space (e.g., 'first_name' -> 'first name')
            synonym_with_space = column.replace('_', ' ')
            if synonym_with_space:
                synonym_map[synonym_with_space] = column
    print(f"Dynamically generated synonym map: {synonym_map}")
    return synonym_map

def replace_synonyms_dynamically(nl_query: str, schema_string: str) -> str:
    """
    Replaces known synonyms in the user's query with the correct database column names.
    """
    synonym_map = _generate_synonym_map(schema_string)
    sorted_synonyms = sorted(synonym_map.keys(), key=len, reverse=True)
    for synonym in sorted_synonyms:
        db_column = synonym_map[synonym]
        nl_query = re.sub(r'\b' + re.escape(synonym) + r'\b', db_column, nl_query, flags=re.IGNORECASE)
    print(f"Query after dynamic synonym replacement: {nl_query}")
    return nl_query 