import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 웹페이지 기본 설정
st.set_page_config(
    page_title="한-미 주요 주식 수익률 비교 분석기",
    page_icon="📈",
    layout="wide"
)

# 헤더 영역
st.title("📈 한-미 주요 주식 및 지수 수익률 비교")
st.markdown("""
당곡고등학교 학생 여러분의 금융 데이터 분석 탐구를 환영합니다! 👋
이 앱은 **yfinance** 라이브러리를 사용하여 한국과 미국의 주요 주식 및 시장 지수 데이터를 실시간으로 가져와 비교해 줍니다.
좌측 사이드바에서 분석하고 싶은 주식과 기간을 선택해 보세요.
""")

# 2. 분석할 주식 딕셔너리 정의 (한글 이름: yfinance 티커)
stock_dict = {
    "삼성전자 (Samsung)": "005930.KS",
    "SK하이닉스 (SK Hynix)": "000660.KS",
    "네이버 (NAVER)": "035420.KS",
    "카카오 (Kakao)": "035720.KS",
    "코스피 지수 (KOSPI)": "^KS11",
    "애플 (Apple - AAPL)": "AAPL",
    "마이크로소프트 (Microsoft - MSFT)": "MSFT",
    "테슬라 (Tesla - TSLA)": "TSLA",
    "엔비디아 (NVIDIA - NVDA)": "NVDA",
    "S&P 500 지수": "^GSPC"
}

# 3. 사이드바 - 사용자 입력 제어
st.sidebar.header("⚙️ 분석 설정")

# 주식 다중 선택 (기본값 설정)
selected_stock_names = st.sidebar.multiselect(
    "비교할 주식을 선택하세요 (복수 선택 가능)",
    options=list(stock_dict.keys()),
    default=["삼성전자 (Samsung)", "애플 (Apple - AAPL)", "S&P 500 지수"]
)

# 분석 기간 설정 (기본값: 최근 1년)
default_start = datetime.today() - timedelta(days=365)
start_date = st.sidebar.date_input("시작일 선택", default_start)
end_date = st.sidebar.date_input("종료일 선택", datetime.today())

# 선택된 주식 이름들을 yfinance 티커 배열로 변환
tickers = [stock_dict[name] for name in selected_stock_names]

# 4. 데이터 로드 및 시각화 로직
if not tickers:
    st.warning("⚠️ 분석할 주식을 최소 하나 이상 선택해 주세요!")
else:
    # 캐싱을 사용해 중복 로딩 방지
    @st.cache_data
    def load_stock_data(ticker_list, start, end):
        all_data = []
        for ticker in ticker_list:
            try:
                # auto_adjust=False 설정을 통해 수정종가(Adj Close) 컬럼을 명시적으로 요청합니다.
                df_single = yf.download(ticker, start=start, end=end, auto_adjust=False)
