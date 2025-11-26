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

# if "access_token" not in st.session_state:
#     st.session_state["access_token"] = None
#     st.session_state["role"] = None
#     st.session_state["user_id"] = None
#     st.session_state["username"] = None


if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
    
if "access_token" not in st.session_state or not st.session_state["access_token"]:
    st.switch_page("pages/Login.py")
    
# if "access_token" not in st.session_state:
#     st.warning("Please log in first.")
#     st.switch_page("pages/Login.py")

# def login_view():
#     st.title("🔐 Document Portal Login")

#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")

#     if st.button("Login"):
#         data = {
#             "username": username,
#             "password": password,
#         }
#         res = requests.post(
#             f"{BACKEND_BASE_URL}/auth/login",
#             data=data,  # form-data for OAuth2PasswordRequestForm
#         )
#         if res.status_code == 200:
#             body = res.json()
#             st.session_state["access_token"] = body["accessToken"]
#             st.session_state["role"] = body["role"]
#             st.session_state["user_id"] = body["userId"]
#             st.session_state["username"] = body["username"]
#             st.success("Logged in!")
#             st.experimental_rerun()
#         else:
#             st.error("Invalid username or password")

with st.sidebar:
    role = st.session_state.get("role")
    if role:
        st.write(f"👤 Logged in as: {role.capitalize()}")
        st.write(f"👤 Logged in as: {st.session_state['role'].capitalize()}")
        if st.button("Logout"):
            st.session_state["access_token"] = None
            st.session_state["user_id"] = None
            st.session_state["role"] = None
            st.switch_page("pages/Login.py")


# if not st.session_state["access_token"]:
#     st.switch_page("Login.py")


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
        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
        res = requests.post(f"{BACKEND_BASE_URL}/api/v1/uploads/request", json=req_payload, headers=headers)

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
            st.balloons()

            with st.expander("🔍 Extracted Metadata", expanded=True):
                if metadata:
                    st.json(metadata)
                else:
                    st.info("⚠ No metadata extracted")
            if download_url:
                st.download_button(
                    label="⬇ Download Original File",
                    data=requests.get(download_url).content,
                    file_name=status["metadata"].get("originalFileName", "document.pdf")
                )
            else:
                st.info("⚠ Download URL not available")
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

st.subheader("📜 Upload History")

headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
hist_res = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/user/{st.session_state['user_id']}", headers=headers)

if hist_res.status_code == 200 and hist_res.json():
    history = hist_res.json()

    for item in history:
        file_id = item["fileId"]
        file_name = item["fileName"]
        status = item["status"]
        uploaded_at = item["uploadedAt"]
        completed_at = item["completedAt"]
        error_msg = item.get("error")

        # Row Layout
        col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 2, 2, 1, 1, 1, 1])
        col1.write(file_name)
        col2.write(status)
        col3.write(uploaded_at)

        # 🟢 ⬇ Download (only when completed)
        if status == "completed":
            if col4.button("⬇", key=f"dl_{file_id}"):
                r = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}/download")
                if r.status_code == 200:
                    dl = r.json()["downloadUrl"]
                    st.session_state["download_url"] = dl
                    st.session_state["download_name"] = file_name
                else:
                    st.error("Failed to fetch download URL")

        # ⚠ Error Viewer (only when failed)
        if status == "failed":
            if col4.button("⚠", key=f"err_{file_id}"):
                st.error(error_msg or "No error details available")

        # 🔁 Retry processing (only when failed)
        if status == "failed":
            if col5.button("🔁", key=f"retry_{file_id}"):
                requests.post(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}/retry")
                st.success(f"Retry triggered for {file_name}")
                st.rerun()

        # 🔍 Metadata side panel (only when completed)
        if status == "completed":
            if col5.button("🔍", key=f"meta_{file_id}"):
                r = requests.get(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}/status")
                metadata = r.json().get("metadata", {})
                st.sidebar.title("📌 Metadata Viewer")
                st.sidebar.json(metadata)

        # 🗑 Delete (always visible)
        if col6.button("🗑", key=f"del_{file_id}"):
            delete_res = requests.delete(f"{BACKEND_BASE_URL}/api/v1/uploads/{file_id}")
            if delete_res.status_code == 200:
                st.warning(f"{file_name} deleted")
                st.rerun()
            else:
                st.error("Failed to delete")

        # Completed timestamp display (col7)
        if completed_at:
            col7.write(completed_at)
else:
    st.info("No uploads yet.")
