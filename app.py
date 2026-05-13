import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
import recipe_service as rs
from datetime import datetime
import time
import requests
import google.generativeai as genai
from groq import Groq
import DiaCam
import Display_Auth
import Article_Lab
import re
import os

def send_to_webhook(data):
    try:
        # Anh cần thêm WEBHOOK_URL vào file secrets.toml
        webhook_url = st.secrets.get("WEBHOOK_URL")
        if webhook_url:
            requests.post(webhook_url, json=data, timeout=5)
    except Exception as e:
        st.error(f"Lỗi gửi dữ liệu: {e}")

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Diabetes Research Factory", layout="wide")

# --- 2. TỪ ĐIỂN ĐA NGÔN NGỮ (DICTIONARY) ---
LANGUAGES = {
    "Tiếng Việt": {
        "title": "🛡️ Giải mã Thực phẩm, Đẩy lùi Tiểu đường",
        "tab1": "🍏 Trí tuệ Thực phẩm USDA",
        "tab2": "🛡️ Elite Foods Lab",
        "tab3": "📄 Về dự án",
        "search_label": "🔍 Tìm tên thực phẩm (VD: Yến mạch, Bông cải, Cá hồi)",
        "prev": "⬅️ Trang trước",
        "next": "Trang sau ➡️",
        "score_label": "Điểm sức khỏe Tiểu đường",
        "nut_title": "📊 Thành phần dinh dưỡng đầy đủ (Chuẩn USDA trên 100g)",
        "ai_title": "💡 Lời khuyên từ Chuyên gia AI",
        "scientific_summary": "🔬 Tóm tắt Khoa học",
        "dietary_guidance": "🌿 Hướng dẫn Chế độ ăn",
        "admin_title": "🛠️ Quản lý nội dung (Admin)",
        "publish_btn": "Xuất bản bài viết",
        "read_more": "Xem chi tiết",
        "discussion": "💬 Thảo luận",
        "comment_btn": "Gửi bình luận",
        "name_label": "Tên của bạn",
        "msg_label": "Ý kiến của bạn",
        "source": "© Nguồn dữ liệu: Thành phần thực phẩm của USDA",
        "register": "Đăng ký tài khoản nghiên cứu",
        "auth_header": "🔑 Tài khoản",
        "login_tab": "Đăng nhập",
        "register_tab": "Đăng ký",
        "email_label": "Email",
        "password_label": "Mật khẩu",
        "login_confirm": "Xác nhận Đăng nhập",
        "logout_btn": "Đăng xuất",
        "no_account": "Bạn chưa có tài khoản?",
        "create_account": "Tạo tài khoản mới",
        "tab4": "📸 Kiểm tra Thực phẩm"
    },
    "English": {
        "title": "🛡️ Decoding Food, Defeating Diabetes",
        "tab1": "🍏 USDA Food Intelligence",
        "tab2": "🛡️ Elite Foods Lab",
        "tab3": "📄 About Project",
        "search_label": "🔍 Search food name (e.g., Oats, Broccoli, Salmon)",
        "prev": "⬅️ Previous Page",
        "next": "Next Page ➡️",
        "score_label": "Diabetes Health Score",
        "nut_title": "📊 Full Nutrient Composition (USDA Standard per 100g)",
        "ai_title": "💡 AI Virtual Expert Advice",
        "scientific_summary": "🔬 Scientific Summary",
        "dietary_guidance": "🌿 Dietary Guidance",
        "admin_title": "🛠️ Content Management (Admin)",
        "publish_btn": "Publish Article",
        "read_more": "Read Details",
        "discussion": "💬 Discussion",
        "comment_btn": "Post Comment",
        "name_label": "Your Name",
        "msg_label": "Add to discussion",
        "source": "© Data source: USDA's Food Composition",
        "register": "Research Account Registration",
        "auth_header": "🔑 Account",
        "login_tab": "Login",
        "register_tab": "Register",
        "email_label": "Email",
        "password_label": "Password",
        "login_confirm": "Confirm Login",
        "logout_btn": "Logout",
        "no_account": "Don't have an account?",
        "create_account": "Create new account",
        "tab4": "📸 Food Check"
    }
}

