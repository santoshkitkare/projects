import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
st.sidebar.empty()  # hide sidebar

st.title("🔐 Login to Document Portal")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if not username or not password:
        st.error("Please enter both username and password")
    else:
        try:
            res = requests.post(
                f"{BACKEND_URL}/auth/login",
                data={"username": username, "password": password}
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state["access_token"] = data["accessToken"]
                st.session_state["user_id"] = data["userId"]
                st.session_state["username"] = data["username"]
                st.session_state["role"] = data["role"]
                st.success("Login successful!")
                st.switch_page("streamlit_app.py")
                # st.rerun()
            else:
                st.error(res.json().get("detail", "Login failed"))
        except Exception:
            st.error("Unable to reach backend")

# If already logged in → skip login screen
if st.session_state.get("access_token"):
    st.switch_page("streamlit_app.py")
    # st.rerun()