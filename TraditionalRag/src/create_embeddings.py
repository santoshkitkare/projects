from sentence_transformers import SentenceTransformer
import numpy as np

def get_embeddings(text_chunks):
  
   # Load embedding model
   model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
  
   print(f"Creating embeddings for {len(text_chunks)} chunks:")
   embeddings = model.encode(text_chunks, show_progress_bar=True)
  
   print(f"Embeddings shape: {embeddings.shape}")
   return np.array(embeddings)