import streamlit as st
import numpy as np
import plotly.graph_objects as go
import math

# Page Config
st.set_page_config(
    page_title="3D 먼작귀 우사기 렌더링!",
    page_icon="🐰",
    layout="wide"
)

# Title & Intro
st.title("🐰 3D 먼작귀(Chiikawa) 우사기(Usagi) 렌더링!")
st.caption("우사기의 3D 형태를 감상하고, 특유의 정열적인 추임새와 움직임을 제어해보세요! 야하~!")

# --- Sidebar Controls ---
st.sidebar.header("⚙️ 우사기 상태 설정")

# 1. Pose/Expression
expression = st.sidebar.selectbox(
    "우사기 표정 / 상태",
    ["기본 (야하~!)", "신남 (우라!!)", "침착 (푸하-)", "정색/입 벌리기"]
)

# 2. Motion / Animation state
bounce_intensity = st.sidebar.slider("통통 튀기 강도", 0.0, 2.0, 0.8, 0.1)
ear_angle = st.sidebar.slider("귀 벌림 각도", 0, 45, 15, 5)

# 3. Yaha Soundboard!
st.sidebar.markdown("---")
st.sidebar.subheader("🔊 우사기 보이스 버튼")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("📢 야하~! (Yaha)"):
        st.toast("🐰: 야하~~~~~! ✨", icon="⚡")
    if st.button("📢 우라!! (Ura)"):
        st.toast("🐰: 우라라라라라라!! 🔥", icon="🔥")
with col2:
    if st.button("📢 푸하- (Fuha)"):
        st.toast("🐰: 푸하--- 🍵", icon="🍃")
    if st.button("📢 이햐-! (Ihya)"):
        st.toast("🐰: 이햐하하하하! 💥", icon="🎉")


