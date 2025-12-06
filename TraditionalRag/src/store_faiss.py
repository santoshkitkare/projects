import faiss
import numpy as np
import pickle

def build_faiss_index(embeddings, save_path="faiss_index"):
   """
   Builds FAISS index and saves it.
   """
   dim = embeddings.shape[1]
   print(f"Building FAISS index with dimension: {dim}")

   # Use a simple flat L2 index
   index = faiss.IndexFlatL2(dim)
   index.add(embeddings.astype('float32'))

   # Save FAISS index
   faiss.write_index(index, f"{save_path}.index")
   print(f"Saved FAISS index to {save_path}.index")

   return index

def save_metadata(text_chunks, path="faiss_metadata.pkl"):
   """
   Saves the mapping of vector positions to text chunks.
   """
   with open(path, "wb") as f:
       pickle.dump(text_chunks, f)
   print(f"Saved text metadata to {path}")