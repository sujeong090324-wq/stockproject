import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px


st.set_page_config(
    page_title="한미 주요 주식 수익률 비교",
    page_icon="📈",
    layout="wide"
)


# -----------------------------
# 기본 종목 목록
# -----------------------------
STOCK_GROUPS = {
    "한국 주요 주식": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "LG에너지솔루션": "373220.KS",
        "현대차": "005380.KS",
        "기아": "000270.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "셀트리온": "068270.KS",
        "POSCO홀딩스": "005490.KS",
        "삼성바이오로직스": "207940.KS",
    },
    "미국 주요 주식 / ETF": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "NVIDIA": "NVDA",
        "Alphabet": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META",
        "Tesla": "TSLA",
        "JPMorgan": "JPM",
        "Exxon Mobil": "XOM",
        "S&P500 ETF": "SPY",
        "Nasdaq100 ETF": "QQQ",
    }
}


# 화면 표시용 라벨 생성
label_to_ticker = {}
ticker_to_label = {}

for group_name, stocks in STOCK_GROUPS.items():
    for name, ticker in stocks.items():
        label = f"{name} ({ticker})"
        label_to_ticker[label] = ticker
        ticker_to_label[ticker] = label


# -----------------------------
# 함수 정의
# -----------------------------
@st.cache_data(ttl=60 * 30, show_spinner=False)
def load_stock_data(tickers, period, interval):
    """
    yfinance에서 종가 데이터를 가져오는 함수
    auto_adjust=True 이므로 배당/액면분할 등이 조정된 가격 기준
    """
    tickers = sorted(list(set([t.strip().upper() for t in tickers if t.strip()])))

    if len(tickers) == 0:
        return pd.DataFrame()

    try:
        data = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True
        )
    except Exception:
        return pd.DataFrame()

    if data.empty:
        return pd.DataFrame()

    # yfinance 결과가 MultiIndex인지 아닌지에 따라 Close 추출
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"].copy()
        elif "Close" in data.columns.get_level_values(1):
            close = data.xs("Close", axis=1, level=1).copy()
        else:
            return pd.DataFrame()
    else:
        if "Close" in data.columns:
            close = data[["Close"]].copy()
            close.columns = [tickers[0]]
        else:
            return pd.DataFrame()

    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()

    # 요청한 종목 중 누락된 컬럼은 NaN으로 추가
    for ticker in tickers:
        if ticker not in close.columns:
            close[ticker] = np.nan

    close = close[tickers]
    close = close.dropna(axis=1, how="all")

    return close


def normalize_to_100(series):
    """
    각 종목의 시작 가격을 100으로 맞춰 수익률 비교가 가능하게 변환
    """
    s = series.dropna()
    if s.empty:
        return series
    first_value = s.iloc[0]
    return series / first_value * 100


def calculate_max_drawdown(series):
    """
    최대 낙폭, Max Drawdown 계산
    """
    s = series.dropna()
    if len(s) < 2:
        return np.nan

    running_max = s.cummax()
    drawdown = s / running_max - 1
    return drawdown.min() * 100


def make_summary_table(close_df):
    """
    종목별 주요 지표 요약표 생성
    """
    rows = []

    for ticker in close_df.columns:
        price = close_df[ticker].dropna()

        if len(price) < 2:
            continue

        daily_return = price.pct_change().dropna()

        start_price = price.iloc[0]
        end_price = price.iloc[-1]
        cumulative_return = (end_price / start_price - 1) * 100

        if len(daily_return) > 1:
            annual_volatility = daily_return.std() * np.sqrt(252) * 100

            if daily_return.std() != 0:
                sharpe_like = daily_return.mean() / daily_return.std() * np.sqrt(252)
            else:
                sharpe_like = np.nan
        else:
            annual_volatility = np.nan
            sharpe_like = np.nan

        max_drawdown = calculate_max_drawdown(price)

        rows.append({
            "티커": ticker,
            "종목": ticker_to_label.get(ticker, ticker),
            "시작일": price.index[0].strftime("%Y-%m-%d"),
            "마지막일": price.index[-1].strftime("%Y-%m-%d"),
            "시작가격": start_price,
            "마지막가격": end_price,
            "누적수익률(%)": cumulative_return,
            "연환산변동성(%)": annual_volatility,
            "샤프비율 유사값": sharpe_like,
            "최대낙폭 MDD(%)": max_drawdown,
        })

    summary = pd.DataFrame(rows)

    if not summary.empty:
        summary = summary.sort_values("누적수익률(%)", ascending=False)

    return summary


