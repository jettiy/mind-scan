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
import traceback # 상세 에러 확인을 위한 모듈
import textwrap # 긴 텍스트 줄바꿈을 위해 추가
from PIL import Image, ImageDraw, ImageFont, ImageColor


# [추가] 공유 및 이미지 생성
class ShareManager:
    def __init__(self):
        pass

    # [코드 최상단 import 영역에 추가]
from PIL import Image, ImageDraw, ImageFont, ImageColor
import textwrap
import io
import re

# [기존 코드]
# if 'selected_scenario' not in st.session_state: st.session_state.selected_scenario = ""

# [▼ 아래 코드를 추가하세요]
if 'show_share' not in st.session_state: st.session_state.show_share = False

# ==========================================
# [보조 함수] 그라데이션 이미지 생성
# ==========================================
def create_gradient_image(width, height, start_color, end_color):
    """주어진 크기와 색상으로 그라데이션 이미지를 생성합니다."""
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    return Image.composite(top, base, mask)

# ==========================================
# [핵심 클래스] 공유 및 이미지 관리
# ==========================================
class ShareManager:
    def create_result_image(self, title, target_name, text_content):
        """결과 텍스트를 예쁜 그라데이션 카드 이미지로 변환합니다."""
        # 1. 디자인 및 크기 설정
        width, height = 900, 1400   # 고해상도 이미지 크기
        card_margin = 60            # 테두리 여백
        card_radius = 40            # 카드 모서리 둥글기
        content_margin = 50         # 카드 내부 텍스트 여백
        
        # 색상 팔레트 (앱 테마 통일)
        start_color = "#667eea"      # 연보라 (시작)
        end_color = "#764ba2"        # 진보라 (끝)
        card_bg_color = (255, 255, 255, 235) # 반투명 흰색 카드
        text_color_point = "#764ba2" # 포인트 컬러 (제목 등)
        text_color_main = "#333333"  # 본문 컬러
        text_color_sub = "#666666"   # 부가 정보 컬러
        line_color = "#eeeeee"       # 구분선

        # 2. 폰트 로드 (⚠️중요: 서버에 맞는 한글 폰트 경로 필수)
        # 예: "NanumGothicBold.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
        font_path_bold = "malgunbd.ttf" # 윈도우용 맑은 고딕 볼드 (임시)
        font_path_reg = "malgun.ttf"    # 윈도우용 맑은 고딕 일반 (임시)
        
        try:
            font_h1 = ImageFont.truetype(font_path_bold, 70) # 대제목
            font_h2 = ImageFont.truetype(font_path_bold, 45) # 중제목/섹션명
            font_body_b = ImageFont.truetype(font_path_bold, 32) # 본문 볼드
            font_body = ImageFont.truetype(font_path_reg, 32)    # 본문 일반
            font_footer = ImageFont.truetype(font_path_reg, 24)  # 푸터
        except Exception as e:
            print(f"폰트 로드 실패: {e}. 기본 폰트로 대체합니다.")
            # 폰트 파일이 없으면 기본 폰트 사용 (한글 깨질 수 있음)
            default_font = ImageFont.load_default()
            font_h1 = font_h2 = font_body_b = font_body = font_footer = default_font

        # 3. 배경 그리기 (그라데이션 + 반투명 카드)
        img = create_gradient_image(width, height, start_color, end_color)
        draw = ImageDraw.Draw(img, 'RGBA')
        
        card_box = [card_margin, card_margin, width - card_margin, height - card_margin]
        draw.rounded_rectangle(card_box, radius=card_radius, fill=card_bg_color)

        # 4. 텍스트 그리기 시작 위치
        start_x = card_margin + content_margin
        current_y = card_margin + content_margin + 20
        usable_width = width - (start_x * 2) # 텍스트가 들어갈 실제 너비

        # [상단 제목 및 정보]
        draw.text((start_x, current_y), "🧠 마인드스캔 분석 결과", font=font_h1, fill=text_color_point)
        current_y += 100
        draw.text((start_x, current_y), f"분석 대상: {target_name} 님", font=font_h2, fill=text_color_main)
        current_y += 70
        
        # 구분선
        draw.line([(start_x, current_y), (width - start_x, current_y)], fill=line_color, width=3)
        current_y += 50

        # 5. 본문 내용 파싱 및 그리기
        # 불필요한 HTML/마크다운 제거 및 줄바꿈 정리
        clean_text = re.sub(r'<[^>]+>', '', text_content) # HTML 태그 제거
        clean_text = clean_text.replace("**", "")        # 마크다운 별표 제거
        clean_text = clean_text.replace("&nbsp;", " ").strip()
        
        # 빈 줄을 기준으로 문단 나누기
        paragraphs = re.split(r'\n\s*\n', clean_text)
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph or paragraph == "---": continue # 빈 문단이나 구분선 건너뛰기

            # 섹션 제목 감지 (이모지로 시작하는 라인)
            is_section_title = any(paragraph.startswith(emoji) for emoji in ["👾", "⚔️", "🩸", "✨", "🗣️", "💘", "🎯", "🔮", "🎲"])
            
            if is_section_title:
                current_y += 40 # 섹션 앞 간격
                # 섹션 제목은 한 줄로 처리 및 강조
                draw.text((start_x, current_y), paragraph, font=font_h2, fill=text_color_point)
                current_y += 60 # 섹션 제목 후 간격
            else:
                # 일반 본문은 자동 줄바꿈 (textwrap) 적용
                # 한글 기준 약 38~40자가 적당 (폰트 크기에 따라 조절 필요)
                wrap_width = 38 
                wrapped_lines = textwrap.wrap(paragraph, width=wrap_width)
                
                for line in wrapped_lines:
                    # 프로필 항목(난이도, 강점 등)은 볼드체로 강조
                    if any(prefix in line for prefix in ["난이도:", "강점:", "약점:"]):
                         curr_font = font_body_b
                         curr_color = text_color_main
                    else:
                         curr_font = font_body
                         curr_color = text_color_main
                         
                    draw.text((start_x, current_y), line, font=curr_font, fill=curr_color)
                    current_y += 48 # 줄 간격 (폰트 크기의 약 1.5배)
                
                current_y += 30 # 문단 간격

        # [푸터]
        footer_text = "Mind Scan AI - https://mind-scan.ai.kr"
        footer_y = height - card_margin - content_margin # 바닥에서 위치 계산
        draw.text((start_x, footer_y), footer_text, font=font_footer, fill=text_color_sub)

        # 6. 결과 반환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return buffered.getvalue()

    

# [중요] PIL의 ImageDraw, ImageFont 사용을 위한 import 추가 (코드 최상단에 추가 필요)
from PIL import ImageDraw, ImageFont 

# 인스턴스 생성
share_manager = ShareManager()

# ==========================================
# [설정] 광고 ID
# ==========================================
ADSENSE_CLIENT_ID = "ca-pub-5407905053449158"
ADSENSE_SLOT_ID = "7042015443"

# ==========================================
# 설정 및 클래스
# ==========================================
st.set_page_config(
    page_title="마인드스캔 (Mind Scan)",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

if 'step' not in st.session_state: st.session_state.step = 0
if 'messages' not in st.session_state: st.session_state.messages = []
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = ""
if 'context_image' not in st.session_state: st.session_state.context_image = None
if 'scenarios' not in st.session_state: st.session_state.scenarios = {}
if 'general_analysis' not in st.session_state: st.session_state.general_analysis = ""
if 'selected_scenario' not in st.session_state: st.session_state.selected_scenario = ""

class MindScanConfig:
    def __init__(self):
        self.SERVICE_URL = "https://mind-scan.ai.kr"
        self.MODEL_PREFERENCES = ["gemini-2.0-flash"]
        self.SAFETY_SETTINGS = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
    def get_qr_code(self, url: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="white", back_color="transparent")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

class AIModelManager:
    def __init__(self, config: MindScanConfig):
        self.config = config
        self.model = None
        self._setup_model()
    
    @st.cache_resource
    def _setup_model(_self):
        try:
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                return genai.GenerativeModel("gemini-2.0-flash", safety_settings=_self.config.SAFETY_SETTINGS), "gemini-1.5-flash"
            return None, "No API Key"
        except Exception as e: return None, str(e)
    
    def generate_response(self, prompt: str, image: Optional[Image.Image] = None, stream: bool = False):
        if not self.model: self.model, _ = self._setup_model()
        content = [prompt]
        if image: content.append(image)
        return self.model.generate_content(content, stream=True) if stream else self.model.generate_content(content).text

class AnalysisResult:
    def __init__(self): self.profile = {}
    def parse_profile(self, raw_text: str) -> Dict: return {}

class SessionManager:
    def __init__(self): self._init_session()
    def _init_session(self):
        if 'analysis_data' not in st.session_state: st.session_state.analysis_data = AnalysisResult()
    def reset(self):
        for key in list(st.session_state.keys()): del st.session_state[key]
        self._init_session()
        st.session_state.step = 0

config = MindScanConfig()
ai_manager = AIModelManager(config)
session_manager = SessionManager()

# ==========================================
# [0단계] 랜딩 페이지
# ==========================================
if st.session_state.step == 0:
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: 'Noto Sans KR', sans-serif; }
            .block-container { max-width: 100% !important; padding: 0 !important; }
            header {visibility: hidden;}
            
            /* [수정 핵심] min-height를 100vh에서 80vh로 줄여서 버튼이 들어올 공간 확보 */
            .hero-section { 
                min-height: 80vh; 
                display: flex; 
                flex-direction: column; 
                justify-content: center; /* 내용을 아래쪽으로 정렬하여 버튼과 가깝게 */
                align-items: center; 
                text-align: center; 
                padding: 20px; 
                color: white; 
            }
            
            .hero-title { font-size: 3rem; font-weight: 900; margin-bottom: 10px; text-shadow: 0 4px 10px rgba(0,0,0,0.2); }
            
            /* 버튼 스타일 */
            div.stButton > button {
                background: white !important; color: #764ba2 !important; font-size: 1.2rem !important; font-weight: 700 !important;
                padding: 1rem 3rem !important; border-radius: 50px !important; border: none !important;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2) !important; transition: all 0.3s ease !important;
            }
            div.stButton > button:hover { transform: translateY(-5px) !important; background-color: #f8f9fa !important; }
        </style>
        
        <div class="hero-section">
            <div style="font-size: 4rem; margin-bottom: 10px;">🧠</div>
            <h1 class="hero-title">AI가 분석하는<br>관계의 속마음</h1>
            <p style="font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px;">
                심리학 데이터를 기반으로 한 AI 기술로<br>상대방의 진짜 마음을 읽어보세요
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    _, col, _ = st.columns([4, 2, 4]) 
    with col:
        if st.button("✨ 무료로 분석 시작하기", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
            
    st.markdown('<div style="height: 20vh;"></div>', unsafe_allow_html=True)

# ==========================================
# [1단계 ~ 4단계] 메인 앱
# ==========================================
else:
    st.markdown("""
    <style>
        /* [1. 전체 배경 및 스크롤 설정] */
        .stApp { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            font-family: 'Noto Sans KR', sans-serif; 
            overflow-y: auto !important; /* 세로 스크롤 허용 */
        }
        
        /* [2. 메인 컨테이너 (Streamlit 내부 래퍼) 강제 확장] */
        div[data-testid="stAppViewContainer"] {
            height: auto !important;
            overflow: visible !important;
        }
        div[data-testid="stAppViewContainer"] > section {
            height: fit-content !important;
            overflow: visible !important;
        }

        /* [3. 하얀색 폰 화면 (껍데기)] - 여기가 핵심입니다 */
        .block-container {
            max-width: 600px !important;
            margin: 40px auto !important;
            
            height: auto !important;
            min-height: 800px !important;
            flex: none !important; 
            display: block !important;
            
            /* 디자인 */
            background-color: #ffffff !important;
            border-radius: 35px !important;
            padding: 40px 20px 40px 20px !important;
            box-shadow: 0 30px 60px rgba(0,0,0,0.4) !important;
            overflow: visible !important;
        }

        /* [4. 내부 콘텐츠 덩어리] - 얘도 같이 늘어나야 함 */
        div[data-testid="stVerticalBlock"] {
            height: fit-content !important;
            display: block !important;
            overflow: visible !important;
        }
        
        /* [5. 기타 스타일 (기존 유지)] */
        .phone-footer {
            margin-top: 20px;
            width: 100%;
            background: #ffffff;
            padding: 15px 20px;
            border-top: 1px solid #eee;
            border-bottom-left-radius: 35px;
            border-bottom-right-radius: 35px;
        }

        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important; border-radius: 12px !important; 
            padding: 12px 0 !important; font-weight: bold !important; border: none !important;
        }
        
        .chat-row { display: flex; width: 100%; margin-bottom: 15px; }
        .chat-row-user { justify-content: flex-end; }
        .chat-row-bot { justify-content: flex-start; }
        .chat-bubble { max-width: 80%; padding: 12px 16px; font-size: 0.95rem; line-height: 1.5; border-radius: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .user-bubble { background: #667eea; color: white; border-radius: 18px 18px 0 18px; }
        .bot-bubble { background: #ffffff; color: #333; border-radius: 18px 18px 18px 0; border: 1px solid #e9ecef; }
        .chat-profile { width: 38px; height: 38px; border-radius: 50%; background: #eee; display: flex; justify-content: center; align-items: center; margin-right: 10px; font-size: 22px; flex-shrink: 0; }
        .info-card { background: white; border-radius: 15px; padding: 20px; margin: 15px 0; border: 1px solid #eee; line-height: 1.7; }
        .scenario-result-box { background: #f8f9fa; border-left: 5px solid #667eea; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        
        .phone-header { text-align: center; padding-bottom: 10px; }
        .stChatInput { position: fixed !important; bottom: 20px !important; left: 50% !important; transform: translateX(-50%) !important; width: 100% !important; max-width: 580px !important; z-index: 1000 !important; }
        .stChatInput > div { border-radius: 25px !important; border: 1px solid #ccc !important; background: white !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h3 style="text-align:center; margin:0;">🧠 마인드스캔</h3>', unsafe_allow_html=True)
    curr = {1:25, 2:50, 3:75, 3.5:85, 4:100}.get(st.session_state.step, 0)
    st.markdown(f'<div style="background:#eee;height:6px;border-radius:10px;margin:15px 0;"><div style="background:#667eea;width:{curr}%;height:100%;border-radius:10px;"></div></div>', unsafe_allow_html=True)

    # ---------------- Step 1 분석 대상 설정 ----------------
    if st.session_state.step == 1:
        st.markdown("##### 1. 분석 대상 설정")
        with st.form("info"):
            relation = st.selectbox("관계", ["연인/썸", "친구", "직장", "가족", "기타"])
            name = st.text_input("이름 (호칭)")
            gender = st.selectbox("성별", ["남성", "여성"])
            c1, c2 = st.columns(2)
            with c1: birth = st.date_input("생년월일", value=datetime.date(2000,1,1), min_value=datetime.date(1950,1,1))
            with c2: cal = st.radio("달력", ["양력", "음력"], horizontal=True)
            if st.form_submit_button("🚀 분석 시작"):
                if name:
                    st.session_state.target_name = name
                    st.session_state.target_gender = gender
                    st.session_state.target_birth = birth
                    st.session_state.target_calendar = cal
                    st.session_state.target_relation = relation
                    st.session_state.step = 2
                    st.rerun()

    # ---------------- Step 2 성향 분석 ----------------
    elif st.session_state.step == 2:
        st.markdown(f"##### 2. {st.session_state.target_name}님 성향 분석")
        
        if not st.session_state.analysis_result:
            with st.spinner("대상 데이터 분석 중..."):
                try:
                    p = f"""
                    역할: 당신은 최고의 심리 분석가입니다. 대상의 생일 데이터를 기반으로 사주, 점성학 데이터를 심도있게 해석합니다.
                    대상: {st.session_state.target_name}({st.session_state.target_gender}, {st.session_state.target_birth})의 심리 성향을 분석해주세요.
                    
                    [지시사항]
                    1. 전문 용어(사주, 점성학)는 절대 사용하지 말고, 쉬운 심리학 표현을 쓰세요.
                    2. **난이도, 강점, 약점**은 반드시 **각각 한 줄씩** 작성하세요.
                    3. 강점과 약점의 키워드는 문장이 아니라 **단어로 나열**하고 앞에 **#**을 붙이세요.
                    4. 불필요한 서론이나 기호(-, *)를 쓰지 말고 아래 **[출력 예시]** 와 똑같은 구조로 출력하세요.
                    5. 난이도는 [최상/상/중/하/최하] 중에 적합한 것으로 골라 작성하세요.
                    
                    [출력 예시 - 이 구조를 그대로 따르세요]

                    **[Profile]**
                    **👾 난이도**: [중] 겉은 차갑지만 속은 따뜻한 반전 매력 
                    **⚔️ 강점**: #통찰력 #공감능력 #창의성 
                    **🩸 약점**: #내향성 #감정 기복 #예민함 
                    <br>
                    **✨ 타고난 성향**
                    (내용)
                    **🗣️ 대화 스타일**
                    (내용)
                    **💘 공략 포인트**
                    (내용)
                    """
                    st.session_state.analysis_result = ai_manager.generate_response(p)
                except Exception as e:
                    st.error(f"🚫 시스템 오류 발생: {e}")
                    st.code(traceback.format_exc()) # 상세 에러 로그 출력 (어디서 틀렸는지 줄번호까지 나옴)


        if st.session_state.analysis_result:
            formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', st.session_state.analysis_result)
            formatted_text = formatted_text.replace("\n", "<br>")
            st.markdown(f'<div class="info-card">{formatted_text}</div>', unsafe_allow_html=True)
            
            # 광고 A
            components.html(f"""<div style="display:flex;justify-content:center;"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}" crossorigin="anonymous"></script><ins class="adsbygoogle" style="display:inline-block;width:300px;height:250px" data-ad-client="{ADSENSE_CLIENT_ID}" data-ad-slot="{ADSENSE_SLOT_ID}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>""", height=260)
            
            # 버튼 위치 (하단 배치)
            st.write("")
            if st.button("다음: 상황 입력 👉"): st.session_state.step = 3; st.rerun()
                    
    # ---------------- Step 3 상황 설명 및 추가 자료료 ----------------
    elif st.session_state.step == 3:
        st.markdown("##### 3. 상황 데이터 입력")
        img = st.file_uploader("카톡 캡처 (선택)", type=['png','jpg','jpeg'])
        if img: st.session_state.context_image = Image.open(img); st.image(img, use_container_width=True)
        txt = st.text_area("상황 설명", height=120, placeholder="예: 어제 싸우고 연락이 없는데 무슨 심리일까?")
        
        if st.button("진단 시작 🩺"):
            if txt: st.session_state.context_text = txt; st.session_state.step = 3.5; st.rerun()

    # ---------------- Step 3.5 AI 행동 예측 ----------------
    elif st.session_state.step == 3.5:
        st.markdown("##### 🕵️‍♂️ AI 정밀 행동 예측")
        
        if not st.session_state.general_analysis:
            with st.spinner("최적의 시나리오 및 변수 예측 중..."):
                # 여러 시나리오 선택 없이, AI가 최적의 시나리오 1개를 자동 도출
                p = f"""
                대상:{st.session_state.analysis_result}
                상황:{st.session_state.context_text}
                
                [미션]
                1. 현재 상황에서 가장 가능성이 높은 **단 하나의 시나리오**를 도출하세요.
                2. 상대의 심리 데이터를 기반으로 이 상황에서 발생할 수 있는 주요 변수(상대의 기분 변화, 외부 요인 등)를 예측하세요.
                3. 전문 용어 없이 친절한 심리 상담가처럼 설명하세요.
                
                [출력 형식]
                **🎯 핵심 분석 (승률 00%)**
                (가장 유력한 상황 분석 내용 - 3문장 이내)
                
                **🔮 미래 예측**
                (당신이 이렇게 행동했을 때 벌어질 일 예측)
                
                **🎲 주요 변수**
                (주의해야 할 돌발 변수 1가지)
                """
                res = ai_manager.generate_response(p, st.session_state.context_image)
                st.session_state.general_analysis = res
                st.session_state.selected_scenario = res

        if st.session_state.general_analysis:
            formatted_analysis = re.sub(
                r'\*\*(.*?)\*\*', 
                r'<strong style="font-weight: 900;">\1</strong>', 
                st.session_state.general_analysis
            )
            formatted_analysis = formatted_analysis.replace("\n", "<br>")
            st.markdown(f"""
            <div class="scenario-result-box">
                {formatted_analysis}
            </div>
            """, unsafe_allow_html=True)
            
            # 광고 B
            components.html(f"""<div style="display:flex;justify-content:center;"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}" crossorigin="anonymous"></script><ins class="adsbygoogle" style="display:inline-block;width:300px;height:100px" data-ad-client="{ADSENSE_CLIENT_ID}" data-ad-slot="{ADSENSE_SLOT_ID}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>""", height=110)

            st.write("---")
            st.caption("위 분석을 바탕으로 시뮬레이션을 시작합니다.")
            
            # 버튼 하단 배치
            if st.button("💬 실전 시뮬레이션 채팅 입장", use_container_width=True):
                 st.session_state.messages = []
                 st.session_state.step = 4
                 st.rerun()
            
            if st.button("⬅️ 다시 입력"): st.session_state.step = 3; st.rerun()

            st.write("---")
            st.caption("위 분석을 바탕으로 시뮬레이션을 시작합니다.")
            
    # ---------------- Step 4 리얼 채팅 시뮬레이션 ----------------
    elif st.session_state.step == 4:
        st.markdown(f"##### 💬 {st.session_state.target_name}님과의 대화방")
        
        chat_container = st.container()
        
        with chat_container:
            if not st.session_state.messages:
                st.info(f"'{st.session_state.target_name}'님에게 보낼 첫 메시지를 입력해보세요.")
            
            for m in st.session_state.messages:
                if m["role"] == "user":
                    # 유저 (오른쪽, 보라색)
                    st.markdown(f"""
                    <div class="chat-row chat-row-user">
                        <div class="chat-bubble user-bubble">
                            {m["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # AI (왼쪽, 흰색)
                    try:
                        data = json.loads(m["content"])
                        reply_text = data.get("reply", "...")
                        emotion = data.get("emotion", "😐")
                        thoughts = data.get("thoughts", "")
                        tips = data.get("tips", "")
                        warning = data.get("warning", "")
                    except:
                        reply_text = m["content"]
                        emotion = "🤖"
                        thoughts = "데이터 없음"
                        tips = "" 
                        warning = ""

                    col_profile, col_bubble = st.columns([1, 7])
                    with col_profile:
                        st.markdown(f'<div class="chat-profile">{emotion}</div>', unsafe_allow_html=True)
                    with col_bubble:
                        st.markdown(f"""
                        <div class="chat-row chat-row-bot">
                            <div class="chat-bubble bot-bubble">
                                {reply_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 속마음 보기 (Expander) - 말풍선 바로 아래 위치, 기본적으로 닫혀있음
                        with st.expander("🔍 속마음 & 공략팁 (Click)"):
                            st.markdown(f"""
                            **🧠 속마음:** {thoughts}  
                            **💡 공략팁:** {tips}  
                            **⚠️ 주의:** {warning}
                            """)
                
            # 하단 여백 확보 (입력창에 가려지지 않게)
            st.write("<br>" * 3, unsafe_allow_html=True)

        # 입력창 (st.chat_input은 자동으로 하단 고정됨. CSS로 흰 창 내부에 있는 것처럼 보이게 디자인함)
        if user_input := st.chat_input("메시지 입력..."):
            # 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.rerun() # 즉시 렌더링 후 AI 답변 생성 트리거

        # AI 답변 생성 로직 (사용자 메시지가 방금 추가된 경우)
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            with st.spinner(f"{st.session_state.target_name}님이 입력 중..."):
                try:
                    user_last_msg = st.session_state.messages[-1]["content"]
                    # [수정] JSON 포맷 강제 및 1순위 답장만 생성하도록 유도
                    p = f"""
                    역할: {st.session_state.target_name} ({st.session_state.analysis_result})
                    현재상황: {st.session_state.selected_scenario}
                    
                    유저가 당신에게 메시지를 보냈습니다: "{user_last_msg}"
                    
                    [미션]
                    1. 당신(페르소나)의 말투로 **가장 적절한 답장(reply)** 하나를 작성하세요. (카톡 말투, 짧게,확률표시시)
                    2. 현재 당신의 **감정(emotion)**을 이모티콘 하나로 표현하세요.
                    3. 당신의 **속마음(thoughts)**, 유저를 위한 **공략팁(tips)**, **주의사항(warning)**을 분석하세요.
                    
                    [반드시 JSON 형식으로만 출력하세요]
                    {{
                        "reply": "여기에 답장 내용",
                        "emotion": "🥰",
                        "thoughts": "여기에 속마음",
                        "tips": "여기에 팁",
                        "warning": "여기에 주의사항"
                    }}
                    """
                    response_text = ai_manager.generate_response(p)
                    clean_json = response_text.replace("```json", "").replace("```", "").strip()
                    
                    st.session_state.messages.append({"role": "assistant", "content": clean_json})
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"🚫 시스템 오류 발생: {e}")
                    st.code(traceback.format_exc()) # 상세 에러 로그 출력 (어디서 틀렸는지 줄번호까지 나옴)

        # [Step 4의 기존 버튼 코드 자리에 덮어쓰세요]
        
        # 하단 여백 및 구분선
        st.write("<br>" * 3, unsafe_allow_html=True)
        st.write("---") 

        # 버튼 2개 나란히 배치 (왼쪽: 처음으로 / 오른쪽: 공유하기)
        c1, c2 = st.columns(2)
        
        with c1:
            # 처음으로 버튼
            if st.button("🔄 처음부터 다시하기", use_container_width=True, key="btn_restart_final"):
                session_manager.reset()
                st.rerun()
                
        with c2:
            # [수정됨] "🔗 공유하기" 버튼
            # 누르면 아래에 공유창(URL 복사 등)이 열렸다 닫혔다 함
            if st.button("🔗 공유하기", use_container_width=True, key="btn_toggle_share"):
                st.session_state.show_share = not st.session_state.show_share
                st.rerun()

        # 공유하기 스위치가 켜져있으면 UI 보여주기
        if st.session_state.show_share:
            st.markdown("""
                <div style="background-color:#f8f9fa; padding:20px; border-radius:15px; margin-top:15px; border:1px solid #eee;">
                """, unsafe_allow_html=True)
            
            # 제목 변경: 결과 공유하기 -> 공유하기
            st.markdown("<h5 style='text-align:center; color:#333; margin-bottom:15px;'>🔗 공유하기</h5>", unsafe_allow_html=True)
            
            # 1. URL 복사 기능 (가장 중요)
            share_url = "https://mind-scan.ai.kr"
            st.code(share_url, language=None) # 사용자가 꾹 눌러서 복사하기 편하게 코드 블록으로 제공
            st.caption("👆 위 링크를 복사해서 친구에게 보내보세요!")
            
            st.write("---")
            
    
