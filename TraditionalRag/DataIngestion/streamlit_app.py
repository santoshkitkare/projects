import streamlit as st
import pandas as pd
import re
import os
from langchain_core.documents import Document
from data_ingestion import DataIngestion

st.set_page_config(page_title="Traditional RAG Demo", layout="centered")

# ----------------------------------------------
# Cache ingestion object to avoid repeated model loading
# ----------------------------------------------
@st.cache_resource
def load_ingestion():
    return DataIngestion(output_folder="output/")

data_ingestion = load_ingestion()

# ----------------------------------------------
# Header
# ----------------------------------------------
st.title("Traditional Rag Demonstration")

# ----------------------------------------------
# FILE UPLOAD SECTION
# ----------------------------------------------
st.subheader("📁 Upload New File")

uploaded_file = st.file_uploader(
    "Upload a document (PDF, TXT, DOCX)",
    type=["pdf", "txt", "docx"]
)

if uploaded_file:
    # Save file to local disk
    save_path = os.path.join("uploaded_files", uploaded_file.name)
    os.makedirs("uploaded_files", exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())

    # Ingest the file
    try:
        data_ingestion.add_new_file(save_path, clear_existing=True)
        st.success(f"File uploaded & ingested successfully: {uploaded_file.name}")
    except Exception as e:
        st.error(f"Error during ingestion: {e}")

st.markdown("---")


# ----------------------------------------------
# QUESTION SECTION
# ----------------------------------------------
st.subheader("🔍 Ask a Question")

question = st.text_input("Enter your question")

def extract_score(content: str):
    """Extracts score from '[Score: X.XXXX]' prefix if exists"""
    match = re.match(r"\[Score:\s*([0-9.]+)\]", content)
    return float(match.group(1)) if match else None

def clean_page_content(content: str):
    """Removes '[Score: X.XXXX]' prefix from text"""
    return re.sub(r"^\[Score:\s*[0-9.]+\]\s*", "", content)


if st.button("Get Answer"):
    if question.strip():
        try:
            # CALL YOUR RAG PIPELINE ANSWERING FUNCTION HERE
            docs, answer = data_ingestion.get_answer(question)

            # Show answer
            st.success(f"🟢 Answer:\n\n{answer}")

            # Show retrieved documents in table
            if docs and isinstance(docs, list):

                result_rows = []
                for idx, doc in enumerate(docs):
                    if not isinstance(doc, Document):
                        continue
                    
                    score = extract_score(doc.page_content)
                    text = clean_page_content(doc.page_content)

                    result_rows.append({
                        "Rank": idx + 1,
                        "Score": score,
                        "Page": doc.metadata.get("page"),
                        "Source": doc.metadata.get("source"),
                        "Text Preview": text[:200] + ("..." if len(text) > 200 else "")
                    })

                df = pd.DataFrame(result_rows)
                st.dataframe(df, width="stretch")

            else:
                st.info("No relevant documents found.")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a valid question.")
