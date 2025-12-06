import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

def load_faiss_index(index_path="faiss_index.index"):
    """
    Loads the saved FAISS index from disk.
    """
    print("Loading FAISS index.")
    return faiss.read_index(index_path)

def load_metadata(metadata_path="faiss_metadata.pkl"):
    """
    Loads text chunk metadata (the actual text pieces).
    """
    print("Loading text metadata.")
    with open(metadata_path, "rb") as f:
        return pickle.load(f)
    
def retrieve_similar_chunks(query, index, text_chunks, top_k=3):
    """
    Retrieves top_k most relevant chunks for a given query.
  
    Parameters:
        query (str): The user's input question.
        index (faiss.Index): FAISS index object.
        text_chunks (list): Original text chunks.
        top_k (int): Number of top results to return.
  
    Returns:
        list: Top matching text chunks.
    """
  
    # Embed the query
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    # Ensure query vector is float32 as required by FAISS
    query_vector = model.encode([query]).astype('float32')
  
    # Search FAISS for nearest vectors
    distances, indices = index.search(query_vector, top_k)
  
    print(f"Retrieved top {top_k} similar chunks.")
    return [text_chunks[i] for i in indices[0]]