# --- 3D Mesh Generator for Usagi ---
def create_usagi_mesh(expression, bounce, ear_deg):
    # 3D Mesh primitives
    def make_sphere(center, radius, res=30):
        u = np.linspace(0, 2 * np.pi, res)
        v = np.linspace(0, np.pi, res)
        x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
        y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
        z = center[2] + radius * np.outer(np.ones(np.size(u)), np.cos(v))
        return x, y, z

    def make_capsule(center, radius, height, tilt_deg=0, res=20):
        # Ear shapes
        u = np.linspace(0, 2 * np.pi, res)
        v = np.linspace(0, np.pi, res)
        
        # Base cylinder + caps
        z_grid = np.linspace(0, height, res)
        grid_u, grid_z = np.meshgrid(u, z_grid)
        x_cyl = radius * np.cos(grid_u)
        y_cyl = radius * np.sin(grid_u)
        
        # Tilt ear
        rad = math.radians(tilt_deg)
        x_rot = x_cyl * math.cos(rad) - grid_z * math.sin(rad)
        z_rot = x_cyl * math.sin(rad) + grid_z * math.cos(rad)
        
        return center[0] + x_rot, center[1] + y_cyl, center[2] + z_rot

    fig = go.Figure()

    # Bounce offset
    z_offset = abs(math.sin(bounce * 3)) * 0.4

    # 1. Usagi Body (Light Yellow / Cream Color)
    # Yellowish-cream: #FFF4B8
    usagi_yellow = "#FFF29D"
    
    # Body (Egg shape - Main Head + Body unified)
    x_body, y_body, z_body = make_sphere([0, 0, 1.2 + z_offset], radius=1.2, res=40)
    # Scale body slightly along Z to make it chubbier
    z_body = (z_body - (1.2 + z_offset)) * 1.1 + (1.2 + z_offset)
    
    fig.add_trace(go.Surface(
        x=x_body, y=y_body, z=z_body,
        colorscale=[[0, usagi_yellow], [1, usagi_yellow]],
        showscale=False,
        name="Body"
    ))

    # 2. Ears (Left & Right)
    ear_rad = 0.28
    ear_len = 1.4
    
    # Left Ear
    x_el, y_el, z_el = make_capsule([-0.4, 0, 2.1 + z_offset], ear_rad, ear_len, tilt_deg=-ear_deg)
    fig.add_trace(go.Surface(
        x=x_el, y=y_el, z=z_el,
        colorscale=[[0, usagi_yellow], [1, usagi_yellow]],
        showscale=False,
        name="Left Ear"
    ))
    
    # Right Ear
    x_er, y_er, z_er = make_capsule([0.4, 0, 2.1 + z_offset], ear_rad, ear_len, tilt_deg=ear_deg)
    fig.add_trace(go.Surface(
        x=x_er, y=y_er, z=z_er,
        colorscale=[[0, usagi_yellow], [1, usagi_yellow]],
        showscale=False,
        name="Right Ear"
    ))

    # 3. Eyes (Dark Brown Dots)
    eye_color = "#362619"
    # Left Eye
    x_eye_l, y_eye_l, z_eye_l = make_sphere([-0.38, 1.05, 1.4 + z_offset], radius=0.09)
    fig.add_trace(go.Surface(x=x_eye_l, y=y_eye_l, z=z_eye_l, colorscale=[[0, eye_color], [1, eye_color]], showscale=False))
    
    # Right Eye
    x_eye_r, y_eye_r, z_eye_r = make_sphere([0.38, 1.05, 1.4 + z_offset], radius=0.09)
    fig.add_trace(go.Surface(x=x_eye_r, y=y_eye_r, z=z_eye_r, colorscale=[[0, eye_color], [1, eye_color]], showscale=False))

    # 4. Cheeks (Pinkish Blushes)
    pink_color = "#FFAAA5"
    x_chk_l, y_chk_l, z_chk_l = make_sphere([-0.65, 0.9, 1.15 + z_offset], radius=0.18)
    fig.add_trace(go.Surface(x=x_chk_l, y=y_chk_l, z=z_chk_l, colorscale=[[0, pink_color], [1, pink_color]], showscale=False))
    
    x_chk_r, y_chk_r, z_chk_r = make_sphere([0.65, 0.9, 1.15 + z_offset], radius=0.18)
    fig.add_trace(go.Surface(x=x_chk_r, y=y_chk_r, z=z_chk_r, colorscale=[[0, pink_color], [1, pink_color]], showscale=False))

    # 5. Tail (White Fluffy Sphere behind)
    tail_color = "#FFFFFF"
    x_tail, y_tail, z_tail = make_sphere([0, -1.15, 0.7 + z_offset], radius=0.3)
    fig.add_trace(go.Surface(x=x_tail, y=y_tail, z=z_tail, colorscale=[[0, tail_color], [1, tail_color]], showscale=False))

    # 6. Mouth / Expression details (3D Curves/Points)
    if "입 벌리기" in expression or "우라" in expression:
        # Open Mouth (Dark Red inside)
        mouth_color = "#A82810"
        x_m, y_m, z_m = make_sphere([0, 1.12, 1.25 + z_offset], radius=0.14)
        fig.add_trace(go.Surface(x=x_m, y=y_m, z=z_m, colorscale=[[0, mouth_color], [1, mouth_color]], showscale=False))
    else:
        # Standard 'Y' Nose-Mouth (Pingu/Usagi style)
        fig.add_trace(go.Scatter3d(
            x=[0, 0, -0.1, 0.1],
            y=[1.14, 1.15, 1.14, 1.14],
            z=[1.35 + z_offset, 1.27 + z_offset, 1.22 + z_offset, 1.22 + z_offset],
            mode='lines',
            line=dict(color=eye_color, width=6),
            showlegend=False
        ))

    # Layout Adjustments
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-2.5, 2.5], showbackground=False, zeroline=False, visible=False),
            yaxis=dict(range=[-2.5, 2.5], showbackground=False, zeroline=False, visible=False),
            zaxis=dict(range=[0, 4.0], showbackground=False, zeroline=False, visible=False),
            aspectmode='cube',
            camera=dict(
                eye=dict(x=0.0, y=2.8, z=0.5) # Front view default
            )
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=650,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

# --- Main Layout ---
col_main, col_info = st.columns([3, 1])

with col_main:
    # Render 3D Usagi
    fig = create_usagi_mesh(expression, bounce_intensity, ear_angle)
    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("📋 우사기 프로필")
    st.markdown("""
    * **이름:** 우사기 (Usagi / 토끼)
    * **작품:** 먼가 작고 귀여운 녀석 (치이카와)
    * **특징:**
      * 언제나 기운이 넘치며 **"야하~!"**, **"우라!"** 같은 소리만 냄.
      * 제초 검정 3급 소지자 (스펙 보유자).
      * 정체불명의 행동을 하지만 친구들(치이카와, 하치와레)을 잘 챙겨줌.
    """)
    
    st.success("💡 **Tip:** 마우스로 3D 모델을 드래그하면 360도로 돌려보거나 꼬리를 관찰할 수 있습니다!")

    st.markdown("---")
    st.write("### 💃 시뮬레이터 가이드")
    st.write("- **통통 튀기 Slider:** 우사기의 통통 튀는 모션을 조정합니다.")
    st.write("- **귀 벌림 Slider:** 흥분도에 따라 귀의 각도가 달라집니다.")
