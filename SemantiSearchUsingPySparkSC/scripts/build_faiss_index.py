import pandas as pd
import numpy as np
import faiss

# Load embedded data
df = pd.read_parquet("data/embedded_complaints.parquet")

embeddings = np.vstack(df['embedding'].values).astype('float32')

# Build FAISS index
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

# Save index
faiss.write_index(index, "data/faiss_index.bin")
df[['complaint_id', 'product', 'complaint_text']].to_csv("data/metadata.csv", index=False)

print(f"✅ FAISS index built and saved ({embeddings.shape[0]} vectors)")
