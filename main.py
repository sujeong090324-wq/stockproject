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
    # 캐싱을 사용해 중복 로딩 방지 (웹앱 속도 향상)
    @st.cache_data
    def load_stock_data(ticker_list, start, end):
        all_data = []
        for ticker in ticker_list:
            try:
                # yf.Ticker().history()는 단일 종목의 데이터를 깨끗한 단일 인덱스 형태로 가져옵니다.
                # 최신 yfinance의 버그를 예방하는 가장 확실한 방법입니다.
                ticker_obj = yf.Ticker(ticker)
                df_single = ticker_obj.history(start=start, end=end)
                
                if df_single.empty:
                    continue
                
                # 미국과 한국 주식은 타임존(Tz) 정보가 다릅니다.
                # 병합할 때 시간대 충돌 오류를 방지하기 위해 타임존 정보만 제거(Naive 전환)해 줍니다.
                if df_single.index.tz is not None:
                    df_single.index = df_single.index.tz_localize(None)
                
                # 배당과 액면분할이 자동 반영된 수정종가('Close') 컬럼만 가져옵니다.
                series = df_single['Close']
                series.name = ticker
                all_data.append(series)
            except Exception as e:
                st.warning(f"⚠️ {ticker} 데이터를 가져오는 중 오류가 발생했습니다: {e}")
                continue
        
        if all_data:
            # 가져온 개별 주식 데이터를 날짜 기준으로 옆으로 합쳐 하나의 큰 표로 만듭니다.
            return pd.concat(all_data, axis=1)
        else:
            return pd.DataFrame()

    try:
        with st.spinner("야후 파이낸스에서 데이터를 가져오는 중입니다..."):
            df = load_stock_data(tickers, start_date, end_date)

        if df.empty:
            st.error("❌ 선택하신 기간에 해당하는 데이터가 존재하지 않습니다. 날짜를 다시 설정해 주세요.")
        else:
            # 영어 티커 열 이름을 사용자가 알아보기 쉽게 한글 이름으로 변경
            inv_stock_dict = {v: k for k, v in stock_dict.items()}
            df = df.rename(columns=inv_stock_dict)

            # 한국과 미국의 휴장일 차이로 인해 발생하는 임시 빈칸(NaN)을 앞뒤 값으로 채워줍니다.
            df_clean = df.ffill().bfill()

            # 누적 수익률 계산 공식: ((현재 가격 / 시작일 가격) - 1) * 100
            normalized_df = (df_clean / df_clean.iloc[0] - 1) * 100

            # 탭(Tab) 구성으로 시각화 화면 정리
            tab1, tab2, tab3 = st.tabs(["📊 누적 수익률 비교", "📈 실제 주가 변동", "📋 요약 데이터"])

            with tab1:
                st.subheader("🔍 누적 수익률 (%) 비교 차트")
                st.markdown("**시작일의 가치를 0%**로 기준 잡고, 선택한 기간 동안 어떤 주식이 가장 높은 성과를 냈는지 직관적으로 비교합니다.")
                
                # 인터랙티브 선 그래프 그리기
                fig_return = px.line(
                    normalized_df, 
                    labels={"value": "누적 수익률 (%)", "Date": "날짜"},
                    title="선택 기간 누적 수익률 추이"
                )
                fig_return.update_layout(hovermode="x unified")
                st.plotly_chart(fig_return, use_container_width=True)

            with tab2:
                st.subheader("💵 개별 주가 원본 차트")
                st.markdown("각 주식의 실제 종가 추이입니다. *주의: 원화(KRW)와 달러(USD) 단위가 다르므로 값의 크기 자체를 직접 비교하지 마세요.*")
                
                fig_price = px.line(
                    df_clean, 
                    labels={"value": "주가 (원화 또는 달러)", "Date": "날짜"},
                    title="선택 주식의 실제 주가 추이"
                )
                fig_price.update_layout(hovermode="x unified")
                st.plotly_chart(fig_price, use_container_width=True)

            with tab3:
                st.subheader("📌 기간 내 통계 요약 및 원본 데이터")
                
                # 각 주식별 성과 분석
                summary_list = []
                for col in df_clean.columns:
                    start_val = df_clean[col].iloc[0]
                    end_val = df_clean[col].iloc[-1]
                    total_return = ((end_val - start_val) / start_val) * 100
                    max_val = df_clean[col].max()
                    min_val = df_clean[col].min()
                    
                    summary_list.append({
                        "종목명": col,
                        "시작가": f"{start_val:,.2f}",
                        "종료가(현재)": f"{end_val:,.2f}",
                        "기간 누적 수익률": f"{total_return:+.2f}%",
                        "기간 최고가": f"{max_val:,.2f}",
                        "기간 최저가": f"{min_val:,.2f}"
                    })
                
                summary_df = pd.DataFrame(summary_list)
                st.table(summary_df)

                st.markdown("### 🗂️ 날짜별 상세 데이터")
                st.dataframe(df_clean)

    except Exception as e:
        st.error(f"데이터를 처리하는 과정에서 오류가 발생했습니다: {e}")
