import streamlit as st
import requests
import time
import json
import base64
import time
import pandas as pd

BACKEND_BASE_URL = "http://localhost:8000"   # FastAPI backend running locally

st.set_page_config(page_title="Document Intelligence Platform", layout="centered")
st.title("📄 Document Processing Demo")


# -- UI Step 1: File Selection --
uploaded_file = st.file_uploader("Upload a file", type=["pdf", "csv", "png", "jpg", "jpeg", "docx"])

user_id = st.text_input("User ID", value="USR001")

if uploaded_file and user_id and st.button("Start Upload"):
    with st.spinner("Requesting upload URL..."):
        req_payload = {
            "userId": user_id,
            "fileName": uploaded_file.name,
            "fileSize": len(uploaded_file.getvalue()),
            "fileType": uploaded_file.type
        }
        res = requests.post(f"{BACKEND_BASE_URL}/api/v1/uploads/request", json=req_payload)

        if res.status_code != 200:
            st.error("Upload request failed: " + res.text)
            st.stop()

        data = res.json()
        file_id = data["fileId"]
        presigned_url = data["uploadUrl"]
        headers = data["headers"]
        print("Presigned URL and headers received: ", presigned_url, headers)

    with st.spinner("Uploading to S3..."):
        # headers = {"x-amz-content-sha256": "UNSIGNED-PAYLOAD"}
        # print("Sending headers:", upload_res.request.headers)
        upload_res = requests.put(presigned_url, data=uploaded_file.getvalue())
        # req = requests.Request("PUT", presigned_url, data=uploaded_file.getvalue())
        # prepared = req.prepare()

        # st.write("🚀 Final request headers:", dict(prepared.headers))

        # session = requests.Session()
        # upload_res = session.send(prepared)
        print(upload_res.status_code)
        print(upload_res.text)

        if upload_res.status_code not in [200, 204]:
            st.error("Upload to S3 failed")
            st.stop()

    st.success(f"Uploaded successfully. File ID: {file_id}")
    st.session_state["file_id"] = file_id
    
    complete_res = requests.post(
        f"{BACKEND_BASE_URL}/api/v1/uploads/complete",
        json={"fileId": file_id}
    )
    
    if complete_res.status_code != 200:
        st.error("Failed to mark upload complete")
        st.stop()


    status_placeholder = st.empty()
    progress = st.progress(0)

    for i in range(100):
        status = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}/status").json()
        status_placeholder.info(f"📌 Status: {status['status']} — {status['message']}")
        
        if status["status"] == "completed":
            progress.progress(100)
            metadata = status["metadata"]
            download_url = status["downloadUrl"]

            st.success("🎉 Processing completed!")

            with st.expander("🔍 Extracted Metadata", expanded=True):
                st.json(metadata)

            st.download_button(
                label="⬇ Download Original File",
                data=requests.get(download_url).content,
                file_name=status["metadata"].get("originalFileName", "document.pdf")
            )
            break
        elif status["status"] == "failed":
            st.error(f"❌ Failed: {status['error']}")
            st.stop()

        progress.progress(int((i/100) * 80))   # 0–80% during worker time
        time.sleep(3)


#  UI Step 2: Status Check + Preview --
if "file_id" in st.session_state:
    st.divider()
    file_id = st.session_state["file_id"]
    st.subheader("🔄 Processing Status")

    if st.button("Refresh Status"):
        res = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}/status")
        if res.status_code != 200:
            st.error("Error fetching status: " + res.text)
            st.stop()

        status_data = res.json()
        st.write(f"Status: **{status_data['status']}**")
        st.caption(status_data["message"])

        if status_data["status"] == "completed":
            st.success("Processing DONE 🎉")
            st.json(status_data["metadata"])

            if status_data.get("downloadUrl"):
                st.markdown(f"[⬇ Download Original File]({status_data['downloadUrl']})", unsafe_allow_html=True)

        elif status_data["status"] == "failed":
            st.error(status_data["error"])
            st.stop()

        else:
            st.info("Still cooking… refresh again 👀")

history = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/user/{user_id}").json()
df = pd.DataFrame(history)

if len(df) > 0:
    st.subheader("📜 Upload History")
    st.dataframe(df)
else:
    st.info("No previous uploads found")
