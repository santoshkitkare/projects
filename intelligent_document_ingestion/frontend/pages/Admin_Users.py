import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

if "access_token" not in st.session_state:
    st.switch_page("Login")

TOKEN = st.session_state["access_token"]
headers = {"Authorization": f"Bearer {TOKEN}"}

st.title("⚙ Admin — User Management")
st.set_page_config(page_title="Admin User", layout="centered")

if st.session_state["role"] != "admin":
    st.error("⛔ Admin access only")
    st.stop()

# List users
res = requests.get(f"{BACKEND_URL}/admin/users", headers=headers)
if res.status_code == 401:
    st.warning("Session expired. Login again.")
    st.session_state.clear()
    st.switch_page("Login")

users = res.json()

st.subheader("Existing Users")
for user in users:
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        col1.write(user["username"])
        col2.write(user["role"])
        col3.write(user["created_at"].replace("T"," ").split(".")[0])

        if col4.button("🗑 Delete", key=f"del-{user['userId']}"):
            requests.delete(f"{BACKEND_URL}/admin/users/{user['userId']}", headers=headers)
            st.success("User deleted")
            st.rerun()


# Create new user
st.subheader("➕ Create New User")
new_user = st.text_input("Username")
new_pass = st.text_input("Password", type="password")
new_role = st.selectbox("Role", ["system", "admin"])

if st.button("Add User"):
    res = requests.post(
        f"{BACKEND_URL}/admin/users",
        json={"username": new_user, "password": new_pass, "role": new_role},
        headers=headers
    )
    if res.status_code == 200:
        st.success("User added")
        st.rerun()
    else:
        st.error(res.json().get("detail"))
