import streamlit as st
import requests

def send_to_webhook(data):
    """Hàm gửi dữ liệu về Webhook để lưu trữ hoặc gửi mail"""
    WEBHOOK_URL = st.secrets.get("WEBHOOK_URL")
    if not WEBHOOK_URL:
        return
    try:
        requests.post(WEBHOOK_URL, json=data, timeout=5)
    except:
        pass

def display_sidebar_auth():
    """Luôn hiển thị trên Sidebar ở mọi trang"""
    with st.sidebar:
        st.title("🛡️ Research Factory")
        
        # Get language from session state
        lang = st.session_state.get('lang', 'English')
        
        # Check authentication settings
        if 'user_email' in st.session_state and st.session_state.user_email:
            st.success(f"👤 {st.session_state.user_email}")
            logout_label = "Đăng xuất" if lang == "Tiếng Việt" else "Logout"
            if st.button(logout_label):
                del st.session_state.user_email
                st.rerun()
        else:
            auth_header = "🔑 Tài khoản" if lang == "Tiếng Việt" else "🔑 Account"
            login_tab_label = "Đăng nhập" if lang == "Tiếng Việt" else "Login"
            register_tab_label = "Đăng ký" if lang == "Tiếng Việt" else "Register"
            
            st.subheader(auth_header)
            tab1, tab2 = st.tabs([login_tab_label, register_tab_label])

            with tab1:
                email_label = "Email"
                pass_label = "Mật khẩu" if lang == "Tiếng Việt" else "Password"
                confirm_label = "Xác nhận Đăng nhập" if lang == "Tiếng Việt" else "Confirm Login"
                
                email = st.text_input(email_label, key="login_email")
                password = st.text_input(pass_label, type="password", key="login_pass")
                if st.button(confirm_label, use_container_width=True):
                    if email and password:
                        send_to_webhook({"action": "LOGIN", "email": email})
                        st.session_state.user_email = email
                        st.success("Signed in!" if lang == "English" else "Đã đăng nhập!")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập đủ thông tin." if lang == "Tiếng Việt" else "Please fill in all fields.")

            with tab2:
                no_account_msg = "Bạn chưa có tài khoản?" if lang == "Tiếng Việt" else "Don't have an account?"
                create_label = "Tạo tài khoản mới" if lang == "Tiếng Việt" else "Create new account"
                st.write(no_account_msg)
                if st.button(create_label, use_container_width=True):
                    st.session_state.step = "DANG_KY_FORM"
                    st.rerun()

        st.divider()
        st.caption("© 2026 Young Scientist Supporter")
