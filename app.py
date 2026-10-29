import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import ezdxf
from io import BytesIO

# --- Konfigurasi Halaman Web ---
st.set_page_config(page_title="Kalkulator Geometri Jalan", layout="wide")
st.title("🛣️ Kalkulator & Visualisasi Tikungan Jalan")
st.write("Aplikasi web untuk menghitung parameter tikungan (FC, SCS, SS), menggambar sketsa, serta mengunduh hasil dalam format Excel dan DXF (AutoCAD).")

# --- Input Parameter di Sidebar Kiri ---
st.sidebar.header("Input Parameter")
Vr = st.sidebar.number_input("Kecepatan Rencana Vr (km/jam)", value=80.0, step=1.0)
Rc = st.sidebar.number_input("Jari-jari Tikungan Rc (m)", value=240.0, step=1.0)
delta_deg = st.sidebar.number_input("Sudut Tikungan Δ (°)", value=30.0, step=0.1)

hitung = st.sidebar.button("🚀 Hitung & Gambar", type="primary")

# --- Logika Perhitungan ---
if hitung:
    # 1. Hitung parameter umum
    f = -0.00065 * Vr + 0.192 if Vr <= 80 else -0.00125 * Vr + 0.24
    e = 0.08 
    Rmin = (Vr**2) / (127 * (e + f))

    if Rc < Rmin:
        st.error(f"⚠️ Rc ({Rc} m) < Rmin ({Rmin:.2f} m). Tikungan tidak aman! Harap perbesar jari-jari.")
    else:
        # 2. Hitung Ls Minimum
        Ls_shortt = (0.022 * Vr**3) / (Rc * 0.4) - (2.727 * Vr * e) / 0.4
        Ls_waktu = (Vr / 3.6) * 3
        Ls_gaya = Ls_shortt
        Ls_kelandaian = ((0.08 - 0.02) * Vr) / (3.6 * 0.025)
        Ls_min = max(Ls_shortt, Ls_waktu, Ls_gaya, Ls_kelandaian, 0)

        # 3. Tentukan Jenis Tikungan
        p = (Ls_min**2) / (24 * Rc)
        delta = math.radians(delta_deg)
        
        hasil = {
            "Vr (km/jam)": Vr,
            "Rc (m)": Rc,
            "Sudut Δ (°)": delta_deg,
            "f": round(f, 4),
            "Rmin (m)": round(Rmin, 3),
        }
        
        x_curve, y_curve = [], []

        if p < 0.25:
            # Full Circle (FC)
            jenis = "Full Circle (FC)"
            Tc = Rc * math.tan(delta / 2)
            Ec = Tc * math.tan(delta / 4)
            Lc = math.pi * Rc * delta_deg / 180
            L_total = Lc
            
            hasil.update({"Jenis Tikungan": jenis, "Tc (m)": round(Tc, 3), "Ec (m)": round(Ec, 3), "Lc (m)": round(Lc, 3), "L_total (m)": round(L_total, 3)})
            
            # Koordinat Gambar FC
            start_angle = math.pi/2 + delta/2
            end_angle = math.pi/2 - delta/2
            cx, cy = 0, -Rc / math.cos(delta/2)
            angles = np.linspace(start_angle, end_angle, 100)
            x_curve = cx + Rc * np.cos(angles)
            y_curve = cy + Rc * np.sin(angles)
            
        else:
            # Spiral-Circle-Spiral (SCS) atau Spiral-Spiral (SS)
            Ls = math.ceil(Ls_min) 
            theta_s = (Ls * 90) / (math.pi * Rc)
            delta_c = delta_deg - 2 * theta_s
            
            if delta_c > 0:
                jenis = "Spiral-Circle-Spiral (SCS)"
                Lc = (delta_c / 360) * 2 * math.pi * Rc
                L_total = Lc + 2 * Ls
            else:
                jenis = "Spiral-Spiral (SS)"
                theta_s = delta_deg / 2
                Ls = (theta_s * math.pi * Rc) / 90
                Lc = 0
                L_total = 2 * Ls
                delta_c = 0

            Xs = Ls * (1 - (Ls**2) / (40 * Rc**2))
            Ys = (Ls**2) / (6 * Rc)
            k = Xs - Rc * math.sin(math.radians(theta_s))
            p_val = Ys - Rc * (1 - math.cos(math.radians(theta_s)))
            Ts = (Rc + p_val) * math.tan(delta / 2) + k
            Es = ((Rc + p_val) / math.cos(delta / 2)) - Rc

            hasil.update({"Jenis Tikungan": jenis, "Ls (m)": round(Ls, 3), "θs (°)": round(theta_s, 3), "Δc (°)": round(delta_c, 3), "Lc (m)": round(Lc, 3), "Xs (m)": round(Xs, 3), "Ys (m)": round(Ys, 3), "k (m)": round(k, 3), "p (m)": round(p_val, 3), "Ts (m)": round(Ts, 3), "Es (m)": round(Es, 3), "L_total (m)": round(L_total, 3)})

            # Koordinat Gambar SCS/SS
            s_vals = np.linspace(0, Ls, 50)
            x_s1 = s_vals - (s_vals**5) / (40 * (Rc * Ls)**2)
            y_s1 = (s_vals**3) / (6 * Rc * Ls)
            
            theta_s_rad = math.radians(theta_s)
            Ox = Xs - Rc * math.sin(theta_s_rad)
            Oy = Ys + Rc * math.cos(theta_s_rad)
            
            if delta_c > 0:
                delta_c_rad = math.radians(delta_c)
                angles = np.linspace(math.pi/2 + theta_s_rad, math.pi/2 + theta_s_rad - delta_c_rad, 50)
                x_c = Ox - Rc * np.sin(angles)
                y_c = Oy - Rc * np.cos(angles)
            else:
                x_c, y_c = [], []
                
            CSx = Ox - Rc * math.sin(math.pi/2 + theta_s_rad - math.radians(delta_c))
            CSy = Oy - Rc * math.cos(math.pi/2 + theta_s_rad - math.radians(delta_c))
            
            STx = Ts - Ts * math.cos(math.radians(delta))
            STy = Ts * math.sin(math.radians(delta))
            
            x_s2, y_s2 = [], []
            for i in range(len(s_vals)-1, -1, -1):
                dx = x_s1[i] - Xs
                dy = y_s1[i] - Ys
                rot_dx = dx * math.cos(math.radians(delta)) - dy * math.sin(math.radians(delta))
                rot_dy = dx * math.sin(math.radians(delta)) + dy * math.cos(math.radians(delta))
                x_s2.append(STx + rot_dx)
                y_s2.append(STy + rot_dy)

            x_all = np.concatenate([x_s1, x_c, x_s2])
            y_all = np.concatenate([y_s1, y_c, y_s2])
            x_all = x_all - Ts
            y_all = -y_all
            
            angle_rot = -math.radians(delta/2)
            x_curve = x_all * math.cos(angle_rot) - y_all * math.sin(angle_rot)
            y_curve = x_all * math.sin(angle_rot) + y_all * math.cos(angle_rot)

        # --- TAMPILAN HASIL ---
        st.subheader(f"Hasil Perhitungan: {jenis}")
        
        # Tabel Hasil
        df = pd.DataFrame(list(hasil.items()), columns=["Parameter", "Nilai"])
        st.dataframe(df, use_container_width=True)

        # Gambar
        fig, ax = plt.subplots(figsize=(8, 5))
        L_vis = max(abs(x_curve[0]), abs(x_curve[-1])) * 1.5
        ax.plot([-L_vis, 0], [0, 0], 'k--', label='Tangen')
        ax.plot([0, L_vis], [0, 0], 'k--')
        ax.plot(x_curve, y_curve, 'b-', linewidth=2, label='Kurva')
        ax.plot(0, 0, 'ro', label='PI')
        ax.plot(x_curve[0], y_curve[0], 'go', label='Awal')
        ax.plot(x_curve[-1], y_curve[-1], 'go', label='Akhir')
        
        ax.annotate('PI', (0, 0), textcoords="offset points", xytext=(0,10), ha='center', color='red', fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend()
        st.pyplot(fig)

        # --- TOMBOL DOWNLOAD ---
        st.subheader("📥 Unduh Hasil")
        col1, col2 = st.columns(2)

        with col1:
            # Buat file Excel
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Hasil')
            excel_data = output_excel.getvalue()
            
            st.download_button(
                label="Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"hasil_tikungan_{jenis}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

        with col2:
            # Buat file DXF
            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            msp.add_line((-L_vis, 0), (0, 0), dxfattribs={"color": 8, "linetype": "DASHED"})
            msp.add_line((0, 0), (L_vis, 0), dxfattribs={"color": 8, "linetype": "DASHED"})
            msp.add_lwpolyline(list(zip(x_curve, y_curve)), dxfattribs={"color": 5})
            msp.add_circle((0, 0), radius=Rc*0.02, dxfattribs={"color": 1})
            msp.add_circle((x_curve[0], y_curve[0]), radius=Rc*0.02, dxfattribs={"color": 3})
            msp.add_circle((x_curve[-1], y_curve[-1]), radius=Rc*0.02, dxfattribs={"color": 3})
            
            output_dxf = BytesIO()
            doc.write(output_dxf)
            dxf_data = output_dxf.getvalue()
            
            st.download_button(
                label="Download CAD (.dxf)",
                data=dxf_data,
                file_name=f"gambar_tikungan_{jenis}.dxf",
                mime="application/dxf",
                type="primary"
            )

else:
    st.info("👈 Silakan atur parameter di panel sebelah kiri, lalu klik tombol **Hitung & Gambar**.")
