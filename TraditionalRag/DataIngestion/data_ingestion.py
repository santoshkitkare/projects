import glob
import os
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from copy import deepcopy

FAISS_INDEX_FILE = "faiss_index.index"
METADATA_FILE = "faiss_metadata.pkl"

class DataIngestion:
    _model_cache = None  # Class-level cache for the SentenceTransformer model
    
    def __init__(self, output_folder="output/", chunk_size=500, chunk_overlap=100):
        self.output_folder = output_folder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if DataIngestion._model_cache is None:
            DataIngestion._model_cache = SentenceTransformer(
                'sentence-transformers/all-MiniLM-L6-v2'
            )
        self.sc_model = DataIngestion._model_cache
        
        self.embedding_dimension = self.sc_model.get_sentence_embedding_dimension()
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dimension)
        
        # Create output paths
        os.makedirs(self.output_folder, exist_ok=True)
        self.metadata_file = f"{self.output_folder}{METADATA_FILE}"
        self.index_file = f"{self.output_folder}{FAISS_INDEX_FILE}"
        
        # If existing index and metadata files are present, load them
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            print(f"Loading existing FAISS index from {self.index_file}...")
            self.faiss_index = faiss.read_index(self.index_file)
            with open(self.metadata_file, "rb") as f:
                self.split_documents = pickle.load(f)
        else:
            print("No existing FAISS index found. A new index will be created upon data ingestion.")
            
        
    def _read_files(self, folder_path):
        """
        Data Ingestion from various file formats in the specified folder.

        Args:
            folder_path (_type_): _description_

        Returns:
            _type_: _description_
        """
        all_documents = []
        text_documents = []
        pdf_documents = []
        
        txt_files = glob.glob(f"{folder_path}/*.txt")
        for file in txt_files:
            txt_loader = TextLoader(file, encoding='utf-8')
            txt_doc = txt_loader.load()
            text_documents.extend(txt_doc)
            all_documents.extend(txt_doc)
            
        pdf_files = glob.glob(f"{folder_path}/*.pdf")
        for file in pdf_files:
            pdf_loader = PyMuPDFLoader(file)
            pdf_doc = pdf_loader.load()
            pdf_documents.extend(pdf_doc)
            all_documents.extend(pdf_doc)

        return all_documents

    def add_new_file(self, file_path):
        """
        Add a new file to the existing FAISS index.

        Args:
            file_path (_type_): _description_
        """
        try:
            # Load existing metadata
            if self.faiss_index.ntotal == 0:    
                if os.path.exists(self.metadata_file) and os.path.exists(self.index_file):
                    with open(self.metadata_file, "rb") as f:
                        self.split_documents = pickle.load(f)
                    self.faiss_index = faiss.read_index(self.index_file)
                else:
                    self.split_documents = []
                    self.faiss_index = faiss.IndexFlatL2(self.embedding_dimension)
            
            # Load new document
            if file_path.endswith(".txt"):
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_path.endswith(".pdf"):
                loader = PyMuPDFLoader(file_path)
            else:
                print(f"Unsupported file format: {file_path}")
                return
            
            new_docs = loader.load()
            
            # Split new documents
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
            new_split_docs = text_splitter.split_documents(new_docs)
            
            # Create embeddings for new documents
            new_embeddings = self._create_embeddings([doc.page_content for doc in new_split_docs])
            
            # Add new embeddings to FAISS index
            self.faiss_index.add(new_embeddings)
            
            # Update metadata
            self.split_documents.extend(new_split_docs)
            
            # Save updated metadata and FAISS index
            with open(self.metadata_file, "wb") as f:
                pickle.dump(self.split_documents, f)
            
            faiss.write_index(self.faiss_index, self.index_file)
        except Exception as e:
            print(f"Error adding new file {file_path}: {e}")
            raise e

    def _create_embeddings(self, text_chunks):
        """
        Create embeddings for the given text chunks and add them to the FAISS index.

        Args:
            text_chunks (_type_): _description_
        """
        print(f"Creating embeddings for {len(text_chunks)} chunks:")
        embeddings = self.sc_model.encode(text_chunks, show_progress_bar=True)
        print(f"Embeddings shape: {embeddings.shape}")
        
        # Convert embeddings to float32 as required by FAISS
        embeddings = embeddings.astype('float32')
        
        return embeddings
    
    
    def ingest_data(self, folder_path):
        """
        Ingest data from the specified folder.

        Args:
            folder_path (_type_): _description_
        """
        # Read Data from files
        documents = self._read_files(folder_path)
        
        # Split the document in chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        self.split_documents = text_splitter.split_documents(documents)
        
        if not hasattr(self, "faiss_index"):
            self.faiss_index = faiss.IndexFlatL2(self.embedding_dimension)
            print(f"Total documents after splitting: {len(self.split_documents)}")
        
        # Create embeddings and add to FAISS index
        embeddings = self._create_embeddings([doc.page_content for doc in self.split_documents])
        
        # Add embeddings to FAISS index
        self.faiss_index.add(embeddings)
        print(f"Total vectors in FAISS index: {self.faiss_index.ntotal}")
                
        # Store metadata for retrieval
        with open(self.metadata_file, "wb") as f:
            pickle.dump(self.split_documents, f)
        
        # Save the FAISS index to a file
        faiss.write_index(self.faiss_index, self.index_file)
        
        return {"index_file": self.index_file, "metadata_file": self.metadata_file}

    
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
            # results.append(self.split_documents[idx])
            data = deepcopy(self.split_documents[idx])
            # data["score"] = distances[0][list(indices[0]).index(idx)]
            data.page_content = f"[Score: {distances[0][list(indices[0]).index(idx)]:.4f}] " + data.page_content
            results.append(data)
        
        print(f"Search results for query: {query} : {results}")
        return results
    
    
if __name__ == "__main__":
    data_ingestion = DataIngestion(output_folder="output/")
    data_config = data_ingestion.ingest_data("../data/")
    print(f"Total documents ingested: {data_config}")
    
    query = "What is the supervised learning?"
    results = data_ingestion.search(query, top_k=3)
    
    print("=================================  Search Results ========================")
    print("Search Results for {query}")
    for result in results:
        print(result.page_content)
        
    
    print("=========================  End of Ingestion and Search ========================")
        
    # Ingest new document
    # read new file path from user
    new_file_Path = input("Enter the path of the new file to ingest (txt or pdf): ")
    data_ingestion.add_new_file(new_file_Path)
    while True:
        query = input("Enter your search query (or type 'exit' to quit): ")
        if query.lower() == 'exit' or query.lower() == 'quit':
            break
        results = data_ingestion.search(query, top_k=3)
        print("=================================  Search Results ========================")
        print(f"Search Results for \"{query}\":")
        for result in results:
            print(result.page_content)
        print("=================================  End of Search ========================")