def format_summary_table(summary):
    """
    보기 좋게 숫자 포맷 적용
    """
    formatted = summary.copy()

    number_columns = [
        "시작가격",
        "마지막가격",
        "누적수익률(%)",
        "연환산변동성(%)",
        "샤프비율 유사값",
        "최대낙폭 MDD(%)"
    ]

    for col in number_columns:
        if col in formatted.columns:
            formatted[col] = formatted[col].map(
                lambda x: "-" if pd.isna(x) else f"{x:,.2f}"
            )

    return formatted


# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.header("설정")

all_labels = list(label_to_ticker.keys())

default_labels = [
    "삼성전자 (005930.KS)",
    "SK하이닉스 (000660.KS)",
    "Apple (AAPL)",
    "Microsoft (MSFT)",
    "NVIDIA (NVDA)",
    "S&P500 ETF (SPY)",
]

selected_labels = st.sidebar.multiselect(
    "비교할 기본 종목 선택",
    options=all_labels,
    default=[label for label in default_labels if label in all_labels]
)

custom_tickers_text = st.sidebar.text_input(
    "직접 티커 추가",
    value="",
    placeholder="예: 005930.KS, 035720.KS, AAPL, TSLA"
)

period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "최대": "max",
}

period_label = st.sidebar.selectbox(
    "조회 기간",
    options=list(period_options.keys()),
    index=3
)

interval_options = {
    "일봉": "1d",
    "주봉": "1wk",
    "월봉": "1mo",
}

interval_label = st.sidebar.selectbox(
    "데이터 간격",
    options=list(interval_options.keys()),
    index=0
)

use_log_scale = st.sidebar.checkbox(
    "가격 차트 로그 스케일 사용",
    value=False
)


# -----------------------------
# 선택 종목 정리
# -----------------------------
selected_tickers = [label_to_ticker[label] for label in selected_labels]

if custom_tickers_text.strip():
    custom_tickers = [
        ticker.strip().upper()
        for ticker in custom_tickers_text.split(",")
        if ticker.strip()
    ]

    for ticker in custom_tickers:
        if ticker not in selected_tickers:
            selected_tickers.append(ticker)
            ticker_to_label[ticker] = ticker


# -----------------------------
# 메인 화면
# -----------------------------
st.title("📈 한국·미국 주요 주식 수익률 비교 웹앱")

st.markdown(
    """
    `yfinance` 데이터를 활용해 한국과 미국 주요 주식의 가격 흐름, 누적 수익률, 변동성, 상관관계를 비교합니다.

    - 한국 코스피 종목 예시: `005930.KS`
    - 한국 코스닥 종목 예시: `091990.KQ`
    - 미국 종목 예시: `AAPL`, `MSFT`, `NVDA`
    """
)

st.info(
    "한국 주식은 원화, 미국 주식은 달러 기준입니다. "
    "정규화 수익률 비교는 가능하지만 환율 효과는 반영하지 않습니다."
)

if len(selected_tickers) == 0:
    st.warning("왼쪽 사이드바에서 비교할 종목을 1개 이상 선택하세요.")
    st.stop()


period = period_options[period_label]
interval = interval_options[interval_label]

with st.spinner("주가 데이터를 불러오는 중입니다..."):
    close_df = load_stock_data(selected_tickers, period, interval)


if close_df.empty:
    st.error(
        "데이터를 불러오지 못했습니다. 티커가 올바른지 확인해 주세요. "
        "한국 종목은 예를 들어 삼성전자 `005930.KS`처럼 입력해야 합니다."
    )
    st.stop()


# 종목명으로 컬럼 표시
display_close_df = close_df.rename(
    columns={ticker: ticker_to_label.get(ticker, ticker) for ticker in close_df.columns}
)


# -----------------------------
# 핵심 지표
# -----------------------------
summary_df = make_summary_table(close_df)

if summary_df.empty:
    st.error("분석할 수 있는 데이터가 충분하지 않습니다.")
    st.stop()

best_row = summary_df.iloc[0]
worst_row = summary_df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "분석 종목 수",
        f"{len(close_df.columns)}개"
    )

with col2:
    st.metric(
        "최고 누적수익률",
        best_row["종목"],
        f"{best_row['누적수익률(%)']:.2f}%"
    )

with col3:
    st.metric(
        "최저 누적수익률",
        worst_row["종목"],
        f"{worst_row['누적수익률(%)']:.2f}%"
    )