# --- 3. CUSTOM CSS ---
st.markdown("""
<style>
    /* Professional Polish Theme & Elderly-friendly sizing */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .main {
        background-color: #f8fafc;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-size: 1.15rem !important;
    }
    
    h1 {
        font-weight: 800 !important;
        color: #1e293b !important;
        letter-spacing: -0.025em !important;
    }
    
    h2, h3 {
        font-weight: 700 !important;
        color: #334155 !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
        font-size: 1.2rem !important;
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 12px !important;
    }
    
    .stButton button {
        height: 3.5rem !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    .nutrient-card { 
        background-color: #ffffff; 
        border-radius: 12px; 
        padding: 20px; 
        border: 1px solid #e2e8f0; 
        text-align: center; 
        margin-bottom: 12px; 
        min-height: 110px;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
    }
    
    .nutrient-value { 
        font-size: 24px; 
        font-weight: 800; 
        color: #059669; 
    }
    
    .nutrient-name { 
        font-size: 14px; 
        color: #64748b; 
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .score-container { 
        padding: 30px; 
        border-radius: 20px; 
        text-align: center; 
        margin-bottom: 30px; 
        border: 1px solid rgba(255,255,255,0.2); 
        color: white; 
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    .ai-box { 
        background-color: #eff6ff; 
        padding: 25px; 
        border-radius: 16px; 
        border-left: 8px solid #3b82f6; 
        color: #1e40af; 
        line-height: 1.8; 
        font-size: 1.25rem !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .article-card { 
        border: 1px solid #e2e8f0; 
        padding: 20px; 
        border-radius: 16px; 
        background: white; 
        transition: transform 0.3s;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Highlight for accessibility */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 12px 12px 0 0;
        padding: 12px 24px;
        font-weight: 800;
        color: #64748b;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* Custom Sidebar Header */
    section[data-testid="stSidebar"] .stMarkdown h1 {
        font-size: 1.5rem !important;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. DATABASE & SESSION STATE ---
def get_db():
    try:
        MONGO_URI = st.secrets["MONGO_URI"]
        client = MongoClient(MONGO_URI)
        return client["USDA_Healthy_Food"]
    except:
        st.error("Lỗi kết nối Cơ sở dữ liệu. Vui lòng kiểm tra cấu hình MONGO_URI.")
        return None

db_connection = get_db()
articles_col = db_connection['food_articles'] if db_connection is not None else None

if 'lang' not in st.session_state: st.session_state.lang = "Tiếng Việt"
L = LANGUAGES[st.session_state.lang]

def display_sidebar_auth():
    with st.sidebar:
        st.write("🌐 **Language / Ngôn ngữ**")
        c_us, c_vn = st.columns(2)
        if c_us.button("🇺🇸 English"): st.session_state.lang = "English"; st.rerun()
        if c_vn.button("🇻🇳 Tiếng Việt"): st.session_state.lang = "Tiếng Việt"; st.rerun()

        st.divider()
        L = LANGUAGES.get(st.session_state.get('lang', 'English'), LANGUAGES['English'])
        st.title(f"{L['title']}")
        st.markdown(f"*{L['source']}*")
        st.write(" ")

        if 'user_email' in st.session_state and st.session_state.user_email:
            st.success(f"👤 {st.session_state.user_email}")
            if st.button(L["logout_btn"]):
                for key in ["user_email", "step"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        else:
            st.subheader(L["auth_header"])
            tab1, tab2 = st.tabs([L["login_tab"], L["register_tab"]])

            with tab1:
                email = st.text_input(L["email_label"], key="login_email", placeholder="abc@email.com")
                password = st.text_input(L["password_label"], type="password", key="login_pass")

                if st.button(L["login_confirm"], use_container_width=True):
                    if email and password:
                        send_to_webhook({"action": "LOGIN", "email": email})
                        st.session_state.user_email = email
                        st.success("Signed in!" if st.session_state.lang == "English" else "Đã đăng nhập!")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập đủ thông tin." if st.session_state.lang == "Tiếng Việt" else "Please fill in all fields.")

            with tab2:
                st.write(L["no_account"])
                if st.button(L["create_account"], use_container_width=True):
                    st.session_state.step = "DANG_KY_FORM"
                    st.rerun()

        st.divider()
        st.caption("© 2026 Healthy Food")

# --- 5. LOGIC THUẬT TOÁN ---
def is_spam(text):
    bad_words = ['http', 'https', 'www', 'buy now', 'cờ bạc', 'quảng cáo']
    return any(word in text.lower() for word in bad_words) or len(text) < 3

@st.cache_data
def get_raw_nutrients(fdc_id):
    if db_connection is None: return pd.DataFrame()
    pipeline = [{"$match": {"fdc_id": int(fdc_id)}}, {
        "$lookup": {"from": "Nutrient_Definitions", "localField": "nutrient_id", "foreignField": "id",
                    "as": "details"}}, {"$unwind": "$details"}]
    results = list(db_connection.Core_Nutrients.aggregate(pipeline))
    return pd.DataFrame(
        [{"Nutrient": r['details']['name'], "Amount": r['amount'], "Unit": r['details']['unit_name']} for r in results])

# --- 7. MÀN HÌNH ĐĂNG KÝ CHI TIẾT ---
step = st.session_state.get('step', 'HOME')

if step == "DANG_KY_FORM":
    display_sidebar_auth()
    st.header("📝 " + L["register"])
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        fn = c1.text_input("Họ và Tên*" if st.session_state.lang == "Tiếng Việt" else "Full Name*")
        em = c1.text_input("Email*")
        un = c2.text_input("Viện/Trường*" if st.session_state.lang == "Tiếng Việt" else "Institution*")
        pw = st.text_input("Mật khẩu*" if st.session_state.lang == "Tiếng Việt" else "Password*", type="password")
        bio = st.text_area("Hướng nghiên cứu" if st.session_state.lang == "Tiếng Việt" else "Research Focus")
        if st.form_submit_button("✅ Hoàn tất" if st.session_state.lang == "Tiếng Việt" else "Complete"):
            if fn and em and pw:
                send_to_webhook({"action": "REGISTER", "full_name": fn, "email": em, "uni": un, "bio": bio})
                st.session_state.user_email = em
                st.session_state.step = "HOME"
                st.rerun()
            else:
                st.error("Vui lòng điền các trường bắt buộc.")
    if st.button("⬅️ Quay lại" if st.session_state.lang == "Tiếng Việt" else "Back"): st.session_state.step = "HOME"; st.rerun()

elif step == "HOME":
    display_sidebar_auth()
    st.title(L["title"])

    # ĐỔI THỨ TỰ TABS: tab4 (Food Check) lên đầu
    tab_foodcheck, tab_explorer, tab_recommend, tab_about = st.tabs([L["tab4"], L["tab1"], L["tab2"], L["tab3"]])

    # --- TAB 1: FOOD CHECK (Tích hợp DiaCam) ---
    with tab_foodcheck:
        DiaCam.run_diacam_lab()

    # --- TAB 2: EXPLORER (USDA Food Intelligence) ---
    with tab_explorer:
        st.markdown(f"### {L['tab1']}")
        
        # Gợi ý tìm kiếm nhanh cho người cao tuổi
        st.write("💡 " + ("Quick suggestions:" if st.session_state.lang == "English" else "Gợi ý nhanh:"))
        suggestions = ["Yến mạch", "Cá hồi", "Bông cải xanh", "Táo", "Quả óc chó"] if st.session_state.lang == "Tiếng Việt" else ["Oats", "Salmon", "Broccoli", "Apple", "Walnuts"]
        cols_sug = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            if cols_sug[i].button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.usda_search = sug
                st.rerun()

        search_input = st.text_input(L["search_label"], key="usda_search")
        
        if 'page' not in st.session_state: st.session_state.page = 1
        skip = (st.session_state.page - 1) * 10

        if db_connection is not None:
            # Tải từ điển CSV để hỗ trợ tìm kiếm gần đúng
            df_dict = None
            try:
                df_dict = pd.read_csv("usda_food_dictionary_cleaned.csv")
            except:
                pass

            client_groq = None
            if "Groq_API_KEY" in st.secrets:
                from groq import Groq
                client_groq = Groq(api_key=st.secrets["Groq_API_KEY"])

            search_keywords = [search_input]
            english_query = search_input
            
            if search_input and client_groq:
                # Dịch từ khóa nếu là tiếng Việt
                with st.spinner("🔍 Translating..." if st.session_state.lang == "English" else "🔍 Đang dịch từ khóa..."):
                    english_query = DiaCam.translate_query(client_groq, search_input)
                    if english_query != search_input:
                        st.info(f"🔎 {'Searching for' if st.session_state.lang == 'English' else 'Đang tìm kiếm'}: **{english_query}**")
                        search_keywords.append(english_query)

            if english_query and df_dict is not None:
                fuzzy_matches = DiaCam.fuzzy_food_search(df_dict, english_query)
                if fuzzy_matches:
                    search_keywords.extend(fuzzy_matches)
            
            if search_input:
                # Loại bỏ các từ khóa trùng lặp
                search_keywords = list(set([k for k in search_keywords if k]))
                pattern = "|".join([re.escape(k) for k in search_keywords])
                query = {"description": {"$regex": pattern, "$options": "i"}}
            else:
                query = {}
                
            scored_data = list(db_connection.Scored_Foods.find(query).sort("score", -1).skip(skip).limit(10))

            if scored_data:
                df_view = pd.DataFrame(scored_data)[["icon", "description", "score", "status"]]
                event = st.dataframe(df_view, use_container_width=True, on_select="rerun", selection_mode="single-row",
                                     hide_index=True)

                st.markdown(
                    f"<div style='color:gray; font-size: 0.9rem; margin-top: -15px; margin-bottom: 15px;'>{L['source']}</div>",
                    unsafe_allow_html=True)

                cp1, cp2, cp3 = st.columns([1, 2, 1])
                if cp1.button(L["prev"]): st.session_state.page = max(1, st.session_state.page - 1)
                if cp3.button(L["next"]): st.session_state.page += 1

                if len(event.selection.rows) > 0:
                    selected_food = scored_data[event.selection.rows[0]]
                    color_map = {1: "#1b5e20", 2: "#2e7d32", 3: "#f9a825", 4: "#ef6c00", 5: "#c62828", 6: "#8e0000"}
                    bg_color = color_map.get(selected_food['rank'], "#757575")

                    st.markdown(f'<div class="score-container" style="background-color: {bg_color};">'
                                f'<h1 style="font-size: 70px; margin:0;">{selected_food["icon"]}</h1>'
                                f'<h2>{selected_food["description"]}</h2>'
                                f'<h3>{selected_food["status"]}</h3>'
                                f'<h3>{L["score_label"]}: {selected_food["score"]}/100</h3></div>', unsafe_allow_html=True)

                    nut_df = get_raw_nutrients(selected_food['fdc_id'])
                    st.subheader(L["nut_title"])
                    n_cols = st.columns(5)
                    for idx, row in nut_df.iterrows():
                        with n_cols[idx % 5]:
                            st.markdown(f'<div class="nutrient-card"><div class="nutrient-name">{row["Nutrient"]}</div>'
                                        f'<div class="nutrient-value">{round(row["Amount"], 2)} <small>{row["Unit"]}</small></div></div>',
                                        unsafe_allow_html=True)

                    advices = {
                        1: "Excellent choice!" if st.session_state.lang == "English" else "Lựa chọn tuyệt vời!",
                        2: "Safe for consumption." if st.session_state.lang == "English" else "An toàn sử dụng.",
                        3: "In moderation." if st.session_state.lang == "English" else "Dùng điều độ.",
                        4: "Caution." if st.session_state.lang == "English" else "Thận trọng.",
                        5: "Not recommended." if st.session_state.lang == "English" else "Không khuyến khích.",
                        6: "Danger Zone!" if st.session_state.lang == "English" else "Vùng nguy hiểm!"
                    }

                    st.markdown(f'<div class="ai-box"><b>{L["scientific_summary"]}:</b> {selected_food["status"]}.<br>'
                                f'<b>{L["dietary_guidance"]}:</b> {advices.get(selected_food["rank"])}</div>',
                                unsafe_allow_html=True)

                    col_chart, col_recipe = st.columns([2, 1])
                    with col_chart:
                        fig = px.bar(nut_df.sort_values('Amount', ascending=False).head(15), x='Amount', y='Nutrient',
                                     orientation='h', color='Amount')
                        st.plotly_chart(fig, use_container_width=True)
                    with col_recipe:
                        rs.show_recipe_section(selected_food['description'])

    # --- TAB 3: ELITE FOODS LAB ---
    with tab_recommend:
        if articles_col is not None:
            with st.expander(L["admin_title"]):
                with st.form("admin_form"):
                    t = st.text_input("Title")
                    c = st.selectbox("Category", ["Beans", "Nuts", "Seeds", "Greens"])
                    img = st.text_input("Image URL")
                    content = st.text_area("Content")
                    if st.form_submit_button(L["publish_btn"]):
                        articles_col.insert_one(
                            {"title": t, "category": c, "image": img, "content": content, "date": datetime.now(),
                             "comments": []})
                        st.rerun()

            articles = list(articles_col.find().sort("date", -1))
            grid = st.columns(3)
            for idx, art in enumerate(articles):
                with grid[idx % 3]:
                    st.image(art.get('image') or "https://via.placeholder.com/300", use_container_width=True)
                    st.subheader(art['title'])
                    if st.button(L["read_more"], key=f"art_{art['_id']}"):
                        st.session_state.selected_article_id = art['_id']

            if 'selected_article_id' in st.session_state:
                det = articles_col.find_one({"_id": st.session_state.selected_article_id})
                if det:
                    st.markdown("---")
                    st.header(det['title'])
                    st.write(det['content'])
                    st.subheader(L["discussion"])
                    for cmt in det.get('comments', []):
                        with st.chat_message("user"): st.write(f"**{cmt['user']}**: {cmt['text']}")
                    with st.form("cmt_form", clear_on_submit=True):
                        u = st.text_input(L["name_label"])
                        m = st.text_area(L["msg_label"])
                        if st.form_submit_button(L["comment_btn"]):
                            if not is_spam(m):
                                articles_col.update_one({"_id": det["_id"]}, {
                                    "$push": {"comments": {"user": u or "Anon", "text": m, "time": datetime.now()}}})
                                st.rerun()

    # --- TAB 4: ABOUT ---
    with tab_about:
        st.info("System optimized for Environmental Toxicology and Nutritional Research. Researcher: Thao Thanh Nguyen")
        
    # --- AI CHATBOT SECTION ---
    def handle_ai_chat():
        if "messages" not in st.session_state:
            st.session_state.messages = []

        st.divider()
        st.subheader("👨‍⚕️ " + ("Expert Diabetes Consultation" if st.session_state.lang == "English" else "Tư vấn Chuyên gia Tiểu đường"))
        st.caption("Powered by Llama 3.3 on Groq Infrastructure")

        col_doc, col_intro = st.columns([1, 4])
        with col_doc:
            st.image("https://cdn-icons-png.flaticon.com/512/387/387561.png", width=80)
        with col_intro:
            st.write(f"**{'Diabetes Specialist' if st.session_state.lang == 'English' else 'Chuyên gia Tiểu đường'}**")
            st.info("Nutrition & Glycemic Index Support Expert." if st.session_state.lang == "English" else "Chuyên gia hỗ trợ Dinh dưỡng & Chỉ số Đường huyết.")

        if st.session_state.messages:
            chat_container = st.container(height=400, border=True)
            with chat_container:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

        if user_query := st.chat_input("Enter your questions..." if st.session_state.lang == "English" else "Nhập câu hỏi của bạn..."):
            st.session_state.messages.append({"role": "user", "content": user_query})
            st.rerun() # Rerun to show the user message immediately

        # If last message is from user, generate AI response
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            with st.spinner("Đang kết nối với trí tuệ nhân tạo..." if st.session_state.lang == "Tiếng Việt" else "Connecting to AI..."):
                try:
                    if "Groq_API_KEY" not in st.secrets:
                        st.error("Lỗi: Không tìm thấy Groq_API_KEY trong file secrets.toml")
                        return

                    client_groq = Groq(api_key=st.secrets["Groq_API_KEY"])
                    
                    system_prompt = (
                        "You are an expert endocrinologist and nutritionist. "
                        "Provide scientific, evidence-based advice on diabetes and nutrition. "
                        f"Keep responses professional, concise, and in {st.session_state.lang}."
                    )

                    completion = client_groq.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": st.session_state.messages[-1]["content"]}
                        ],
                        temperature=0.5,
                        max_tokens=1024,
                    )

                    ai_response = completion.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    st.rerun()

                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg:
                        st.error("Lỗi xác thực: API Key của Groq không đúng hoặc đã bị thu hồi.")
                    elif "429" in error_msg:
                        st.error("Lỗi hạn mức: Bạn đã gửi quá nhiều yêu cầu trong thời gian ngắn.")
                    else:
                        st.error(f"Lỗi hệ thống: {error_msg}")

    handle_ai_chat()
