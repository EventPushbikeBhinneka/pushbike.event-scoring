import streamlit as st
import pandas as pd
from io import BytesIO
import json
import os
import math

st.set_page_config(page_title="Pushbike Race Scoring System", page_icon="🚲", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-left: 5px solid #2a5298;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATABASE GLOBAL & SISTEM DRAFT
# ==========================================
@st.cache_resource
def get_global_database():
    return {
        "live_payload": None,
        "saved_df": None,
        "event_name": "BHINNEKA RACING FEST",
        "logo_url": ""
    }

db = get_global_database()

if db["saved_df"] is None and os.path.exists("draft_turnamen.json"):
    try:
        with open("draft_turnamen.json", "r") as f:
            draft_raw = json.load(f)
            db["saved_df"] = pd.DataFrame(draft_raw.get("df_records", []))
            db["event_name"] = draft_raw.get("event_name", db["event_name"])
            db["logo_url"] = draft_raw.get("logo_url", db["logo_url"])
    except:
        pass

# ==========================================
# NAVIGASI ROLE
# ==========================================
with st.sidebar:
    st.header("👤 Akses Pengguna")
    role = st.radio("Pilih Akses:", ["👥 Penonton (Live Score)", "🔑 Panitia / Juri (Input Skor)"])
    st.divider()

# ==========================================
# 1. TAMPILAN KHUSUS PENONTON / MC
# ==========================================
if role == "👥 Penonton (Live Score)":
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
        elif db.get("logo_url"):
            try: st.image(db["logo_url"], width=120)
            except: st.markdown("## 🚴‍♂️")
        else:
            st.markdown("## 🚴‍♂️")
    with col_title:
        st.markdown(f"## 🏆 {db.get('event_name', 'Pushbike Race Event')}")
        st.caption("🔴 Live Timing & Official Standings Board")

    st.write("---")
    
    col_btn, _ = st.columns([2, 8])
    with col_btn:
        if st.button("🔄 Refresh Data Real-Time", use_container_width=True):
            st.rerun()

    live_data = db["live_payload"]
    if live_data is None and os.path.exists("live_standing.json"):
        try:
            with open("live_standing.json", "r") as f:
                live_data = json.load(f)
        except:
            pass

    if live_data and live_data.get('tables_dict'):
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0; color:#1e3c72;">🏁 KELAS: {live_data.get('kelas', '-')}</h4>
            <span style="font-size:0.85rem; color:#666;">Status: Hasil Resmi Terverifikasi Juri</span>
        </div>
        """, unsafe_allow_html=True)
        
        tables_dict = live_data.get('tables_dict', {})
        available_tabs = [k for k, v in tables_dict.items() if len(v) > 0]
        
        if available_tabs:
            tabs_ui = st.tabs(available_tabs)
            for tab_name, tab_ui in zip(available_tabs, tabs_ui):
                with tab_ui:
                    for block_title, data_table in tables_dict[tab_name]:
                        st.markdown(f"#### 📋 {block_title}")
                        df_view = pd.DataFrame(data_table)
                        st.dataframe(df_view, hide_index=True, use_container_width=True)
                        st.write("")
        else:
            st.info("Belum ada data tabel yang siap ditampilkan.")
    else:
        st.info("ℹ️ Belum ada babak yang dipublikasikan juri untuk kelas ini.")
    
    st.stop()

# ==========================================
# 2. TAMPILAN ADMIN / PANITIA (DILINDUNGI PIN)
# ==========================================
with st.sidebar:
    pin = st.text_input("Masukkan PIN Panitia:", type="password")
    if pin != "1234":
        st.error("Masukkan PIN yang benar untuk menginput skor.")
        st.stop()

    st.success("✅ Terverifikasi sebagai Panitia")
    st.header("⚙️ Pengaturan Event")
    db["event_name"] = st.text_input("Nama Event / Judul Banner:", value=db.get("event_name", "BHINNEKA RACING FEST"))
    db["logo_url"] = st.text_input("URL Link Logo Eksternal (Opsional):", value=db.get("logo_url", ""))
    
    st.header("🛠️ Kustom Format & Bagan Race")
    batas_gate = st.number_input("Kapasitas Rider per Gate / Podium", min_value=2, max_value=12, value=10)
    
    selected_piala = st.multiselect(
        "Kategori Piala yang Diperebutkan:",
        ["Utama", "Novice", "Rookie", "Beginner", "Newbie"],
        default=["Utama", "Novice", "Rookie", "Beginner"]
    )
    if "Utama" not in selected_piala:
        selected_piala = ["Utama"] + selected_piala

    skema_alur = st.selectbox(
        "Skema Babak Gugur:",
        [
            "Otomatis (Berdasarkan Jumlah Peserta)",
            "Quarter-Final -> Semi-Final -> Final (Lengkap)",
            "Quarter-Final -> Langsung Multi-Final (Cepat)",
            "Langsung Semi-Final -> Final",
            "Langsung Multi-Final (Tanpa QF/SF)"
        ]
    )
    
    custom_qf_quota = st.number_input("Rider Teratas per Grup ke Babak Lolos (QF/SF):", min_value=1, max_value=10, value=5)
    custom_qf_heats = st.number_input("Jumlah Heat/Grup Quarter-Final:", min_value=2, max_value=8, value=4)
    enable_repechage = st.checkbox("Aktifkan Jalur Repechage", value=True)
    
    st.divider()
    
    # TOMBOL DOWNLOAD TEMPLATE EXCEL KOSONG
    def generate_excel_template():
        out = BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            sample_data = {
                "NO": [1, 2, 3, 4, 5, 6, 7, 8],
                "Kelas": ["2022 Boys", "2022 Boys", "2022 Boys", "2022 Boys", "2022 Boys", "2022 Boys", "2022 Boys", "2022 Boys"],
                "Group": [1, 1, 1, 1, 2, 2, 2, 2],
                "Number plate": ["11", "832", "99", "177", "38", "168", "99B", "10"],
                "Name": ["Arbi Gemoy", "Kanaka Adinata", "Khalid Anaku", "Davanka", "Jerome", "Jason", "Haikal", "Rafassya"],
                "Team": ["Barbados", "KARA ROLLER", "Bhinneka", "Doublepoint", "Cakids", "Bumbleride", "CPB", "CPB"]
            }
            df_sample = pd.DataFrame(sample_data)
            df_sample.to_excel(writer, sheet_name='Data Peserta', index=False)
            
            df_guide = pd.DataFrame({
                "Nama Kolom Wajib": ["NO", "Kelas", "Group", "Number plate", "Name", "Team"],
                "Keterangan": [
                    "Nomor urut peserta",
                    "Nama kategori kelas turnamen (misal: 2022 Boys, 2023 MIX)",
                    "Nomor grup kualifikasi moto (1, 2, 3, dst.)",
                    "Nomor plat rider",
                    "Nama lengkap anak / rider",
                    "Nama komunitas / tim / privateer"
                ]
            })
            df_guide.to_excel(writer, sheet_name='Petunjuk Format', index=False)
        return out.getvalue()

    st.download_button(
        label="📥 DOWNLOAD TEMPLATE EXCEL PESERTA",
        data=generate_excel_template(),
        file_name="Template_Peserta_Pushbike.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    if st.button("🗑️ Reset Semua Data Server"):
        db["live_payload"] = None
        db["saved_df"] = None
        if os.path.exists("live_standing.json"): os.remove("live_standing.json")
        if os.path.exists("draft_turnamen.json"): os.remove("draft_turnamen.json")
        st.rerun()

st.title("🛠️ Panel Panitia - Scoring System")

uploaded_file = st.file_uploader("📂 Upload Data Peserta (.xlsx / .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            db["saved_df"] = pd.read_csv(uploaded_file)
        else:
            db["saved_df"] = pd.read_excel(uploaded_file)
        st.success("File peserta berhasil diunggah!")
    except Exception as e:
        st.error(f"Gagal membaca file upload: {e}")

if db["saved_df"] is None:
    st.info("Silakan unggah file data peserta atau gunakan tombol download template di sidebar kiri.")
    st.stop()

df = db["saved_df"].copy()
df.columns = df.columns.str.strip()

for col in ['Group', 'Team', 'Number plate', 'Gate M1', 'Gate M2', 'M1', 'M2', 'Hasil QF', 'Hasil Repechage', 'Hasil Semi-Final', 'Hasil Akhir']:
    if col not in df.columns: df[col] = "-"
        
def clean_moto_val(v):
    v = str(v).strip().upper()
    if v in ['DNS', 'DNF']: return v
    try: return str(int(float(v)))
    except: return "-"
    
df['M1'] = df['M1'].apply(clean_moto_val)
df['M2'] = df['M2'].apply(clean_moto_val)

# FASE 1: KUALIFIKASI MOTO
st.header("1. 🏁 Fase 1: Kualifikasi (Moto 1 & 2)")
kelas_list = [k for k in df['Kelas'].dropna().unique().tolist() if str(k).strip() != ""]

if not kelas_list:
    st.warning("Kolom 'Kelas' tidak ditemukan pada file.")
    st.stop()

selected_kelas = st.selectbox("Pilih Kelas:", kelas_list)
df_kelas = df[df['Kelas'] == selected_kelas].copy()

grup_list = sorted([g for g in df_kelas['Group'].unique() if str(g).strip() not in ["", "-", "NAN", "None", "nan"]])

col_m_mode, col_m_btn = st.columns([3, 2])
with col_m_mode:
    mode_input_moto = st.radio(
        "🚥 Mode Fokus Input:", 
        ["Tampilkan Semua (M1 & M2)", "Fokus Input Moto 1 Saja", "Fokus Input Moto 2 Saja"], 
        horizontal=True
    )
with col_m_btn:
    if st.button("🎲 Auto Susun Silang Gate M1/M2 (Default)"):
        for g in grup_list:
            sub_idx = df_kelas[df_kelas['Group'] == g].index
            jml = len(sub_idx)
            df.loc[sub_idx, 'Gate M1'] = [str(i) for i in range(1, jml + 1)]
            df.loc[sub_idx, 'Gate M2'] = [str(x+1 if x%2!=0 and x<jml else (x-1 if x%2==0 else x)) for x in range(1, jml + 1)]
        db["saved_df"] = df
        st.rerun()

edited_motos = []
moto_errors = []

for g in grup_list:
    df_g = df_kelas[df_kelas['Group'] == g].copy()
    jml_rider = len(df_g)
    
    if (df_g['Gate M1'] == "-").all():
        df_g['Gate M1'] = [str(i) for i in range(1, jml_rider + 1)]
    if (df_g['Gate M2'] == "-").all():
        df_g['Gate M2'] = df_g['Gate M1'].apply(lambda x: str(int(x)+1 if int(x)%2!=0 and int(x)<jml_rider else (int(x)-1 if int(x)%2==0 else int(x))) if str(x).isdigit() else "1")
    
    options = ["-"] + [str(i) for i in range(1, jml_rider + 1)] + ["DNS", "DNF"]
    gate_options = [str(i) for i in range(1, jml_rider + 1)]
    
    col_cfg = {
        "NO": st.column_config.TextColumn("NO", disabled=True),
        "Number plate": st.column_config.TextColumn("No. Plate", disabled=True),
        "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
        "Team": st.column_config.TextColumn("Komunitas", disabled=True),
        "Gate M1": st.column_config.SelectboxColumn("Gate M1 (Live Draw)", options=gate_options),
        "Gate M2": st.column_config.SelectboxColumn("Gate M2 (Live Draw)", options=gate_options),
        "M1": st.column_config.SelectboxColumn("Moto 1", options=options),
        "M2": st.column_config.SelectboxColumn("Moto 2", options=options)
    }
    
    cols_to_show = ['NO', 'Number plate', 'Name', 'Team', 'Gate M1', 'Gate M2']
    if mode_input_moto == "Fokus Input Moto 1 Saja":
        cols_to_show.append('M1')
    elif mode_input_moto == "Fokus Input Moto 2 Saja":
        cols_to_show.append('M2')
        cols_to_show.insert(6, 'M1')
        col_cfg["M1"] = st.column_config.TextColumn("Moto 1 (Terkunci)", disabled=True)
    else:
        cols_to_show.extend(['M1', 'M2'])
    
    st.markdown(f"**🔹 Grup {g}** ({jml_rider} Rider)")
    edited_g = st.data_editor(df_g[cols_to_show], column_config=col_cfg, hide_index=True, key=f"moto_{selected_kelas}_{g}", use_container_width=True)
    
    if mode_input_moto == "Fokus Input Moto 1 Saja":
        edited_g['M2'] = df_g['M2'].values
    elif mode_input_moto == "Fokus Input Moto 2 Saja":
        edited_g['M1'] = df_g['M1'].values
    
    m1_vals = [v for v in edited_g['M1'].astype(str) if v not in ["-", "DNS", "DNF", "nan", ""]]
    m2_vals = [v for v in edited_g['M2'].astype(str) if v not in ["-", "DNS", "DNF", "nan", ""]]
    
    if len(m1_vals) != len(set(m1_vals)): 
        moto_errors.append(f"Grup {g} - Moto 1: Posisi Finish tidak boleh sama.")
    if len(m2_vals) != len(set(m2_vals)): 
        moto_errors.append(f"Grup {g} - Moto 2: Posisi Finish tidak boleh sama.")
        
    edited_g['M1_Num'] = edited_g['M1'].apply(lambda x: jml_rider + 2 if x in ['DNS', 'DNF'] else (int(x) if str(x).isdigit() else 0))
    edited_g['M2_Num'] = edited_g['M2'].apply(lambda x: jml_rider + 2 if x in ['DNS', 'DNF'] else (int(x) if str(x).isdigit() else 0))
    edited_g['Total Point'] = edited_g['M1_Num'] + edited_g['M2_Num']
    edited_g['Group'] = g
    
    edited_motos.append(edited_g)
    st.write("---")

if moto_errors:
    for err in moto_errors: st.error(f"⚠️ {err}")
    st.stop()

edited_df_moto = pd.concat(edited_motos) if edited_motos else df_kelas
klasemen = df_kelas.copy()
klasemen.update(edited_df_moto[['Gate M1', 'Gate M2', 'M1', 'M2']])
klasemen['M1_Num'] = edited_df_moto['M1_Num']
klasemen['M2_Num'] = edited_df_moto['M2_Num']
klasemen['Total Point'] = edited_df_moto['Total Point']

df.update(klasemen)
db["saved_df"] = df

klasemen_aktif = klasemen[klasemen['Total Point'] > 0].copy()
grup_valid = sorted([g for g in klasemen_aktif['Group'].unique() if str(g) not in ["", "-", "NAN"]])
total_peserta_aktif = len(klasemen_aktif)

klasemen_aktif['Status'] = "-"
klasemen_aktif['Gate'] = "-"
klasemen_aktif['Status'] = klasemen_aktif['Status'].astype(str)
klasemen_aktif['Gate'] = klasemen_aktif['Gate'].astype(str)

# DETEKSI SKEMA
use_qf = False
qf_direct_to_final = False

if skema_alur == "Quarter-Final -> Semi-Final -> Final (Lengkap)":
    use_qf = True
elif skema_alur == "Quarter-Final -> Langsung Multi-Final (Cepat)":
    use_qf = True
    qf_direct_to_final = True
elif skema_alur == "Otomatis (Berdasarkan Jumlah Peserta)" and total_peserta_aktif >= 36:
    use_qf = True

FINAL_TIERS = [f"Final {p}" for p in selected_piala] + ["Finisher"]

# =========================================================================
# SEEDING & DISTRIBUSI BABAK MOTO KE TAHAP BERIKUTNYA
# =========================================================================
if total_peserta_aktif > 0 and skema_alur != "Langsung Multi-Final (Tanpa QF/SF)":
    klasemen_aktif = klasemen_aktif.sort_values(by=['Group', 'Total Point', 'M2_Num', 'M1_Num'])
    klasemen_aktif['Rank di Grup'] = klasemen_aktif.groupby('Group').cumcount() + 1
    
    quota = custom_qf_quota
    num_heat = int(custom_qf_heats) if use_qf else 2
    heat_prefix = "Quarter-Final" if use_qf else "Semi-Final"
    
    rank_tiers = {r: [] for r in range(1, quota + 1)}
    rep_riders = []
    rest_riders = []
    
    for g_name in grup_valid:
        g_df = klasemen_aktif[klasemen_aktif['Group'] == g_name]
        for r in range(1, quota + 1):
            r_idx = g_df[g_df['Rank di Grup'] == r].index.tolist()
            if r_idx: rank_tiers[r].extend(r_idx)
        
        if enable_repechage:
            rep_idx = g_df[g_df['Rank di Grup'] == quota + 1].index.tolist()
            if rep_idx: rep_riders.extend(rep_idx)
            rem_idx = g_df[g_df['Rank di Grup'] > quota + 1].index.tolist()
            if rem_idx: rest_riders.extend(rem_idx)
        else:
            rem_idx = g_df[g_df['Rank di Grup'] > quota].index.tolist()
            if rem_idx: rest_riders.extend(rem_idx)

    # Non-lolos langsung Finisher
    if rest_riders:
        for idx_r in rest_riders:
            klasemen_aktif.loc[idx_r, 'Status'] = "Finisher"
            klasemen_aktif.loc[idx_r, 'Gate'] = "-"

    # Serpentine Cross-Seeding
    heat_gate_counter = {h: 1 for h in range(1, num_heat + 1)}
    for r in range(1, quota + 1):
        riders_in_this_rank = rank_tiers[r]
        heat_order = list(range(1, num_heat + 1)) if r % 2 != 0 else list(range(num_heat, 0, -1))
        
        for idx_r in riders_in_this_rank:
            target_heat = min(heat_order, key=lambda h: heat_gate_counter[h])
            assigned_gate = heat_gate_counter[target_heat]
            
            klasemen_aktif.loc[idx_r, 'Status'] = f"{heat_prefix} {target_heat}"
            klasemen_aktif.loc[idx_r, 'Gate'] = str(assigned_gate)
            heat_gate_counter[target_heat] += 1

    if rep_riders:
        for i, idx_r in enumerate(rep_riders):
            klasemen_aktif.loc[idx_r, 'Status'] = "Repechage"
            klasemen_aktif.loc[idx_r, 'Gate'] = str(i + 1)

    klasemen_aktif['Status_Moto'] = klasemen_aktif['Status'].astype(str)

    # ==========================================
    # FASE 2: REPECHAGE
    # ==========================================
    rep_df = klasemen_aktif[klasemen_aktif['Status'] == 'Repechage'].copy()
    rep_df['Gate_Sort'] = pd.to_numeric(rep_df['Gate'], errors='coerce').fillna(99)
    rep_df = rep_df.sort_values('Gate_Sort')
    
    if enable_repechage and len(rep_df) > 0:
        st.header("2. 🛟 Fase 2: Repechage")
        rep_options = ["-"] + [str(i) for i in range(1, len(rep_df) + 1)]
        editor_columns_rep = {
            "NO": None, 
            "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
            "Name": st.column_config.TextColumn("Nama Rider", disabled=True), 
            "Hasil Repechage": st.column_config.SelectboxColumn("Posisi Finish", options=rep_options),
            "Gate": st.column_config.TextColumn("Gate", disabled=True)
        }
        edited_rep = st.data_editor(rep_df[['Number plate', 'Name', 'Hasil Repechage', 'Gate']], column_config=editor_columns_rep, hide_index=True, key=f"rep_{selected_kelas}", use_container_width=True)
        
        for idx in edited_rep.index:
            hr = str(edited_rep.at[idx, 'Hasil Repechage']).strip()
            klasemen_aktif.loc[idx, 'Hasil Repechage'] = hr
            df.loc[idx, 'Hasil Repechage'] = hr
            if hr.isdigit():
                pos = int(hr)
                if use_qf:
                    if pos == 4:
                        klasemen_aktif.loc[idx, 'Status'] = "Quarter-Final 1"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    elif pos == 3:
                        klasemen_aktif.loc[idx, 'Status'] = "Quarter-Final 2"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    elif pos == 2:
                        klasemen_aktif.loc[idx, 'Status'] = "Quarter-Final 3"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    elif pos == 1:
                        klasemen_aktif.loc[idx, 'Status'] = "Quarter-Final 4"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    else:
                        klasemen_aktif.loc[idx, 'Status'] = "Finisher"
                        klasemen_aktif.loc[idx, 'Gate'] = "-"
                else:
                    if pos == 1:
                        klasemen_aktif.loc[idx, 'Status'] = "Semi-Final 1"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    elif pos == 2:
                        klasemen_aktif.loc[idx, 'Status'] = "Semi-Final 2"
                        klasemen_aktif.loc[idx, 'Gate'] = str(batas_gate)
                    else:
                        klasemen_aktif.loc[idx, 'Status'] = "Finisher"
                        klasemen_aktif.loc[idx, 'Gate'] = "-"
        st.divider()

    # ==========================================
    # FASE 3A: QUARTER-FINAL
    # ==========================================
    if use_qf:
        st.header("3. ⚡ Fase 3A: Quarter-Final")
        qf_list = [f"Quarter-Final {i}" for i in range(1, num_heat + 1)]
        four_tier_mode = all(k in selected_piala for k in ["Utama", "Novice", "Rookie", "Beginner"])
        
        for qf_name in qf_list:
            qf_sub = klasemen_aktif[klasemen_aktif['Status'] == qf_name].copy()
            qf_sub['Gate_Sort'] = pd.to_numeric(qf_sub['Gate'], errors='coerce').fillna(99)
            qf_sub = qf_sub.sort_values('Gate_Sort')
            
            if len(qf_sub) > 0:
                st.markdown(f"**🔹 {qf_name}** ({len(qf_sub)} Rider)")
                qf_options = ["-"] + [str(i) for i in range(1, len(qf_sub) + 1)]
                col_cfg_qf = {
                    "Number plate": st.column_config.TextColumn("No. Plate", disabled=True),
                    "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
                    "Hasil QF": st.column_config.SelectboxColumn("Posisi Finish QF", options=qf_options),
                    "Gate": st.column_config.TextColumn("Gate", disabled=True)
                }
                edited_qf_sub = st.data_editor(qf_sub[['Number plate', 'Name', 'Hasil QF', 'Gate']], column_config=col_cfg_qf, hide_index=True, key=f"qf_{selected_kelas}_{qf_name}", use_container_width=True)
                
                for idx in edited_qf_sub.index:
                    hqf = str(edited_qf_sub.at[idx, 'Hasil QF']).strip()
                    klasemen_aktif.loc[idx, 'Hasil QF'] = hqf
                    df.loc[idx, 'Hasil QF'] = hqf
                    if hqf.isdigit():
                        pos = int(hqf)
                        
                        # PILIHAN A: MODE CEPAT (LANGSUNG MULTI-FINAL)
                        if qf_direct_to_final:
                            if pos <= 2: klasemen_aktif.loc[idx, 'Status'] = "Final Utama"
                            elif pos <= 4: klasemen_aktif.loc[idx, 'Status'] = "Final Novice" if "Novice" in selected_piala else "Finisher"
                            elif pos <= 6: klasemen_aktif.loc[idx, 'Status'] = "Final Rookie" if "Rookie" in selected_piala else "Finisher"
                            elif pos <= 8: klasemen_aktif.loc[idx, 'Status'] = "Final Beginner" if "Beginner" in selected_piala else "Finisher"
                            elif pos <= 10: klasemen_aktif.loc[idx, 'Status'] = "Final Newbie" if "Newbie" in selected_piala else "Finisher"
                            else: klasemen_aktif.loc[idx, 'Status'] = "Finisher"
                            
                        # PILIHAN B: MODE LENGKAP (QF -> SF -> FINAL)
                        else:
                            if four_tier_mode:
                                if pos <= 4:
                                    target_sf = "Semi-Final 1 (Utama/Novice)" if ("1" in qf_name or "3" in qf_name) else "Semi-Final 2 (Utama/Novice)"
                                elif pos <= 8:
                                    target_sf = "Semi-Final 3 (Rookie/Beginner)" if ("1" in qf_name or "3" in qf_name) else "Semi-Final 4 (Rookie/Beginner)"
                                else:
                                    target_sf = "Finisher"
                                klasemen_aktif.loc[idx, 'Status'] = target_sf
                            else:
                                if pos <= 5:
                                    target_sf = "Semi-Final 1" if ("1" in qf_name or "3" in qf_name) else "Semi-Final 2"
                                    klasemen_aktif.loc[idx, 'Status'] = target_sf
                                else:
                                    klasemen_aktif.loc[idx, 'Status'] = "Finisher"
                                    klasemen_aktif.loc[idx, 'Gate'] = "-"
        st.divider()

    # ==========================================
    # FASE 3B: SEMI-FINAL
    # ==========================================
    if not qf_direct_to_final:
        sf_active_groups = sorted([s for s in klasemen_aktif['Status'].unique() if "Semi-Final" in str(s)])
        if sf_active_groups:
            st.header("3B. ⚔️ Fase 3B: Semi-Final")
            for sf_name in sf_active_groups:
                sf_sub = klasemen_aktif[klasemen_aktif['Status'] == sf_name].copy()
                sf_sub['Gate_Sort'] = pd.to_numeric(sf_sub['Gate'], errors='coerce').fillna(99)
                sf_sub = sf_sub.sort_values('Gate_Sort')
                
                if len(sf_sub) > 0:
                    st.markdown(f"**🔹 {sf_name}** ({len(sf_sub)} Rider)")
                    sf_options = ["-"] + [str(i) for i in range(1, len(sf_sub) + 1)]
                    col_cfg_sf = {
                        "Number plate": st.column_config.TextColumn("No. Plate", disabled=True),
                        "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
                        "Hasil Semi-Final": st.column_config.SelectboxColumn("Posisi Finish SF", options=sf_options),
                        "Gate": st.column_config.TextColumn("Gate", disabled=True)
                    }
                    edited_sf_sub = st.data_editor(sf_sub[['Number plate', 'Name', 'Hasil Semi-Final', 'Gate']], column_config=col_cfg_sf, hide_index=True, key=f"sf_{selected_kelas}_{sf_name}", use_container_width=True)
                    
                    for idx in edited_sf_sub.index:
                        hsf = str(edited_sf_sub.at[idx, 'Hasil Semi-Final']).strip()
                        klasemen_aktif.loc[idx, 'Hasil Semi-Final'] = hsf
                        df.loc[idx, 'Hasil Semi-Final'] = hsf
                        if hsf.isdigit():
                            pos = int(hsf)
                            if "Rookie/Beginner" in sf_name:
                                klasemen_aktif.loc[idx, 'Status'] = "Final Rookie" if pos <= 5 else ("Final Beginner" if "Beginner" in selected_piala else "Finisher")
                            else:
                                klasemen_aktif.loc[idx, 'Status'] = "Final Utama" if pos <= 5 else ("Final Novice" if "Novice" in selected_piala else "Finisher")
            st.divider()

    # Hitung Gate untuk Babak Final
    for target_final in FINAL_TIERS:
        mask = klasemen_aktif['Status'] == target_final
        if mask.sum() > 0:
            df_temp = klasemen_aktif[mask].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
            klasemen_aktif.loc[df_temp.index, 'Gate'] = [str(x) for x in range(1, len(df_temp) + 1)]

else:
    if len(klasemen_aktif) > 0:
        klasemen_aktif = klasemen_aktif.sort_values(by=['Total Point', 'M2_Num', 'M1_Num', 'Group'])
        for i, idx_r in enumerate(klasemen_aktif.index):
            t_idx = min(i // batas_gate, len(FINAL_TIERS) - 1)
            klasemen_aktif.loc[idx_r, 'Status'] = FINAL_TIERS[t_idx]
            klasemen_aktif.loc[idx_r, 'Gate'] = str((i % batas_gate) + 1)
        klasemen_aktif['Status_Moto'] = klasemen_aktif['Status'].astype(str)

# ==========================================
# FASE 4: FINAL & INPUT PODIUM
# ==========================================
# Filter KHUSUS: Hanya peserta yang statusnya SUDAH MASUK FINAL TIER yang dimunculkan di tabel Podium
df_final_active = klasemen_aktif[klasemen_aktif['Status'].isin(FINAL_TIERS)].copy()

if not df_final_active.empty:
    st.header("4. 🏆 Fase 4: Hasil Final & Input Podium")
    
    status_map = {t: i for i, t in enumerate(FINAL_TIERS)}
    df_final_active['Status_Order'] = df_final_active['Status'].map(status_map).fillna(99)
    df_final_active['Gate_Sort'] = pd.to_numeric(df_final_active['Gate'], errors='coerce').fillna(99)
    df_final_active = df_final_active.sort_values(by=['Status_Order', 'Gate_Sort'])

    pilihan_hasil = ["-", "Gugur/DNF"]
    for kat in selected_piala:
        for i in range(1, batas_gate + 1): 
            pilihan_hasil.append(f"Juara {i} {kat}")
    pilihan_hasil.append("Finisher")

    editor_columns_final = {
        "Status_Order": None, "Gate_Sort": None, "Hasil QF": None, "Hasil Repechage": None, "Hasil Semi-Final": None, "NO": None,
        "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
        "Name": st.column_config.TextColumn("Nama Rider", disabled=True), 
        "Status": st.column_config.TextColumn("Bracket Final", disabled=True),
        "Hasil Akhir": st.column_config.SelectboxColumn("🏅 Input Juara Podium", options=pilihan_hasil),
        "Gate": st.column_config.TextColumn("Gate Start", disabled=True)
    }

    edited_final = st.data_editor(
        df_final_active[['Number plate', 'Name', 'Status', 'Hasil Akhir', 'Gate']], 
        column_config=editor_columns_final, 
        hide_index=True, 
        key=f"final_{selected_kelas}", 
        use_container_width=True
    )
    for idx_f in edited_final.index:
        klasemen_aktif.loc[idx_f, 'Hasil Akhir'] = edited_final.at[idx_f, 'Hasil Akhir']
        df.loc[idx_f, 'Hasil Akhir'] = edited_final.at[idx_f, 'Hasil Akhir']
    db["saved_df"] = df
    st.write("---")

def extract_rank(hasil):
    hasil_str = str(hasil).strip()
    if pd.isna(hasil) or hasil_str == "-" or hasil_str == "None": return 999
    if "Gugur" in hasil_str or "DNF" in hasil_str: return 998
    base = 0
    if "Utama" in hasil_str: base = 0
    elif "Novice" in hasil_str: base = 100
    elif "Rookie" in hasil_str: base = 200
    elif "Beginner" in hasil_str: base = 300
    elif "Newbie" in hasil_str: base = 400
    elif "Finisher" in hasil_str: base = 800
    num = ''.join(filter(str.isdigit, hasil_str))
    return base + int(num) if num else 997

def prepare_block(df_filtered, block_type="MOTO"):
    df_filtered = df_filtered.copy()
    df_filtered['Gate_Sort'] = pd.to_numeric(df_filtered['Gate'], errors='coerce').fillna(99)
    
    if block_type == "FINAL":
        df_filtered['RankSort'] = df_filtered['Hasil Akhir'].apply(extract_rank)
        has_podium = (df_filtered['Hasil Akhir'] != "-").any()
        res = df_filtered.sort_values('RankSort').copy() if has_podium else df_filtered.sort_values('Gate_Sort').copy()
        res = res[['Name', 'Number plate', 'Team', 'Hasil Akhir', 'Gate']]
        res.columns = ['Nama Rider', 'No. Plate', 'Komunitas', 'Hasil Podium', 'Gate']
        res['Gate'] = res['Gate'].astype(str)
        return res
    elif block_type == "MOTO":
        cols_base = ['Gate M1', 'Gate M2', 'Name', 'Number plate', 'Team', 'M1', 'M2', 'Total Point', 'Status_Moto']
        cols_rename = ['Gate M1', 'Gate M2', 'Nama Rider', 'No. Plate', 'Komunitas', 'M1', 'M2', 'Total Poin', 'Remark / Status Lolos']
        res = df_filtered[cols_base].copy()
        res.columns = cols_rename
        res['Total Poin'] = res['Total Poin'].astype(int).astype(str)
        return res
    else:
        res = df_filtered.sort_values('Gate_Sort').copy()
        cols_base = ['Name', 'Number plate', 'Team', 'M1', 'M2', 'Total Point', 'Gate']
        cols_rename = ['Nama Rider', 'No. Plate', 'Komunitas', 'M1', 'M2', 'Total Poin', 'Gate']
        res = res[cols_base].copy()
        res.columns = cols_rename
        res['Total Poin'] = res['Total Poin'].astype(int).astype(str)
        res['Gate'] = res['Gate'].astype(str)
        return res

# KELOMPOKKAN TABEL SESUAI TAHAPAN TURNAMEN
tables_dict = {
    "🏁 Kualifikasi Moto": [],
    "🛟 Repechage": [],
    "⚡ Quarter-Final": [],
    "⚔️ Semi-Final": [],
    "🏆 Babak Final (Podium)": []
}

if not klasemen_aktif.empty:
    for g in grup_valid:
        df_g = klasemen_aktif[klasemen_aktif['Group'] == g].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
        tables_dict["🏁 Kualifikasi Moto"].append((f"MOTO - GRUP {g}", prepare_block(df_g, "MOTO")))
        
    df_b_rep = klasemen_aktif[klasemen_aktif.get('Status_Moto', '') == "Repechage"]
    if not df_b_rep.empty:
        tables_dict["🛟 Repechage"].append(("REPECHAGE", prepare_block(df_b_rep, "REPECHAGE")))
        
    for qf_name in [f"Quarter-Final {i}" for i in range(1, int(custom_qf_heats) + 1)]:
        df_b_qf = klasemen_aktif[klasemen_aktif['Status'] == qf_name]
        if not df_b_qf.empty:
            tables_dict["⚡ Quarter-Final"].append((qf_name.upper(), prepare_block(df_b_qf, "QF")))
            
    sf_list = [s for s in klasemen_aktif['Status'].unique() if "Semi-Final" in str(s)]
    for sf_name in sorted(sf_list):
        df_b_sf = klasemen_aktif[klasemen_aktif['Status'] == sf_name]
        if not df_b_sf.empty:
            tables_dict["⚔️ Semi-Final"].append((sf_name.upper(), prepare_block(df_b_sf, "SF")))
            
    for final_tier in FINAL_TIERS:
        df_b_f = klasemen_aktif[klasemen_aktif['Status'] == final_tier]
        if not df_b_f.empty:
            tables_dict["🏆 Babak Final (Podium)"].append((final_tier.upper(), prepare_block(df_b_f, "FINAL")))

# ==========================================
# TOMBOL AKSI: SIMPAN DRAFT, PUBLIKASI, & EXCEL
# ==========================================
col_draft, col_pub, col_dl = st.columns(3)

with col_draft:
    if st.button("💾 SIMPAN DRAFT TURNAMEN", use_container_width=True):
        draft_payload = {
            "event_name": db["event_name"],
            "logo_url": db["logo_url"],
            "df_records": df.to_dict(orient="records")
        }
        with open("draft_turnamen.json", "w") as f:
            json.dump(draft_payload, f)
        st.success("✅ Draft turnamen berhasil disimpan di server!")

with col_pub:
    if st.button("📢 SIMPAN & PUBLIKASI KE PENONTON", use_container_width=True):
        payload_data = {
            "kelas": selected_kelas,
            "tables_dict": {
                k: [(t_name, df_b.to_dict(orient="records")) for t_name, df_b in v]
                for k, v in tables_dict.items()
            }
        }
        db["live_payload"] = payload_data
        
        with open("live_standing.json", "w") as f:
            json.dump(payload_data, f)
            
        draft_payload = {
            "event_name": db["event_name"],
            "logo_url": db["logo_url"],
            "df_records": df.to_dict(orient="records")
        }
        with open("draft_turnamen.json", "w") as f:
            json.dump(draft_payload, f)
            
        st.success("✅ Berhasil dipublikasikan ke Live Score penonton!")

with col_dl:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet_excel = workbook.add_worksheet('Hasil Race')
        worksheet_excel.hide_gridlines(2)
        
        title_format = workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        current_row_excel = 0
        for tab_name, list_tables in tables_dict.items():
            for title_suffix, df_bracket in list_tables:
                title_text = f"{selected_kelas} {title_suffix}"
                num_cols = len(df_bracket.columns)
                worksheet_excel.merge_range(current_row_excel, 0, current_row_excel, num_cols - 1, title_text, title_format)
                current_row_excel += 1
                
                for col_num, value in enumerate(df_bracket.columns):
                    worksheet_excel.write(current_row_excel, col_num, value, header_format)
                current_row_excel += 1
                
                for row_data in df_bracket.values:
                    for col_num, value in enumerate(row_data):
                        worksheet_excel.write(current_row_excel, col_num, str(value) if pd.notnull(value) else "", data_format)
                    current_row_excel += 1
                current_row_excel += 1

    st.download_button(
        label="⬇️ DOWNLOAD EXCEL (.xlsx)", 
        data=output.getvalue(), 
        file_name=f"Hasil_{selected_kelas}.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )
