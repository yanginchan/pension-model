import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

try:
    import koreanize_matplotlib
except:
    pass

def est_hp(v, a): # 주택연금 로직
    return v * (0.002 + (max(0, a - 60) * 0.0001)) * 12 if a >= 60 else 0

def calc_hi(inc, prp): # 건보료 로직
    if inc <= 20000000: return 0, "피부양자"
    pts = (inc/1e6*20) + (prp/5e7*15)
    return (pts * 2400), "지역전환"

def run_sim(d):
    res = []
    irp, sav = d['irp'], d['sav']
    for a in range(60, 91):
        gap = d['npa'] - 65
        np = d['np'] * (1 + (gap * 0.072 if gap > 0 else gap * 0.06)) if a >= d['npa'] else 0
        hp = est_hp(d['hv'], 60) if d['use_hp'] else 0
        limit = max(0, 2e7 - np)
        d_sav = min(sav, 1.5e7, limit)
        sav -= d_sav
        need = d['tgt'] - (np + d_sav + hp)
        d_irp = min(irp, max(0, need))
        irp -= d_irp
        taxable = np + d_sav + d_irp
        hi_v, hi_s = calc_hi(taxable, d['hv'])
        cost = hi_v + taxable * 0.05
        res.append({"나이": a, "국민연금": np, "연금저축": d_sav, "IRP인출": d_irp, "주택연금": hp, "차감액": cost, "실수령액": (taxable + hp) - cost, "건보상태": hi_s, "남은자산": irp + sav})
        irp *= (1+d['roi']); sav *= (1+d['roi'])
    return pd.DataFrame(res)

st.set_page_config(page_title="은퇴설계 Pro", layout="wide")
st.title("🛡️ 연금수령 최적화 전문가 모델 Pro")

with st.sidebar:
    st.header("⚙️ 시나리오 설정")
    t_v = st.slider("🎯 목표 연 생활비(만원)", 1000, 20000, 4800)
    st.info(f"💰 연 목표: {t_val*10000 if 't_val' in locals() else t_v*10000:,}원")
    roi = st.slider("📈 예상 수익률(%)", 0.0, 10.0, 3.0) / 100
    st.header("🏠 부동산 & 주택연금")
    hv = st.number_input("공시지가(만원)", 0, 1000000, 90000)
    st.info(f"🏠 가치: {hv*10000:,}원")
    use_hp = st.checkbox("주택연금 포함")
    st.header("💰 보유 자산")
    irp_v = st.number_input("IRP 잔액(만원)", 0, 1000000, 25000)
    sav_v = st.number_input("연금저축 잔액(만원)", 0, 1000000, 15000)
    np_v = st.number_input("국민연금(만원)", 0, 10000, 1800); np_a = st.select_slider("개시나이", options=list(range(60, 71)), value=65)

df = run_sim({'tgt': t_v*10000, 'roi': roi, 'hv': hv*10000, 'use_hp': use_hp, 'irp': irp_v*10000, 'sav': sav_v*10000, 'np': np_v*10000, 'npa': np_a})

t1, t2, t3 = st.tabs(["📊 분석 그래프", "📑 데이터 시트", "💡 전문가 조언"])
with t1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("월 평균 실수령", f"{int(df['실수령액'].mean()/12):,}원")
    c2.metric("평생 차감액", f"{int(df['차감액'].sum()):,}원")
    c3.metric("90세 잔여 자산", f"{int(df['남은자산'].iloc[-1]):,}원")
    c4.metric("건보료 위험", f"{df[df['건보상태']=='지역전환']['나이'].min() if '지역전환' in df['건보상태'].values else '안전'}")

    fig, ax1 = plt.subplots(figsize=(10, 5))
    cols = ['국민연금', '연금저축', 'IRP인출', '주택연금']
    df.plot(kind='bar', x='나이', y=cols, stacked=True, ax=ax1, alpha=0.7)
    ax1.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
    
    ax2 = ax1.twinx()
    ax2.plot(df.index, df['남은자산'], color='red', marker='o', linewidth=2, label='자산잔액')
    
    # [수정된 부분] 함수 뒤에 ()를 꼭 붙였습니다!
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=9)
    st.pyplot(fig)

with t2:
    st.dataframe(df.style.format({col: "{:,.0f}" for col in df.columns if col not in ["나이", "건보상태"]}))
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        df.to_excel(w, index=False)
    st.download_button("📥 엑셀 다운로드", data=out.getvalue(), file_name="pension_report.xlsx")

with t3:
    if '지역전환' in df['건보상태'].values:
        st.warning(f"🚨 {df[df['건보상태']=='지역전환']['나이'].min()}세부터 건보료 주의!")
    else:
        st.success("✅ 평생 피부양자 유지가 가능합니다.")
    st.info(f"자산 유지 가능: **{df[df['남은자산'] > 0]['나이'].max()}세**")