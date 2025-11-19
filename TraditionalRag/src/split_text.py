#from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_docs(documents, chunk_size=500, chunk_overlap=100):
   # define the splitter
   splitter = RecursiveCharacterTextSplitter(
       chunk_size=chunk_size,
       chunk_overlap=chunk_overlap
   )

   # use the splitter to split docs into chunks
   chunks = splitter.create_documents(documents)
   print(f"Total chunks created: {len(chunks)}")

   return chunks