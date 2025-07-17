import spacy

nlp = spacy.load("en_core_web_sm")

def preprocess_text(text):
    """Clean and tokenize user input using spaCy."""
    doc = nlp(text)
    tokens = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
    return " ".join(tokens) 