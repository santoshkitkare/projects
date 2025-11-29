import streamlit as st
import requests
import time
import json
from datetime import datetime
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Dashboard", page_icon="📄", layout="wide")

# Redirect not logged in users
if "access_token" not in st.session_state:
    st.switch_page("pages/Login.py")

TOKEN = st.session_state["access_token"]
headers = {"Authorization": f"Bearer {TOKEN}"}

st.header("📄 Document Processing Portal")
st.write(
    f"👤 Logged in as: `{st.session_state['username']}` "
    f"({st.session_state['role'].upper()})"
)

# ----------------- Logout -----------------
if st.button("🚪 Logout", type="secondary"):
    st.session_state.clear()
    st.switch_page("pages/Login.py")

# ----------------- Upload File -----------------
st.subheader("📤 Upload New Document")

uploaded_file = st.file_uploader(
    "Upload document",
    type=["pdf", "csv", "png", "jpg", "jpeg", "docx", "xlsx"],
)

userId = st.session_state["user_id"]

if uploaded_file:
    if st.button("Start Upload 🚀", use_container_width=True):
        file_bytes = uploaded_file.getvalue()
        file_size = len(file_bytes)

        payload = {
            "userId": userId,
            "fileName": uploaded_file.name,
            "fileSize": file_size,
            "fileType": uploaded_file.type,
        }
        res = requests.post(
            f"{BACKEND_URL}/api/v1/uploads/request",
            json=payload,
            headers=headers,
        )

        if res.status_code == 401:
            st.warning("Session expired. Please login again.")
            st.session_state.clear()
            st.switch_page("pages/Login.py")

        if res.status_code != 200:
            st.error(res.json())
            st.stop()

        data = res.json()
        fileId = data["fileId"]

        # Upload to S3
        with st.spinner("⏫ Uploading to S3..."):
            upload_res = requests.put(
                data["uploadUrl"],
                data=file_bytes,
            )
        if upload_res.status_code not in [200, 204]:
            st.error("❌ Upload failed")
            st.stop()

        st.success("Upload completed, queuing job...")
        requests.post(
            f"{BACKEND_URL}/api/v1/uploads/complete",
            json={"fileId": fileId},
            headers=headers,
        )

        # For very large files, avoid tight polling
        if file_size > 20 * 1024 * 1024:  # > 20 MB
            st.info(
                "Large file detected. Processing may take a while — "
                "you can monitor status in the history table below."
            )
            st.stop()

        # Polling progress (adaptive interval)
        progress = st.progress(0)
        status_text = st.empty()
        pct = 0
        poll_interval = 2
        max_interval = 8

        while True:
            time.sleep(poll_interval)
            r = requests.get(
                f"{BACKEND_URL}/api/v1/uploads/{fileId}/status",
                headers=headers,
            )
            if r.status_code == 401:
                st.warning("Session expired. Login again.")
                st.session_state.clear()
                st.switch_page("pages/Login.py")

            data = r.json()
            status = data["status"]

            status_text.write(f"📌 Status: {status} — {data['message']}")

            if status == "processing":
                # slow ramp-up for long-running jobs
                pct = min(pct + 5, 90)
                progress.progress(pct)
                if poll_interval < max_interval:
                    poll_interval += 1  # backoff to reduce load

            if status == "pending":
                # queued but not yet picked — also back off
                if poll_interval < max_interval:
                    poll_interval += 1

            if status == "failed":
                progress.progress(100)
                st.error(data.get("error", "Processing failed"))
                break

            if status == "completed":
                progress.progress(100)
                st.success("🎉 Processing Completed!")
                st.json(data["metadata"])
                if data["downloadUrl"]:
                    # NOTE: Streamlit can't directly download from URL content,
                    # so we show URL or you can proxy through backend if needed.
                    st.write("Download URL:")
                    st.code(data["downloadUrl"])
                break

# ----------------- Document History -----------------
st.subheader("📜 Upload History")
res = requests.get(
    f"{BACKEND_URL}/api/v1/uploads/user/{userId}",
    headers=headers,
)

if res.status_code == 401:
    st.warning("Session expired. Login again.")
    st.session_state.clear()
    st.switch_page("pages/Login.py")

history = res.json()

# ---------- Header row ----------
with st.container():
    col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
    col1.markdown("#### 📄 File Name")
    col2.markdown("#### ⚙️ Status")
    col3.markdown("#### ⏱ Uploaded")
    col4.markdown("#### 🔧 Actions")

# ---------- History Table ----------
for item in history:
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 3])

        col1.write(f"📄 **{item['fileName']}**")
        col2.write(f"🕒 {item['status']}")
        if item["uploadedAt"]:
            col3.write(item["uploadedAt"].replace("T", " ").split(".")[0])
        else:
            col3.write("-")

        with col4:
            a, b, c, d = st.columns(4)

            # Download
            if item["status"] == "completed":
                if a.button("⬇", key=f"dl-{item['fileId']}"):
                    r = requests.get(
                        f"{BACKEND_URL}/api/v1/uploads/{item['fileId']}/download",
                        headers=headers,
                    )
                    if r.status_code == 200:
                        st.write(r.json()["downloadUrl"])
                    else:
                        st.error("Unable to get download URL")

            # View Metadata
            if item["status"] == "completed":
                if b.button("🔍", key=f"meta-{item['fileId']}"):
                    st.session_state["view_metadata_fileId"] = item["fileId"]

            # Retry (only if failed)
            if item["status"] == "failed":
                if c.button("🔁", key=f"retry-{item['fileId']}"):
                    requests.post(
                        f"{BACKEND_URL}/api/v1/uploads/{item['fileId']}/retry",
                        headers=headers,
                    )
                    st.success("Retry triggered")
                    st.rerun()

            # Delete (always visible)
            if d.button("🗑", key=f"del-{item['fileId']}"):
                requests.delete(
                    f"{BACKEND_URL}/api/v1/uploads/{item['fileId']}",
                    headers=headers,
                )
                st.success("Deleted")
                st.rerun()

# ---------- Metadata Viewer Panel ----------
if "view_metadata_fileId" in st.session_state:
    fileId = st.session_state["view_metadata_fileId"]

    res = requests.get(
        f"{BACKEND_URL}/api/v1/uploads/{fileId}/status",
        headers=headers,
    )

    if res.status_code == 200:
        meta = res.json().get("metadata")

        st.markdown("---")
        st.markdown("### 📌 Extracted Metadata")

        meta_query = st.text_input("Search in metadata", key="meta_search_box")

        if meta_query and meta:
            q = meta_query.lower()
            filtered = {}
            for k, v in meta.items():
                v_str = json.dumps(v).lower()
                if q in k.lower() or q in v_str:
                    filtered[k] = v
            meta = filtered

        st.json(meta)

        if st.button("❌ Close metadata panel", key="meta_close"):
            del st.session_state["view_metadata_fileId"]
            st.rerun()

# 🚨 Show Admin page link for Admin users
if st.session_state["role"] == "admin":
    st.page_link("pages/Admin_Users.py", label="⚙ Admin User Management")
