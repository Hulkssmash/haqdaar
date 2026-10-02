"""Haqdaar - Streamlit version (for Streamlit Community Cloud). Run: streamlit run streamlit_app.py"""
import os

os.environ.setdefault("SEARCH_MODE", "keyword")  # light search, no ML packages needed

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Haqdaar - حقدار", page_icon="🏠")
st.title("Haqdaar — حقدار")
st.write("Find out which government schemes you may qualify for. "
         "کون سی سرکاری اسکیمیں آپ کے لیے ہو سکتی ہیں۔")
st.caption("No login needed. Do not enter your CNIC number here. "
           "Your answers are saved anonymously to improve the tool. / "
           "آپ کے جوابات بغیر نام کے محفوظ کیے جاتے ہیں۔")

tab1, tab2, tab3 = st.tabs(["Check my eligibility / اہلیت چیک کریں",
                            "Ask a question / سوال پوچھیں",
                            "Is this link official? / کیا یہ لنک سرکاری ہے؟"])

with tab1:
    province = st.selectbox("Province / صوبہ", ui.PROVINCES, format_func=lambda x: x[0])[1]
    with st.form("eligibility"):
        age = st.number_input("Age / عمر", min_value=0, max_value=120, value=0, step=1,
                              help="Leave 0 if you prefer not to say")
        occupation = st.selectbox("What do you do? / آپ کیا کرتے ہیں؟", ui.OCCUPATIONS, format_func=lambda x: x[0])[1]
        income = st.selectbox("Monthly household income / ماہانہ آمدنی", ui.INCOME_BANDS, format_func=lambda x: x[0])[1]
        family = st.number_input("Family size / خاندان کے افراد", min_value=0, max_value=40, value=0, step=1)
        district = st.selectbox("District / ضلع", ui.district_choices(province), format_func=lambda x: x[0])[1]
        submitted = st.form_submit_button("Check / چیک کریں", type="primary")
    if submitted:
        profile = {"province": province, "age": age or None, "occupation": occupation,
                   "income_band": income, "family_size": family or None, "district": district}
        st.markdown(ui.run_eligibility(profile))

with tab2:
    question = st.text_input("Your question / آپ کا سوال",
                             placeholder="e.g. What is the age limit for Apna Ghar?")
    if st.button("Ask / پوچھیں", type="primary"):
        st.markdown(ui.run_ask(question))

with tab3:
    url = st.text_input("Paste a link / لنک یہاں ڈالیں")
    if st.button("Check link / لنک چیک کریں", type="primary"):
        st.markdown(ui.run_link(url))