with col4:
    start_date = close_df.index.min().strftime("%Y-%m-%d")
    end_date = close_df.index.max().strftime("%Y-%m-%d")
    st.metric(
        "분석 기간",
        f"{start_date}",
        f"~ {end_date}"
    )


st.divider()


# -----------------------------
# 정규화 수익률 차트
# -----------------------------
st.subheader("1. 시작점을 100으로 맞춘 수익률 비교")

normalized_df = close_df.apply(normalize_to_100)
display_normalized_df = normalized_df.rename(
    columns={ticker: ticker_to_label.get(ticker, ticker) for ticker in normalized_df.columns}
)

fig_normalized = px.line(
    display_normalized_df,
    x=display_normalized_df.index,
    y=display_normalized_df.columns,
    labels={
        "value": "기준값, 시작=100",
        "index": "날짜",
        "variable": "종목"
    },
    title="정규화 가격 추이"
)

fig_normalized.update_layout(
    hovermode="x unified",
    legend_title_text="종목"
)

st.plotly_chart(fig_normalized, use_container_width=True)


# -----------------------------
# 누적 수익률 막대 차트
# -----------------------------
st.subheader("2. 종목별 누적 수익률")

bar_df = summary_df[["종목", "누적수익률(%)"]].copy()
bar_df = bar_df.sort_values("누적수익률(%)", ascending=True)

fig_bar = px.bar(
    bar_df,
    x="누적수익률(%)",
    y="종목",
    orientation="h",
    text="누적수익률(%)",
    title="조회 기간 누적 수익률"
)

fig_bar.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="outside"
)

fig_bar.update_layout(
    xaxis_title="누적 수익률(%)",
    yaxis_title="종목"
)

st.plotly_chart(fig_bar, use_container_width=True)


# -----------------------------
# 실제 가격 차트
# -----------------------------
st.subheader("3. 실제 종가 차트")

fig_price = px.line(
    display_close_df,
    x=display_close_df.index,
    y=display_close_df.columns,
    labels={
        "value": "종가, 현지 통화 기준",
        "index": "날짜",
        "variable": "종목"
    },
    title="종가 추이"
)

fig_price.update_layout(
    hovermode="x unified",
    legend_title_text="종목"
)

if use_log_scale:
    fig_price.update_yaxes(type="log")

st.plotly_chart(fig_price, use_container_width=True)


# -----------------------------
# 요약표
# -----------------------------
st.subheader("4. 종목별 요약 지표")

st.caption(
    """
    - 누적수익률: 조회 기간 시작 가격 대비 마지막 가격의 변화율
    - 연환산변동성: 일별 수익률 표준편차를 연 단위로 환산한 값
    - 샤프비율 유사값: 무위험수익률을 0으로 가정한 단순 지표
    - MDD: 조회 기간 중 고점 대비 최대 하락률
    """
)

formatted_summary = format_summary_table(summary_df)

st.dataframe(
    formatted_summary,
    use_container_width=True,
    hide_index=True
)


# -----------------------------
# 상관관계 히트맵
# -----------------------------
st.subheader("5. 일별 수익률 상관관계")

daily_return_df = close_df.pct_change().dropna(how="all")
display_daily_return_df = daily_return_df.rename(
    columns={ticker: ticker_to_label.get(ticker, ticker) for ticker in daily_return_df.columns}
)

if len(display_daily_return_df.columns) >= 2 and len(display_daily_return_df) >= 2:
    corr_df = display_daily_return_df.corr()

    fig_corr = px.imshow(
        corr_df,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="일별 수익률 상관관계"
    )

    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("상관관계를 계산하려면 최소 2개 이상의 종목과 충분한 데이터가 필요합니다.")


# -----------------------------
# 원본 데이터 확인 및 다운로드
# -----------------------------
st.subheader("6. 원본 종가 데이터")

with st.expander("종가 데이터 보기"):
    st.dataframe(display_close_df, use_container_width=True)

csv_data = display_close_df.to_csv().encode("utf-8-sig")

st.download_button(
    label="CSV 파일 다운로드",
    data=csv_data,
    file_name="stock_price_data.csv",
    mime="text/csv"
)


# -----------------------------
# 하단 설명
# -----------------------------
st.divider()

st.markdown(
    """
    ### 학습 포인트

    이 앱을 통해 다음 개념을 연습할 수 있습니다.

    1. `yfinance`를 이용한 금융 데이터 수집
    2. `pandas`를 활용한 수익률 계산
    3. 누적 수익률과 변동성 비교
    4. 상관관계 분석
    5. `Streamlit`을 이용한 데이터 웹앱 제작
    """
)
