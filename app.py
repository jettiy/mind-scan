import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components 
from PIL import Image
import datetime
import time
import qrcode
import io
import base64
import json
from typing import Dict, List, Optional
import re

# ==========================================
# 설정 관리 클래스
# ==========================================
class MindScanConfig:
    def __init__(self):
        self.SERVICE_URL = "https://mind-scan.ai.kr"
        self.MODEL_PREFERENCES = [
            "gemini-2.5-flash", 
            "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-1.5-flash", 
            "gemini-1.5-pro"
        ]
        self.SAFETY_SETTINGS = [
            {"category": c, "threshold": "BLOCK_NONE"} 
            for c in [
                "HARM_CATEGORY_HARASSMENT", 
                "HARM_CATEGORY_HATE_SPEECH", 
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", 
                "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]
        ]
        
    def get_qr_code(self, url: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="white", back_color="transparent")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

# ==========================================
# AI 모델 관리자
# ==========================================
class AIModelManager:
    def __init__(self, config: MindScanConfig):
        self.config = config
        self.model = None
        self.model_name = None
        self._setup_model()
    
    @st.cache_resource
    def _setup_model(_self):
        try:
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            else:
                return None, "API 키 없음"
            
            available = []
            try:
                for m in genai.list_models():
                    if "generateContent" in getattr(m, "supported_generation_methods", []):
                        available.append(m.name.replace("models/", ""))
            except:
                available = _self.config.MODEL_PREFERENCES
            
            chosen = next(
                (t for t in _self.config.MODEL_PREFERENCES if t in available), 
                "gemini-1.5-flash"
            )
            
            model = genai.GenerativeModel(
                chosen, 
                safety_settings=_self.config.SAFETY_SETTINGS
            )
            return model, chosen
        except Exception as e:
            return None, str(e)
    
    def generate_response(self, prompt: str, image: Optional[Image.Image] = None, stream: bool = False):
        if not self.model:
            self.model, self.model_name = self._setup_model()
        
        if not self.model:
            raise Exception("AI 모델을 초기화할 수 없습니다.")
        
        content = [prompt]
        if image:
            content.append(image)
        
        if stream:
            return self.model.generate_content(content, stream=True)
        else:
            response = self.model.generate_content(content)
            return response.text

# ==========================================
# 분석 결과 구조화
# ==========================================
class AnalysisResult:
    def __init__(self):
        self.profile: Dict = {}
        self.scenarios: Dict[str, str] = {}
        self.general_analysis: str = "" # [NEW] 전체 상황 분석 추가
        self.selected_scenario: str = ""
        
    def parse_profile(self, raw_text: str) -> Dict:
        profile = {
            "temperament": "",
            "communication": "",
            "strategy": ""
        }
        lines = raw_text.split('\n')
        for line in lines:
            line = line.strip()
            if '기질' in line or '성격' in line:
                profile['temperament'] = line.split(':', 1)[-1].strip()
            elif '소통' in line or '대화' in line:
                profile['communication'] = line.split(':', 1)[-1].strip()
            elif '공략' in line or '팁' in line:
                profile['strategy'] = line.split(':', 1)[-1].strip()
        return profile

# ==========================================
# 세션 상태 관리자
# ==========================================
class SessionManager:
    def __init__(self):
        self._init_session()
    
    def _init_session(self):
        defaults = {
            'step': 1,
            'messages': [],
            'analysis_result': "",
            'context_image': None,
            'scenarios': {},
            'general_analysis': "", # [NEW]
            'selected_scenario': "",
            'target_relation': "",
            'target_name': "",
            'target_gender': "",
            'target_birth': None,
            'target_calendar': "",
            'context_text': "",
            'analysis_data': AnalysisResult()
        }
        
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default
    
    def reset(self):
        for key in st.session_state.keys():
            del st.session_state[key]
        self._init_session()

# --- Streamlit 페이지 설정 ---
st.set_page_config(
    page_title="마인드 스캔 (Mind Scan)",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 전역 설정 ---
config = MindScanConfig()
ai_manager = AIModelManager(config)
session_manager = SessionManager()

# ==========================================
# CSS 스타일링
# ==========================================
st.markdown(f"""
<style>
    /* 전체 배경 및 폰트 */
    .stApp {{ 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
        color: #333;
    }}
    
    /* 메인 컨테이너 */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 50px;
        max-width: 600px;
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        min-height: 95vh;
        margin: 0 auto;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.2);
    }}

    /* 헤더 숨기기 */
    header {{visibility: hidden;}}
    
    /* 말풍선 디자인 */
    .stChatMessage {{ padding: 10px 0; border: none; background: none; margin-bottom: 8px; }}
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) div[data-testid="stChatMessageContent"] {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 18px 18px 4px 18px; padding: 14px 18px; color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); font-weight: 500; line-height: 1.5;
    }}
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) div[data-testid="stChatMessageContent"] {{
        background-color: #F8F9FA; border-radius: 18px 18px 18px 4px; padding: 14px 18px; color: #333;
        border: 1px solid #E9ECEF; font-weight: 500; line-height: 1.5;
    }}

    /* 입력창 스타일 */
    .stChatInputContainer {{
        background-color: #FFFFFF; padding: 15px 0 5px 0; border-top: 1px solid #E9ECEF;
    }}
    
    /* 버튼 스타일 */
    .stButton > button {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;
        border-radius: 12px; padding: 12px 24px; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease; width: 100%;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); color: white;
    }}

    /* 공유 카드 디자인 */
    .share-card {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 30px 20px; border-radius: 20px; text-align: center;
        margin: 30px 0; box-shadow: 0 15px 35px rgba(102, 126, 234, 0.3); position: relative; overflow: hidden;
    }}
    .share-card .highlight {{
        background-color: rgba(255,255,255,0.2); backdrop-filter: blur(10px);
        padding: 20px; border-radius: 15px; margin: 20px 0; font-weight: 600; font-size: 1rem; line-height: 1.6;
    }}
    .qr-img {{ width: 100px; height: 100px; margin-top: 15px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.2); }}
    
    /* [수정] 시나리오 박스 (가로 배치용) */
    .scenario-box {{
        background: white;
        border: 1px solid #E9ECEF;
        border-radius: 15px;
        padding: 20px; 
        margin-bottom: 10px; 
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        color: #333;
        min-height: 250px; /* 높이 맞춰줌 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .scenario-box:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.15);
        border-color: #667eea;
    }}
    .scenario-title {{
        font-weight: 800; font-size: 1.1rem; color: #667eea; margin-bottom: 10px;
    }}
    .scenario-desc {{
        font-size: 0.95rem; color: #555; line-height: 1.6; flex-grow: 1;
    }}
    
    /* 타이틀 스타일 */
    .main-title {{
        text-align: center; color: #333; font-size: 2.5rem; font-weight: 800; margin-bottom: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }}
    .subtitle {{
        text-align: center; color: #666; font-size: 1rem; margin-bottom: 30px; font-weight: 500;
    }}
    
    /* 진행 바 */
    .progress-container {{ background-color: #E9ECEF; border-radius: 10px; height: 8px; margin: 20px 0; overflow: hidden; }}
    .progress-bar {{ background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); height: 100%; border-radius: 10px; transition: width 0.5s ease; }}
</style>
""", unsafe_allow_html=True)

# --- 헤더 및 진행 바 ---
st.markdown('<h1 class="main-title">🧠 마인드 스캔</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI Relationship Analysis Lab</p>', unsafe_allow_html=True)

progress_map = {1: 25, 2: 50, 3: 75, 3.5: 85, 4: 100}
current_progress = progress_map.get(st.session_state.step, 0)
st.markdown(f'''
<div class="progress-container"><div class="progress-bar" style="width: {current_progress}%"></div></div>
<div style="text-align: center; color: #666; font-size: 0.9rem; margin-bottom: 30px;">Step {st.session_state.step} / 4</div>
''', unsafe_allow_html=True)

# ==========================================
# [1단계] 정보 입력
# ==========================================
if st.session_state.step == 1:
    st.markdown('<h2 style="color: #333; margin-bottom: 30px;">Step 1. 분석 대상 설정</h2>', unsafe_allow_html=True)
    
    with st.form("info_form"):
        relation = st.selectbox("관계 유형", ["연인/썸", "친구", "직장동료/상사", "가족", "기타"])
        name = st.text_input("이름 (호칭)", placeholder="예: 김팀장, 썸녀")
        gender = st.selectbox("성별", ["남성", "여성"])
        col1, col2 = st.columns([2, 1])
        with col1:
            birth = st.date_input("생년월일", value=datetime.date(2000, 1, 1), min_value=datetime.date(1950, 1, 1), max_value=datetime.date(2015, 12, 31))
        with col2:
            calendar_type = st.radio("달력", ["양력", "음력"], horizontal=True)
        
        if st.form_submit_button("🚀 프로필 분석 시작"):
            if not name.strip():
                st.error("이름을 입력해주세요.")
            else:
                st.session_state.target_relation = relation
                st.session_state.target_name = name
                st.session_state.target_gender = gender
                st.session_state.target_birth = birth
                st.session_state.target_calendar = calendar_type
                st.session_state.step = 2
                st.rerun()

# ==========================================
# [2단계] 성향 분석 (사주 엔진 -> 심리학 번역)
# ==========================================
elif st.session_state.step == 2:
    name = st.session_state.target_name
    st.markdown(f'<h2 style="color: #333; margin-bottom: 30px;">Step 2. {name}님 성향 리포트</h2>', unsafe_allow_html=True)

    # [광고 A]
    st.caption("AI가 데이터를 심층 분석 중입니다...")
    components.html("""
       <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXX"
     crossorigin="anonymous"></script>
    <ins class="adsbygoogle"
         style="display:inline-block;width:300px;height:250px"
         data-ad-client="ca-pub-XXXXXXXXXXXXXX"
         data-ad-slot="YYYYYYYYYY"></ins>
    <script>
         (adsbygoogle = window.adsbygoogle || []).push({});
    </script>
    """, height=260)

    if not st.session_state.analysis_result:
        with st.spinner("🔄 사주/점성술 데이터를 현대 심리학으로 해석 중..."):
            try:
                # [핵심] 사주 엔진 -> 심리학 표현 프롬프트
                prompt = f"""
                당신은 사주명리학과 점성술에 정통한 고수이자, 이를 현대 심리학 용어로 완벽하게 번역하는 프로파일러입니다.
                
                [대상] {name}({st.session_state.target_gender}), {st.session_state.target_birth}({st.session_state.target_calendar})
                [관계] {st.session_state.target_relation}
                
                [분석 미션]
                1. (Internal): 사주(오행, 십성, 격국)와 점성술(별자리, 행성 배치)을 정밀하게 분석하세요.
                2. (Output): **절대 사주 용어(갑목, 역마살 등)를 쓰지 마세요.** 대신 일반인이 이해하기 쉬운 **성격 키워드, 행동 패턴, 심리적 기제**로 표현하세요.
                3. 말투는 전문적이지만 따뜻하고 이해하기 쉽게 작성하세요.
                
                [출력 형식 (반드시 지킬 것)]
                **타고난 기질**: [핵심 성격을 한 문장으로 명쾌하게]
                **소통 스타일**: [대화 방식과 선호하는 소통법을 한 문장으로]
                **공략 포인트**: [관계를 좋게 만드는 결정적 팁 한 문장으로]
                """
                response = ai_manager.generate_response(prompt)
                st.session_state.analysis_result = response
                st.session_state.analysis_data.profile = st.session_state.analysis_data.parse_profile(response)
            except Exception as e:
                st.error(f"❌ 분석 실패: {str(e)}")

    if st.session_state.analysis_result:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.analysis_result)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👉 다음 단계 (상황 입력)"): st.session_state.step = 3; st.rerun()
        with col2:
            if st.button("🔄 처음으로"): session_manager.reset(); st.rerun()

# ==========================================
# [3단계] 상황 공유
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<h2 style="color: #333; margin-bottom: 30px;">Step 3. 상황 데이터 입력</h2>', unsafe_allow_html=True)
    st.info("💡 대화 캡처나 구체적인 상황을 입력하면 AI가 숨겨진 의도를 파악합니다.")
    
    uploaded_file = st.file_uploader("대화 캡처 이미지 (선택)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.session_state.context_image = Image.open(uploaded_file)
        st.image(st.session_state.context_image, caption="이미지 로드됨", use_container_width=True)

    context_text = st.text_area("상황 설명", placeholder="예: 썸남이 읽씹했는데, 내가 실수한 걸까?", height=150)
    
    if st.button("🩺 AI 진단 시작"):
        if not context_text.strip():
            st.error("상황 설명을 입력해주세요.")
        else:
            st.session_state.context_text = context_text
            st.session_state.scenarios = {}
            st.session_state.step = 3.5
            st.rerun()

# ==========================================
# [3.5단계] 상황 정밀 진단 (레이아웃 개선)
# ==========================================
elif st.session_state.step == 3.5:
    st.markdown('<h2 style="color: #333; margin-bottom: 30px;">🕵️‍♂️ 상황 진단 리포트</h2>', unsafe_allow_html=True)

    if not st.session_state.scenarios:
        # [광고 B]
        components.html("""
            <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXX"
     crossorigin="anonymous"></script>
    <ins class="adsbygoogle"
         style="display:inline-block;width:300px;height:250px"
         data-ad-client="ca-pub-XXXXXXXXXXXXXX"
         data-ad-slot="YYYYYYYYYY"></ins>
    <script>
         (adsbygoogle = window.adsbygoogle || []).push({});
    </script>
        """, height=110)
        
        with st.spinner("🔄 AI가 상황을 분석하여 가능성을 도출 중입니다..."):
            try:
                # [수정] 통합 분석 + 2가지 시나리오 프롬프트
                prompt = f"""
                당신은 관계 분석 전문가입니다. 
                
                [정보]
                - 프로필: {st.session_state.analysis_result}
                - 상황: {st.session_state.context_text}
                
                [미션]
                1. 먼저 이 상황에 대한 **[종합 분석]**을 3~4문장으로 서술하세요. (객관적 상황 판단)
                2. 그 후, 가장 유력한 **2가지 가능성(시나리오)**를 제시하세요.
                
                [출력 형식 (형식을 엄격히 지켜주세요)]
                [종합 분석]
                (여기에 전체적인 상황 분석 내용을 적어주세요.)
                
                ##A##
                [시나리오 A 제목]
                (심리적/내면적 원인 중심의 설명. 3문장 이내)
                
                ##B##
                [시나리오 B 제목]
                (현실적/상황적 원인 중심의 설명. 3문장 이내)
                """
                
                response = ai_manager.generate_response(prompt, st.session_state.context_image)
                
                # 파싱 로직
                if "##A##" in response and "##B##" in response:
                    # 종합 분석 추출
                    parts_gen = response.split("##A##")
                    general_analysis = parts_gen[0].replace("[종합 분석]", "").strip()
                    
                    # 시나리오 추출
                    parts_scen = parts_gen[1].split("##B##")
                    scenario_a = parts_scen[0].strip()
                    scenario_b = parts_scen[1].strip()
                    
                    st.session_state.general_analysis = general_analysis
                    st.session_state.scenarios = {"A": scenario_a, "B": scenario_b}
                else:
                    st.session_state.general_analysis = "분석 결과"
                    st.session_state.scenarios = {"A": response, "B": "추가 분석 불가"}
                    
            except Exception as e:
                st.error(f"❌ 분석 실패: {str(e)}")

    # 결과 표시 화면
    if st.session_state.scenarios:
        # 1. 종합 분석 (상단)
        st.info(f"📋 **AI 종합 분석**\n\n{st.session_state.general_analysis}")
        
        st.write("---")
        st.markdown("<h4 style='text-align:center;'>가장 유력한 상황을 선택해주세요</h4>", unsafe_allow_html=True)
        
        # 2. 시나리오 A / B (가로 배치)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="scenario-box">
                <div class="scenario-title">🅰️ 가능성 1</div>
                <div class="scenario-desc">{st.session_state.scenarios.get("A", "")}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("이게 맞는 듯 (A)", key="btn_a", use_container_width=True):
                st.session_state.selected_scenario = st.session_state.scenarios.get('A', '')
                st.session_state.messages = []
                st.session_state.step = 4
                st.rerun()
        
        with col2:
            st.markdown(f"""
            <div class="scenario-box">
                <div class="scenario-title">🅱️ 가능성 2</div>
                <div class="scenario-desc">{st.session_state.scenarios.get("B", "")}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("이게 맞는 듯 (B)", key="btn_b", use_container_width=True):
                st.session_state.selected_scenario = st.session_state.scenarios.get('B', '')
                st.session_state.messages = []
                st.session_state.step = 4
                st.rerun()
    
    st.write("<br>", unsafe_allow_html=True)
    if st.button("⬅️ 상황 다시 설명하기"): st.session_state.step = 3; st.rerun()

# ==========================================
# [4단계] 실전 대화 (확률 기반 반응)
# ==========================================
elif st.session_state.step == 4:
    name = st.session_state.target_name
    st.markdown(f'<h2 style="color: #333; margin-bottom: 30px;">💬 {name}님과의 시뮬레이션</h2>', unsafe_allow_html=True)
    
    with st.expander("🎯 선택된 상황 보기"):
        st.info(st.session_state.selected_scenario)
    
    for msg in st.session_state.messages:
        avatar = "🔮" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("메시지를 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.write(prompt)
        
        with st.chat_message("assistant", avatar="🔮"):
            container = st.empty()
            full_response = ""
            try:
                history_text = ""
                for m in st.session_state.messages:
                    role = "나" if m['role'] == 'user' else name
                    history_text += f"{role}: {m['content']}\n"
                
                prompt_content = f"""
                너는 '{name}'으로 대화하는 AI입니다. 
                [정보] 성격:{st.session_state.analysis_result}, 상황:{st.session_state.selected_scenario}
                [사용자 메시지] "{prompt}"
                
                [미션]
                1. 위 정보를 바탕으로 '{name}'이 보일 반응을 1순위/2순위로 예측하세요.
                2. 각 반응의 확률(%)을 추정하세요.
                
                [출력]
                ### 🎲 예상 반응
                * **1순위 (00%)**: "(대사)" - (지문)
                * **2순위 (00%)**: "(대사)" - (지문)
                
                ### 🧠 속마음
                (2줄 요약)
                
                ### 💡 공략 팁
                (1줄 조언)
                
                ### ⚠️ 주의사항
                (1줄 경고)
                """
                
                response_stream = ai_manager.generate_response(prompt_content, st.session_state.context_image, stream=True)
                for chunk in response_stream:
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        container.markdown(full_response + "▌")
                container.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e: st.error(f"❌ 오류: {str(e)}")
    
    # 공유 카드
    if len(st.session_state.messages) > 1:
        qr_image = config.get_qr_code(config.SERVICE_URL)
        st.markdown(f"""
        <div class="share-card">
            <h3>🧠 MIND SCAN</h3>
            <div class="highlight">"{name}님의 속마음은...<br>{st.session_state.analysis_result.split('**타고난 기질**:')[1].split('**')[0].strip() if '**타고난 기질**:' in st.session_state.analysis_result else '...'}"</div>
            <img src="{qr_image}" class="qr-img">
            <div class="share-footer">QR 스캔하고 직접 체험해보세요!</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅️ 상황 재설정"): st.session_state.step = 3; st.rerun()
    with col2: 
        if st.button("처음부터 다시하기"): session_manager.reset(); st.rerun()

# --- 푸터 ---
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.8rem; margin-top: 50px; padding-top: 30px; border-top: 1px solid #E9ECEF;">
    <p>© 2025 Mind Scan. AI Relationship Analysis Lab.</p>
</div>
""", unsafe_allow_html=True)
