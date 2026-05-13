import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from pymongo import MongoClient
import io
import time
import difflib

# --- CÁC HÀM XỬ LÝ LOGIC ---

def translate_query(query):
    """Dịch tên món ăn từ bất kỳ ngôn ngữ nào (chủ yếu tiếng Việt) sang tiếng Anh để tra cứu USDA dùng Gemini"""
    if not query:
        return query
    
    # Kiểm tra xem có chứa ký tự tiếng Việt không
    vi_chars = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    is_vietnamese = any(char in query.lower() for char in vi_chars)
    
    if not is_vietnamese:
        return query

    prompt = f"Translate this food name to a standard English food name/category for USDA database searching. Return ONLY the English name, nothing else: {query}"
    try:
        model = genai.GenerativeModel(get_available_gemini_model())
        response = model.generate_content(prompt)
        translated = response.text.strip().lower()
        return translated.replace(".", "")
    except:
        return query

def get_available_gemini_model():
    """Lấy tên model Gemini ổn định"""
    return "gemini-2.0-flash"

def fuzzy_food_search(df, keyword):
    """Tìm kiếm gần đúng trong dataframe"""
    if df is None or df.empty or not keyword:
        return []
    food_list = df['food_name'].tolist()
    # Tăng độ nhạy cho tìm kiếm gần đúng
    matches = difflib.get_close_matches(keyword, food_list, n=5, cutoff=0.4)
    return matches

def lookup_and_calculate(db, keyword, df_dict=None):
    """Tìm kiếm trực tiếp trên Scored_Foods và Join với Core_Nutrients"""
    search_keywords = [keyword]
    if df_dict is not None:
        fuzzy_matches = fuzzy_food_search(df_dict, keyword)
        if fuzzy_matches:
            search_keywords.extend(fuzzy_matches)
    
    # Tạo query tìm kiếm linh hoạt hơn
    search_patterns = [kw.strip() for kw in search_keywords if kw.strip()]
    if not search_patterns:
        return None

    query = {"$or": [{"description": {"$regex": pat, "$options": "i"}} for pat in search_patterns]}
    scored_items = list(db.Scored_Foods.find(query).limit(30))

    if not scored_items:
        return None

    cal_list = []
    gl_list = []

    for item in scored_items:
        fid = item.get('fdc_id')
        carb = item.get('Carbohydrate, by difference', 0)
        
        # Thử lấy Energy (Calorie) từ nhiều nguồn/ID khác nhau nếu có
        # 1008 is Energy in kcal
        energy_data = db.Core_Nutrients.find_one({
            "fdc_id": int(fid),
            "nutrient_id": 1008
        })

        cal = energy_data.get('amount', 0) if energy_data else 0

        try:
            v_cal = float(cal)
            v_carb = float(carb)
            # GL = (GI * Carb) / 100. Giả định GI trung bình là 55 nếu không có dữ liệu
            v_gl = (v_carb * 55) / 100

            if v_cal > 0 or v_carb > 0:
                cal_list.append(v_cal)
                gl_list.append(v_gl)
        except:
            continue

    if not cal_list and not gl_list:
        return None

    return {
        "keyword": keyword,
        "count": len(cal_list),
        "min_cal": min(cal_list) if cal_list else 0,
        "max_cal": max(cal_list) if cal_list else 0,
        "avg_cal": sum(cal_list) / len(cal_list) if cal_list else 0,
        "avg_gl": sum(gl_list) / len(gl_list) if gl_list else 0
    }

def analyze_with_gemini(ai_analysis, summary_data):
    lang = st.session_state.get('lang', 'English')
    
    prompt = f"""
    Bạn là chuyên gia dinh dưỡng cao cấp chuyên về tiểu đường. Hãy phân tích báo cáo sau:
    1. Nhận diện hình ảnh: {ai_analysis}
    2. Thống kê từ Database USDA: 
    {summary_data}

    Yêu cầu trả về chính xác cấu trúc sau bằng ngôn ngữ {lang}:
    **Tên món**: [Tên món ăn nhận diện được từ ảnh, dịch sang {lang} nếu cần]
    **Ước tính Calo**: [Tổng calo ước tính cho cả đĩa/phần ăn trong ảnh]
    **Lời khuyên**: [Nên ăn / Hạn chế / KHÔNG NÊN ĂN] - [Giải thích chuyên sâu nhưng ngắn gọn lý do dựa trên Calo, Carb và Chỉ số Glycemic Load GL để bảo vệ sức khỏe người tiểu đường. Đề xuất thêm rau xanh hoặc cách ăn giảm đường huyết].
    """

    try:
        model = genai.GenerativeModel(get_available_gemini_model())
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi phân tích từ AI: {e}"

# --- HÀM CHÍNH ---

