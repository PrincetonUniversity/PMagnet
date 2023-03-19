import os.path
from PIL import Image
import streamlit as st
import base64

STREAMLIT_ROOT = os.path.dirname(__file__)


def ui_mc(m):

    st.title('2023 IEEE PELS-Google-Tesla-Princeton MagNet Challenge')
    st.image(Image.open(os.path.join(STREAMLIT_ROOT, 'img', 'mclogo.jpg')), width=500)
    st.header('[Sign-Up for Updates about MagNet Challenge](https://forms.gle/aAmcwB5G5kvaDvJB9)')
    
    with open(os.path.join(STREAMLIT_ROOT, 'img', 'handbook.pdf'),"rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="1200" height="500" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.markdown("""---""")
