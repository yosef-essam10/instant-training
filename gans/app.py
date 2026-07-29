import streamlit as st
import torch
import torch.nn as nn
import torchvision.utils as vutils
import numpy as np
from PIL import Image
import io

# ----------------------------- Model definition (must match training) -----------------------------
NZ, NGF, NC = 128, 64, 3

class Generator(nn.Module):
    def __init__(self, nz=NZ, ngf=NGF, nc=NC):
        super().__init__()
        self.main = nn.Sequential(
            nn.ConvTranspose2d(nz, ngf * 16, 4, 1, 0, bias=False),
            nn.BatchNorm2d(ngf * 16), nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 16, ngf * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 8), nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 8, ngf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 4), nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 4, ngf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 2), nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 2, ngf, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf), nn.ReLU(True),
            nn.ConvTranspose2d(ngf, nc, 4, 2, 1, bias=False),
            nn.Tanh(),
        )

    def forward(self, z):
        return self.main(z)

# ----------------------------------------- Page setup -----------------------------------------
st.set_page_config(page_title="AI Face Generator", page_icon="\U0001F9EC", layout="wide")

CUSTOM_CSS = """
<style>
:root {
    --accent1: #7b2ff7;
    --accent2: #00d4ff;
    --bg: #0f0c1d;
    --card: #1a1533;
}
.stApp {
    background: radial-gradient(circle at top left, #1a1533 0%, #0f0c1d 60%);
    color: #eae6ff;
}
h1, h2, h3 { color: #f2eeff !important; }
.hero {
    padding: 28px 32px;
    border-radius: 18px;
    background: linear-gradient(120deg, rgba(123,47,247,0.25), rgba(0,212,255,0.15));
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 24px;
}
.hero h1 { font-size: 2.1rem; margin-bottom: 6px; }
.hero p { color: #c9c3ea; font-size: 1.02rem; }
div.stButton > button {
    background: linear-gradient(120deg, var(--accent1), var(--accent2));
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.6em 1.6em;
    font-weight: 600;
    letter-spacing: 0.3px;
}
div.stButton > button:hover {
    filter: brightness(1.1);
    color: white;
}
section[data-testid="stSidebar"] {
    background: #150f28;
    border-right: 1px solid rgba(255,255,255,0.06);
}
.stSlider label, .stNumberInput label { color: #c9c3ea !important; }
.face-card {
    background: var(--card);
    border-radius: 14px;
    padding: 10px;
    border: 1px solid rgba(255,255,255,0.06);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h1>\U0001F9EC AI Face Generator</h1>
        <p>DCGAN trained on CelebA \u2014 generate brand-new synthetic human faces from random noise.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------- Model loading -----------------------------------------
@st.cache_resource
def load_generator(path="generator_final.pth"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Generator().to(device)
    state = torch.load(path, map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model, device

try:
    netG, device = load_generator()
    model_ready = True
except Exception as e:
    model_ready = False
    load_error = str(e)

# ----------------------------------------- Sidebar controls -----------------------------------------
with st.sidebar:
    st.header("Controls")
    n_faces = st.slider("Number of faces", min_value=1, max_value=64, value=16, step=1)
    seed = st.number_input("Random seed (-1 = random)", value=-1, step=1)
    generate_clicked = st.button("\u2728 Generate Faces", use_container_width=True)

if not model_ready:
    st.error(
        "Could not load `generator_final.pth`. Make sure this file is in the same "
        "folder as app.py (it is produced by the training notebook, Section 9)."
    )
    st.caption(f"Details: {load_error}")
else:
    if "faces" not in st.session_state:
        st.session_state.faces = None

    if generate_clicked:
        if seed is not None and seed >= 0:
            torch.manual_seed(int(seed))
        with st.spinner("Generating faces..."):
            with torch.no_grad():
                noise = torch.randn(n_faces, NZ, 1, 1, device=device)
                fakes = netG(noise).cpu()
                fakes = (fakes + 1) / 2.0  # [-1,1] -> [0,1]
        st.session_state.faces = fakes

    if st.session_state.faces is not None:
        fakes = st.session_state.faces
        cols = st.columns(4)
        for idx in range(fakes.shape[0]):
            img = (fakes[idx].permute(1, 2, 0).numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img)
            with cols[idx % 4]:
                st.markdown('<div class="face-card">', unsafe_allow_html=True)
                st.image(pil_img, use_container_width=True)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                st.download_button(
                    "Download", buf.getvalue(), file_name=f"face_{idx}.png",
                    mime="image/png", key=f"dl_{idx}", use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Set your options in the sidebar and click **Generate Faces** to begin.")