def run_diacam_lab():
    lang = st.session_state.get('lang', 'English')
    
    # Giao diện header
    st.markdown(f"""
        <div style="background-color:#eff6ff; padding:20px; border-radius:15px; border-left:10px solid #3b82f6; margin-bottom:20px;">
            <h2 style="margin:0; color:#1e40af;">📸 { "AI Food Scanner" if lang == "English" else "Máy quét Thực phẩm AI" }</h2>
            <p style="margin:0; color:#1e40af; opacity:0.8;">{ "Advanced Diabetic Glycemic Analysis" if lang == "English" else "Phân tích Chỉ số Đường huyết Chuyên sâu" }</p>
        </div>
    """, unsafe_allow_html=True)

    df_dict = None
    try:
        df_dict = pd.read_csv("usda_food_dictionary_cleaned.csv")
    except:
        pass

    # 1. Cấu hình
    try:
        gemini_key = st.secrets.get("GEMINI_API_KEY")
        mongo_uri = st.secrets.get("MONGO_URI")

        if not gemini_key:
            st.error("Missing GEMINI_API_KEY")
            return
        
        genai.configure(api_key=gemini_key)
        
        if not mongo_uri:
            st.error("Missing MONGO_URI")
            return
            
        @st.cache_resource
        def get_diacam_db(uri):
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            return client["USDA_Healthy_Food"]
            
        db = get_diacam_db(mongo_uri)
    except Exception as e:
        st.error(f"Lỗi khởi tạo hệ thống: {e}")
        return

    # 2. Upload
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        input_method = st.radio(
            "Method:" if lang == "English" else "Cách tải:", 
            ["📤 Upload" if lang == "English" else "📤 Tải lên", "📸 Camera" if lang == "English" else "📸 Chụp ảnh"], 
            horizontal=True
        )

        img_file = None
        if "Upload" in input_method or "Tải lên" in input_method:
            img_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
        else:
            img_file = st.camera_input("")

    if img_file:
        img = Image.open(img_file)
        with col_preview:
            st.image(img, use_container_width=True, caption= ("Your meal" if lang == "English" else "Món ăn của bạn"))

        if st.button("🚀 " + ("START ANALYSIS" if lang == "English" else "BẮT ĐẦU PHÂN TÍCH"), use_container_width=True):
            full_text = ""
            with st.spinner("🔍 " + ("Detecting ingredients..." if lang == "English" else "Đang nhận diện thành phần...")):
                gemini_prompt = """
                You are a nutrition expert. Analyze this image carefully:
                1. Identify the dish and its major ingredients.
                2. For EACH main ingredient, provide 1 concise English keyword for USDA searching.
                3. Describe the portion size.
                
                Return exactly this format:
                Analysis: [Brief description in Vietnamese]
                Keywords: [keyword1, keyword2, keyword3]
                """
                try:
                    # Thử danh sách các model khả dụng
                    models_to_try = [get_available_gemini_model(), "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash", "gemini-1.5-pro"]
                    success = False
                    for target_model in models_to_try:
                        try:
                            model = genai.GenerativeModel(target_model)
                            response = model.generate_content([gemini_prompt, img])
                            full_text = response.text
                            success = True
                            break
                        except Exception as inner_e:
                            # Log error to console for debugging
                            print(f"Skipping model {target_model}: {inner_e}")
                            if "404" not in str(inner_e) and "not found" not in str(inner_e).lower():
                                # Nếu lỗi khác 404 (ví dụ 429 quota), và không phải "not found", thử model tiếp theo hoặc dừng
                                # Ở AI Studio, 404 thường mang ý nghĩa model không khả dụng trong vùng hoặc đã bị đổi tên
                                continue
                            continue
                    
                    if not success:
                        st.error("❌ Không tìm thấy model Gemini khả dụng (404). Vui lòng kiểm tra lại cấu hình API.")
                        return
                except Exception as e:
                    st.error(f"Gemini Error: {e}")
                    return

            if full_text:
                keywords = []
                analysis_part = ""
                for line in full_text.split('\n'):
                    if "Keywords:" in line:
                        keywords = [k.strip().strip('[]') for k in line.replace("Keywords:", "").split(',')]
                    if "Analysis:" in line:
                        analysis_part = line.replace("Analysis:", "")

                with st.spinner("📊 " + ("Querying USDA Database..." if lang == "English" else "Đang truy vấn cơ sở dữ liệu USDA...")):
                    summary_for_groq = ""
                    
                    results_area = st.container()
                    with results_area:
                        st.markdown(f"**{'Detected Ingredients:' if lang == 'English' else 'Các thành phần nhận diện:'}**")
                        
                        found_any = False
                        for kw in keywords:
                            if not kw: continue
                            stats = lookup_and_calculate(db, kw, df_dict)
                            if stats:
                                found_any = True
                                info = f"- {kw}: {stats['avg_cal']:.1f} kcal; GL: {stats['avg_gl']:.1f}"
                                summary_for_groq += info + "\n"
                                
                                with st.expander(f"📍 {kw}"):
                                    c1, c2, c3 = st.columns(3)
                                    c1.metric("Avg Calories", f"{stats['avg_cal']:.1f}")
                                    c2.metric("Avg GL", f"{stats['avg_gl']:.1f}")
                                    c3.metric("Data Points", stats['count'])
                            else:
                                st.caption(f"No USDA data for: {kw}")

                if summary_for_groq:
                    with st.spinner("👨‍⚕️ " + ("Consulting Virtual Doctor..." if lang == "English" else "Đang tham vấn ý kiến chuyên gia...")):
                        final_report = analyze_with_gemini(analysis_part, summary_for_groq)
                        st.markdown("---")
                        st.markdown(f"""
                            <div class="ai-box">
                                {final_report.replace('**', '<b>').replace('\n', '<br>')}
                            </div>
                        """, unsafe_allow_html=True)
                elif found_any == False:
                    st.error("Could not find nutritional data for ingredients detected.")
