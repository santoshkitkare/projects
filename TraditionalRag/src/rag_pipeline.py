# Data preparation
from prepare_data import prepare_docs
from split_text import split_docs

# Embedding and storage
from create_embeddings import get_embeddings
from store_faiss import build_faiss_index, save_metadata

# Retrieval and answer generation
from generate_answer import generate_answer

def run_pipeline():
    """
    Runs the full end-to-end RAG workflow.
    """
    print("\nLoad and Clean Data:")
    documents = prepare_docs("../data/")
    print(f"Loaded {len(documents)} clean documents.\n")

    print("Split Text into Chunks:")
    # documents is a list of strings, but split_docs expects a list of documents
    # For this simple example where documents are small, we pass them as strings
    chunks_as_text = split_docs(documents, chunk_size=500, chunk_overlap=100)
    # In this case, chunks_as_text is a list of LangChain Document objects

    # Extract text content from LangChain Document objects
    texts = [c.page_content for c in chunks_as_text]
    print(f"Created {len(texts)} text chunks.\n")

    print("Generate Embeddings:")
    embeddings = get_embeddings(texts)
  
    print("Store Embeddings in FAISS:")
    index = build_faiss_index(embeddings)
    save_metadata(texts)
    print("Stored embeddings and metadata successfully.\n")

    print("Retrieve & Generate Answer:")
    query = "Does unsupervised ML cover regression tasks?"
    generate_answer(query)
    
if __name__ == "__main__":
    run_pipeline()