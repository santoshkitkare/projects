from load_data import load_documents
from clean_data import clean_text

def prepare_docs(folder_path="data/"):
    """
    Loads and cleans all text documents from the given folder.
    """
    # Load Documents
    raw_docs = load_documents(folder_path)

    # Clean Documents
    cleaned_docs = [clean_text(doc) for doc in raw_docs]

    print(f"Prepared {len(cleaned_docs)} documents.")
    return cleaned_docs