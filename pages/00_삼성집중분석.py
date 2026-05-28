import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# 1. 페이지 설정 및 디자인 레이아웃 정의
st.set_page_config(
    page_title="삼성전자 집중 분석 대시보드",
    page_icon="🔵",
    layout="wide"
)

# 헤더 영역
st.title("🔵 삼성전자 (005930.KS) 집중 분석 대시보드")
st.markdown("""
당곡고등학교 학생 여러분! 대한민국 대표 기업 **삼성전자**의 주가 흐름과 시장 지표를 한눈에 볼 수 있는 전문 분석 페이지입니다.
과거의 가격 흐름 속에서 어떤 패턴이 숨어있는지, 이동평균선을 통해 주가의 추세를 분석해 보세요.
""")

# 2. 사이드바 - 분석 기간 설정
st.sidebar.header("⚙️ 분석 설정")
period_options = {
    "최근 3개월": 90,
    "최근 6개월": 180,
    "최근 1년 (기본)": 365,
    "최근 3년": 365 * 3,
    "최근 5년": 365 * 5
}
selected_period_label = st.sidebar.selectbox("분석 기간을 선택하세요", list(period_options.keys()), index=2)
days_to_subtract = period_options[selected_period_label]

start_date = datetime.today() - timedelta(days=days_to_subtract)
end_date = datetime.today()

