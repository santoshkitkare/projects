import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from copy import deepcopy

class RagRetriever:
    def __init__(self, config, data_path="."):
        """
        

        Args:
            config (_type_): {"index_file": self.index_file, "metadata_file": self.metadata_file}
        """
        self.index_path = config["index_file"]
        print(f"Loading FAISS index from {data_path}/{self.index_path}...")
        self.faiss_index = faiss.read_index(f"{data_path}/{self.index_path}")
        
        self.metadata_path = config["metadata_file"]
        print(f"Loading metadata from {data_path}/{self.metadata_path}...")
        with open(f"{data_path}/{self.metadata_path}", "rb") as f:
            self.metadata = pickle.load(f)
        
        self.sc_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    

    def search(self, query, top_k=5):
        """
        Search the FAISS index for the most similar documents to the query.

        Args:
            query (_type_): _description_
        """
        query_embedding = self.sc_model.encode([query]).astype('float32')
        distances, indices = self.faiss_index.search(query_embedding, top_k)
        
        results = []
        for idx in indices[0]:
            data = deepcopy(self.metadata[idx])
            # data["score"] = distances[0][list(indices[0]).index(idx)]
            data.page_content = f"[Score: {distances[0][list(indices[0]).index(idx)]:.4f}] " + data.page_content
            results.append(data)
        
        results2 = []
        for rank, idx in enumerate(indices[0]):
            doc = deepcopy(self.metadata[idx])
            doc.page_content = f"[Rank: {rank+1} | Score: {distances[0][rank]:.4f}] " + doc.page_content
            results2.append(doc)
        return results, results2
    
if __name__ == "__main__":
    config = {
        "index_file": "output/faiss_index.index",
        "metadata_file": "output/faiss_metadata.pkl"
    }
    retriever = RagRetriever(config, data_path=".")
    query = "What is the capital of France?"
    results, results2 = retriever.search(query, top_k=3)
    print("=========================  Results with Scores: ========================")
    for i, res in enumerate(results):
        print(f"Result {i+1}: {res.page_content}")
        
    print("=========================  Results with Ranks and Scores: ========================")
    for i, res in enumerate(results2):
        print(f"Result {i+1}: {res.page_content}")