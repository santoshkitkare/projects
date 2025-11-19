import streamlit as st
from langchain_core.documents import Document
from data_ingestion import DataIngestion
import pandas as pd
import re

st.set_page_config(page_title="Traditional RAG Demo", layout="centered")

data_ingestion = DataIngestion(output_folder="output/")
# ---- Header ----
st.title("Traditional Rag Demonstration")

# ---- File ingestion UI ----
st.subheader("📁 Add New File")

filename = st.text_input("Enter filename to ingest")


if st.button("Ingest File"):
    if filename.strip():
        try:
            data_ingestion.add_new_file(filename)
            st.success(f"Data ingested successfully for: {filename}")
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a valid filename.")

st.markdown("---")

# ---- Question UI ----
st.subheader("🔍 Ask a Question")

question = st.text_input("Question")

def extract_score(content: str):
    """Extracts score from '[Score: X.XXXX]' prefix if exists"""
    match = re.match(r"\[Score:\s*([0-9.]+)\]", content)
    return float(match.group(1)) if match else None

def clean_page_content(content: str):
    """Removes '[Score: X.XXXX]' prefix from text"""
    return re.sub(r"^\[Score:\s*[0-9.]+\]\s*", "", content)

if st.button("Search"):
    if question.strip():
        try:
            docs = data_ingestion.search(question)  # list of Document objects

            if isinstance(docs, list) and len(docs) > 0:

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
                        # trimmed for clean UI, keep full version separately if needed
                        "Text Preview": text[:200] + ("..." if len(text) > 200 else "")
                    })

                df = pd.DataFrame(result_rows)
                st.dataframe(df, use_container_width=True)

            else:
                st.info("No results found.")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter a question.")