# 3. 데이터 로드 및 전처리 (안전하게 데이터 수집)
@st.cache_data(ttl=3600)  # 1시간 동안 캐싱하여 속도 최적화
def get_samsung_data(start, end):
    try:
        ticker = yf.Ticker("005930.KS")
        # 데이터 수집 (최신 안정화된 history 메서드 사용)
        df = ticker.history(start=start, end=end)
        
        if df.empty:
            return pd.DataFrame(), {}
        
        # 시간대(Timezone) 제거하여 표 병합 및 처리를 매끄럽게 함
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        # 이동평균선(Moving Average) 계산
        # 20일(단기), 60일(중기), 120일(장기) 추세를 보여줍니다.
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        # 기업 개요 정보 수집 (안전하게 예외 처리)
        info = {}
        try:
            info = ticker.info
        except:
            pass
            
        return df, info
    except Exception as e:
        st.error(f"데이터 수집 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(), {}

with st.spinner("삼성전자 실시간 금융 데이터를 분석하는 중입니다..."):
    df, info = get_samsung_data(start_date, end_date)

# 4. 화면 구성 시작
if df.empty:
    st.error("❌ 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
else:
    # ─── 핵심 지표 요약 카드 (KPI Metrics) ───
    # 가장 최근 데이터와 전날 데이터 비교
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    price_diff = current_price - prev_price
    price_diff_percent = (price_diff / prev_price) * 100
    
    # 52주 최고가 및 최저가 계산 (데이터 내에서 직접 계산하여 안전함)
    high_52w = df['High'].max()
    low_52w = df['Low'].min()
    avg_volume = df['Volume'].mean()

    # 상단 4개 열로 레이아웃 분할
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="현재 주가 (종가 기준)", 
            value=f"{int(current_price):,} 원", 
            delta=f"{int(price_diff):+,} 원 ({price_diff_percent:+.2f}%)"
        )
    with col2:
        st.metric(
            label="기간 최고가", 
            value=f"{int(high_52w):,} 원"
        )
    with col3:
        st.metric(
            label="기간 최저가", 
            value=f"{int(low_52w):,} 원"
        )
    with col4:
        st.metric(
            label="기간 평균 거래량", 
            value=f"{int(avg_volume):,} 주"
        )

    st.markdown("---")

    # ─── 시각화 영역 (탭으로 구성하여 깔끔하게 제공) ───
    tab1, tab2, tab3 = st.tabs(["📈 주가 & 이동평균선 추이", "📊 거래량 분석", "🏢 기업 재무 정보"])

    with tab1:
        st.subheader("💡 주가와 이동평균선(MA)")
        st.markdown("""
        * **이동평균선(Moving Average)**은 주가의 잡음을 줄이고 전체적인 추세를 보여주는 선입니다.
        * **단기선(20일선)**이 **장기선(60일/120일선)**을 뚫고 올라가는 현상을 **골든크로스(매수 신호)**, 반대로 뚫고 내려가는 것을 **데드크로스(매도 신호)**라고 부릅니다. 차트에서 이 신호를 찾아보세요!
        """)
        
        # Plotly Graph Objects를 사용하여 정교한 캔들스틱/선 차트 그리기
        fig = go.Figure()
        
        # 1. 실제 종가 선
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='삼성전자 주가', line=dict(color='#004B87', width=2.5)))
        
        # 2. 20일 이동평균선
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20일 이평선(단기)', line=dict(color='#FF5733', width=1.5, dash='dash')))
        
        # 3. 60일 이동평균선
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60일 이평선(중기)', line=dict(color='#33FF57', width=1.5)))
        
        # 4. 120일 이동평균선
        fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], name='120일 이평선(장기)', line=dict(color='#8A33FF', width=1.5)))

        fig.update_layout(
            title=f"삼성전자 주가 및 이동평균선 추이 ({selected_period_label})",
            xaxis_title="날짜",
            yaxis_title="주가 (원)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🔊 거래량 변동 분석")
        st.markdown("주가가 상승할 때 거래량이 동반되어 터지는지, 혹은 주가가 빠지는데 거래량이 없는지 분석하면 세력이나 대중의 심리를 파악할 수 있습니다.")
        
        # 거래량 바 차트 그리기
        # 거래량이 늘어난 날은 초록색, 줄어든 날은 빨간색으로 시각화하기 위한 색상 처리
        df['Vol_Color'] = ['#2ca02c' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#d62728' for i in range(len(df))]
        
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=df.index, 
            y=df['Volume'], 
            name='거래량', 
            marker_color=df['Vol_Color']
        ))
        
        fig_vol.update_layout(
            title=f"일별 거래량 변동 ({selected_period_label})",
            xaxis_title="날짜",
            yaxis_title="거래량 (주)",
            height=400
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with tab3:
        st.subheader("🔍 주요 투자 및 기업 정보")
        
        # yfinance info 데이터에서 안전하게 기업 기본 지표들을 추출
        market_cap = info.get('marketCap', '정보 없음')
        if isinstance(market_cap, int):
            market_cap_formatted = f"{market_cap / 1000000000000:.2f} 조 원"
        else:
            market_cap_formatted = market_cap
            
        pe_ratio = info.get('trailingPE', '정보 없음')
        dividend_yield = info.get('dividendYield', '정보 없음')
        if isinstance(dividend_yield, float):
            dividend_yield_formatted = f"{dividend_yield * 100:.2f} %"
        else:
            dividend_yield_formatted = dividend_yield

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 📊 기업 펀더멘탈 (기본 수치)")
            fundamental_df = pd.DataFrame({
                "지표명": ["시가총액", "주가수익비율 (PER)", "배당수익률"],
                "값": [market_cap_formatted, f"{pe_ratio} 배" if pe_ratio != '정보 없음' else pe_ratio, dividend_yield_formatted]
            })
            st.table(fundamental_df)
            
        with col_b:
            st.markdown("### 🏢 기업 개요 및 설명")
            business_summary = info.get('longBusinessSummary', '기업 설명 정보를 불러올 수 없습니다.')
            # 번역 API가 따로 없으므로 기본 영문 설명을 깔끔하게 텍스트 상자에 담아 보여줍니다.
            st.write(business_summary)

        st.markdown("### 📁 최근 날짜별 수치 데이터 테이블")
        st.dataframe(df[['Open', 'High', 'Low', 'Close', 'Volume']].tail(15))
