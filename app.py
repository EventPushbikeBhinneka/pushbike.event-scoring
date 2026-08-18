import streamlit as st
import pandas as pd
from io import BytesIO
import json
import os
import math

st.set_page_config(page_title="Pushbike Race Scoring System", page_icon="🚲", layout="wide")

# ==========================================
# CUSTOM CSS UNTUK TAMPILAN PREMIUM
# ==========================================
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
# DATABASE GLOBAL
# ==========================================
@st.cache_resource
def get_global_database():
    return {
        "live_payload": None,
        "saved_df": None,
        "selected_kelas": None,
        "event_name": "BHINNEKA RACING FEST",
        "logo_url": ""
    }

db = get_global_database()

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
            try:
                st.image(db["logo_url"], width=120)
            except:
                st.markdown("## 🚴‍♂️")
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

    if live_data and live_data.get('tables'):
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0; color:#1e3c72;">🏁 KELAS: {live_data.get('kelas', '-')}</h4>
            <span style="font-size:0.85rem; color:#666;">Status: Hasil Resmi Terverifikasi Juri</span>
        </div>
        """, unsafe_allow_html=True)
        
        for block_title, data_table in live_data.get('tables', []):
            st.markdown(f"#### 📋 {block_title}")
            df_view = pd.DataFrame(data_table)
            st.dataframe(df_view, hide_index=True, use_container_width=True)
            st.write("")
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
    
    st.header("🛠️ Kustom Format & Bagan")
    batas_gate = st.number_input("Kapasitas Rider per Gate / Podium", min_value=2, max_value=12, value=4)
    
    skema_alur = st.selectbox(
        "Skema Babak Gugur:",
        ["Otomatis (Berdasarkan Jumlah Peserta)", "Gunakan Quarter-Final (QF -> SF -> Final)", "Langsung Semi-Final (SF -> Final)", "Langsung Multi-Final (Tanpa QF/SF)"]
    )
    
    custom_qf_quota = st.number_input("Rider Teratas per Grup ke Babak Lolos (QF/SF):", min_value=1, max_value=8, value=5)
    enable_repechage = st.checkbox("Aktifkan Jalur Repechage (Kesempatan Terakhir)", value=True)
    
    st.divider()
    
    if st.button("🗑️ Reset Semua Data Server", help="Mulai turnamen baru dari awal"):
        db["live_payload"] = None
        db["saved_df"] = None
        if os.path.exists("live_standing.json"):
            os.remove("live_standing.json")
        st.rerun()

st.title("🛠️ Panel Panitia - Scoring System")

uploaded_file = st.file_uploader("📂 Upload Data Peserta (.xlsx / .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            db["saved_df"] = pd.read_csv(uploaded_file)
        else:
            db["saved_df"] = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Gagal membaca file upload: {e}")

if db["saved_df"] is None:
    st.info("Silakan unggah file data peserta terlebih dahulu.")
    st.stop()

df = db["saved_df"].copy()
df.columns = df.columns.str.strip()

for col in ['Group', 'Team', 'Number plate', 'M1', 'M2', 'Hasil QF', 'Hasil Repechage', 'Hasil Semi-Final', 'Hasil Akhir']:
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
    st.warning("Kolom 'Kelas' tidak ditemukan.")
    st.stop()

selected_kelas = st.selectbox("Pilih Kelas:", kelas_list)
df_kelas = df[df['Kelas'] == selected_kelas].copy()

grup_list = sorted([g for g in df_kelas['Group'].unique() if str(g).strip() not in ["", "-", "NAN", "None", "nan"]])

mode_input_moto = st.radio(
    "🚥 Mode Fokus Input:", 
    ["Tampilkan Semua (M1 & M2)", "Fokus Input Moto 1 Saja", "Fokus Input Moto 2 Saja"], 
    horizontal=True
)

edited_motos = []
moto_errors = []

for g in grup_list:
    df_g = df_kelas[df_kelas['Group'] == g].copy()
    jml_rider = len(df_g)
    
    df_g['Gate M1'] = range(1, jml_rider + 1)
    df_g['Gate M2'] = df_g['Gate M1'].apply(lambda x: x+1 if x%2!=0 and x<jml_rider else (x-1 if x%2==0 else x))
    df_g['Gate M1'] = df_g['Gate M1'].astype(str)
    df_g['Gate M2'] = df_g['Gate M2'].astype(str)
    
    options = ["-"] + [str(i) for i in range(1, jml_rider + 1)] + ["DNS", "DNF"]
    
    col_cfg = {
        "NO": st.column_config.TextColumn("NO", disabled=True),
        "Number plate": st.column_config.TextColumn("No. Plate", disabled=True),
        "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
        "Team": st.column_config.TextColumn("Komunitas", disabled=True),
        "Gate M1": st.column_config.TextColumn("Gate M1", disabled=True),
        "Gate M2": st.column_config.TextColumn("Gate M2", disabled=True),
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
klasemen.update(edited_df_moto[['M1', 'M2']])
klasemen['M1_Num'] = edited_df_moto['M1_Num']
klasemen['M2_Num'] = edited_df_moto['M2_Num']
klasemen['Total Point'] = edited_df_moto['Total Point']

klasemen_aktif = klasemen[klasemen['Total Point'] > 0].copy()
grup_valid = sorted([g for g in klasemen_aktif['Group'].unique() if str(g) not in ["", "-", "NAN"]])
jumlah_grup_aktif = len(grup_valid)
total_peserta_aktif = len(klasemen_aktif)

# DETEKSI ALUR (QF vs SF vs Direct Final)
use_qf = False
if skema_alur == "Gunakan Quarter-Final (QF -> SF -> Final)":
    use_qf = True
elif skema_alur == "Otomatis (Berdasarkan Jumlah Peserta)" and total_peserta_aktif >= 36:
    use_qf = True

edited_rep, edited_qf, edited_sf, edited_final = None, None, None, None

# DAFTAR TIER MULTI-FINAL SECARA BERURUTAN
FINAL_TIERS = ["Final Utama", "Final Novice", "Final Rookie", "Final Beginner", "Final Newbie", "Final Harapan"]

if total_peserta_aktif > 0 and skema_alur != "Langsung Multi-Final (Tanpa QF/SF)":
    klasemen_aktif = klasemen_aktif.sort_values(by=['Group', 'Total Point', 'M2_Num', 'M1_Num'])
    klasemen_aktif['Rank di Grup'] = klasemen_aktif.groupby('Group').cumcount() + 1
    
    pass_riders, rep_riders, rest_riders = [], [], []
    quota = custom_qf_quota
    
    for g_name in grup_valid:
        g_df = klasemen_aktif[klasemen_aktif['Group'] == g_name]
        p_list = g_df[g_df['Rank di Grup'] <= quota].index.tolist()
        pass_riders.extend(p_list)
        
        if enable_repechage:
            r_list = g_df[g_df['Rank di Grup'] == quota + 1].index.tolist()
            rep_riders.extend(r_list)
            rem_list = g_df[g_df['Rank di Grup'] > quota + 1].index.tolist()
            rest_riders.extend(rem_list)
        else:
            rem_list = g_df[g_df['Rank di Grup'] > quota].index.tolist()
            rest_riders.extend(rem_list)
            
    # BAGIKAN SISA RIDER KE FINAL TIER (NOVICE, ROOKIE, BEGINNER, NEWBIE)
    if rest_riders:
        df_rest = klasemen_aktif.loc[rest_riders].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
        tier_start_idx = 2 # Mulai dari Rookie jika jalur utama menuju Utama & Novice
        for i, idx_r in enumerate(df_rest.index):
            tier_idx = min(tier_start_idx + (i // batas_gate), len(FINAL_TIERS) - 1)
            klasemen_aktif.at[idx_r, 'Status'] = FINAL_TIERS[tier_idx]
            klasemen_aktif.at[idx_r, 'Gate'] = (i % batas_gate) + 1

    # PEMBAGIAN BABAK LOLOS
    if use_qf:
        # QUARTER FINAL (DIBAGI KE QF 1, QF 2, QF 3, QF 4)
        for i, idx_r in enumerate(pass_riders):
            qf_num = (i % 4) + 1
            klasemen_aktif.at[idx_r, 'Status'] = f"Quarter-Final {qf_num}"
            klasemen_aktif.at[idx_r, 'Gate'] = (i // 4) + 1
            
        if rep_riders:
            for i, idx_r in enumerate(rep_riders):
                klasemen_aktif.at[idx_r, 'Status'] = "Repechage"
                klasemen_aktif.at[idx_r, 'Gate'] = i + 1
    else:
        # SEMI FINAL LANGSUNG (SF 1 & SF 2)
        for i, idx_r in enumerate(pass_riders):
            sf_num = (i % 2) + 1
            klasemen_aktif.at[idx_r, 'Status'] = f"Semi-Final {sf_num}"
            klasemen_aktif.at[idx_r, 'Gate'] = (i // 2) + 1
            
        if rep_riders:
            for i, idx_r in enumerate(rep_riders):
                klasemen_aktif.at[idx_r, 'Status'] = "Repechage"
                klasemen_aktif.at[idx_r, 'Gate'] = i + 1

    # ==========================================
    # FASE 2: REPECHAGE
    # ==========================================
    rep_df = klasemen_aktif[klasemen_aktif['Status'] == 'Repechage'].copy().sort_values('Gate')
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
            klasemen_aktif.at[idx, 'Hasil Repechage'] = hr
            if hr.isdigit():
                pos = int(hr)
                if use_qf:
                    if pos <= 4: klasemen_aktif.at[idx, 'Status'] = f"Quarter-Final {pos}"
                    else: klasemen_aktif.at[idx, 'Status'] = "Final Rookie"
                else:
                    if pos == 1: klasemen_aktif.at[idx, 'Status'] = "Semi-Final 1"
                    elif pos == 2: klasemen_aktif.at[idx, 'Status'] = "Semi-Final 2"
                    else: klasemen_aktif.at[idx, 'Status'] = "Final Rookie"
        st.divider()

    # ==========================================
    # FASE 3A: QUARTER FINAL (JIKA DIKATIFKAN)
    # ==========================================
    if use_qf:
        st.header("3. ⚡ Fase 3A: Quarter-Final (QF 1 - 4)")
        qf_df = klasemen_aktif[klasemen_aktif['Status'].str.startswith('Quarter-Final', na=False)].copy().sort_values(['Status', 'Gate'])
        if len(qf_df) > 0:
            qf_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
            editor_columns_qf = {
                "Status": st.column_config.TextColumn("Grup QF", disabled=True), 
                "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
                "Name": st.column_config.TextColumn("Nama Rider", disabled=True), 
                "Hasil QF": st.column_config.SelectboxColumn("Posisi Finish QF", options=qf_options),
                "Gate": st.column_config.TextColumn("Gate", disabled=True)
            }
            edited_qf = st.data_editor(qf_df[['Status', 'Number plate', 'Name', 'Hasil QF', 'Gate']], column_config=editor_columns_qf, hide_index=True, key=f"qf_{selected_kelas}", use_container_width=True)
            
            for idx in edited_qf.index:
                hqf = str(edited_qf.at[idx, 'Hasil QF']).strip()
                klasemen_aktif.at[idx, 'Hasil QF'] = hqf
                if hqf.isdigit():
                    pos = int(hqf)
                    # 2 Besar ke SF, sisanya ke Final Novice / Rookie
                    if pos <= 2:
                        klasemen_aktif.at[idx, 'Status'] = "Semi-Final 1" if "1" in str(edited_qf.at[idx, 'Status']) or "3" in str(edited_qf.at[idx, 'Status']) else "Semi-Final 2"
                    else:
                        klasemen_aktif.at[idx, 'Status'] = "Final Novice" if pos == 3 else "Final Rookie"
            st.divider()

    # ==========================================
    # FASE 3B: SEMI-FINAL
    # ==========================================
    st.header("3B. ⚔️ Fase 3B: Semi-Final (SF 1 & 2)")
    sf_df = klasemen_aktif[klasemen_aktif['Status'].str.startswith('Semi-Final', na=False)].copy().sort_values(['Status', 'Gate'])
    if len(sf_df) > 0:
        sf_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
        editor_columns_sf = {
            "Status": st.column_config.TextColumn("Grup SF", disabled=True), 
            "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
            "Name": st.column_config.TextColumn("Nama Rider", disabled=True), 
            "Hasil Semi-Final": st.column_config.SelectboxColumn("Posisi Finish SF", options=sf_options),
            "Gate": st.column_config.TextColumn("Gate", disabled=True)
        }
        edited_sf = st.data_editor(sf_df[['Status', 'Number plate', 'Name', 'Hasil Semi-Final', 'Gate']], column_config=editor_columns_sf, hide_index=True, key=f"sf_{selected_kelas}", use_container_width=True)
        
        for idx in edited_sf.index:
            hsf = str(edited_sf.at[idx, 'Hasil Semi-Final']).strip()
            klasemen_aktif.at[idx, 'Hasil Semi-Final'] = hsf
            if hsf.isdigit():
                pos = int(hsf)
                # 2 Terdepan SF ke Final Utama, sisanya ke Final Novice
                klasemen_aktif.at[idx, 'Status'] = 'Final Utama' if pos <= 2 else 'Final Novice'
                
        # Re-index gate untuk Final Utama & Novice
        for target_final in ['Final Utama', 'Final Novice']:
            mask = klasemen_aktif['Status'] == target_final
            if mask.sum() > 0:
                df_temp = klasemen_aktif[mask].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
                klasemen_aktif.loc[df_temp.index, 'Gate'] = range(1, len(df_temp) + 1)
        st.divider()

else:
    # FORMAT LANGSUNG MULTI-FINAL (BAGI MERATA SESUAI URUTAN POIN)
    if len(klasemen_aktif) > 0:
        klasemen_aktif = klasemen_aktif.sort_values(by=['Total Point', 'M2_Num', 'M1_Num', 'Group'])
        for i, idx_r in enumerate(klasemen_aktif.index):
            tier_idx = min(i // batas_gate, len(FINAL_TIERS) - 1)
            klasemen_aktif.at[idx_r, 'Status'] = FINAL_TIERS[tier_idx]
            klasemen_aktif.at[idx_r, 'Gate'] = (i % batas_gate) + 1

# ==========================================
# FASE 4: FINAL & INPUT PODIUM
# ==========================================
st.header("4. 🏆 Fase 4: Hasil Final & Input Podium")

status_map = {t: i for i, t in enumerate(FINAL_TIERS)}
if 'Status' in klasemen_aktif.columns:
    klasemen_aktif['Status_Order'] = klasemen_aktif['Status'].map(status_map).fillna(99)
    klasemen_aktif = klasemen_aktif.sort_values(by=['Status_Order', 'Gate'])

pilihan_hasil = ["-", "Gugur/DNF"]
for kat in ["Utama", "Novice", "Rookie", "Beginner", "Newbie", "Harapan"]:
    for i in range(1, batas_gate + 1): 
        pilihan_hasil.append(f"Juara {i} {kat}")
        
editor_columns_final = {
    "Status_Order": None, "Hasil QF": None, "Hasil Repechage": None, "Hasil Semi-Final": None, "NO": None,
    "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
    "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
    "Status": st.column_config.TextColumn("Bracket Final", disabled=True),
    "Hasil Akhir": st.column_config.SelectboxColumn("🏅 Input Juara Podium", options=pilihan_hasil),
    "Gate": st.column_config.TextColumn("Gate Start", disabled=True)
}

if len(klasemen_aktif) > 0:
    edited_final = st.data_editor(
        klasemen_aktif[['Number plate', 'Name', 'Status', 'Hasil Akhir', 'Gate']], 
        column_config=editor_columns_final, 
        hide_index=True, 
        key=f"final_{selected_kelas}", 
        use_container_width=True
    )
    klasemen_aktif['Hasil Akhir'] = edited_final['Hasil Akhir']

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
    elif "Harapan" in hasil_str: base = 500
    num = ''.join(filter(str.isdigit, hasil_str))
    return base + int(num) if num else 997

def prepare_block(df_filtered, block_type="MOTO"):
    if block_type == "FINAL":
        df_filtered['RankSort'] = df_filtered['Hasil Akhir'].apply(extract_rank)
        has_podium = (df_filtered['Hasil Akhir'] != "-").any()
        res = df_filtered.sort_values('RankSort').copy() if has_podium else df_filtered.sort_values('Gate').copy()
        res = res[['Name', 'Number plate', 'Team', 'Hasil Akhir', 'Gate']]
        res.columns = ['Nama Rider', 'No. Plate', 'Komunitas', 'Hasil Podium', 'Gate']
        res['Gate'] = res['Gate'].astype(str)
        return res
    else:
        cols_base = ['Name', 'Number plate', 'Team', 'M1', 'M2', 'Total Point', 'Status', 'Gate']
        cols_rename = ['Nama Rider', 'No. Plate', 'Komunitas', 'M1', 'M2', 'Total Poin', 'Bracket', 'Gate']
        res = df_filtered[cols_base].copy()
        res.columns = cols_rename
        res['Total Poin'] = res['Total Poin'].astype(int).astype(str)
        res['Gate'] = res['Gate'].astype(str)
        return res

blocks_to_export = []

if not klasemen_aktif.empty:
    for g in grup_valid:
        df_g = klasemen_aktif[klasemen_aktif['Group'] == g].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
        blocks_to_export.append((f"MOTO - GRUP {g}", prepare_block(df_g, "MOTO")))
        
    df_b_rep = klasemen_aktif[klasemen_aktif['Status'] == "Repechage"].sort_values('Gate')
    if not df_b_rep.empty:
        blocks_to_export.append(("REPECHAGE", prepare_block(df_b_rep, "REPECHAGE")))
        
    for qf_name in [f"Quarter-Final {i}" for i in range(1, 5)]:
        df_b_qf = klasemen_aktif[klasemen_aktif['Status'] == qf_name].sort_values('Gate')
        if not df_b_qf.empty:
            blocks_to_export.append((qf_name.upper(), prepare_block(df_b_qf, "QF")))
            
    for sf_name in ["Semi-Final 1", "Semi-Final 2"]:
        df_b_sf = klasemen_aktif[klasemen_aktif['Status'] == sf_name].sort_values('Gate')
        if not df_b_sf.empty:
            blocks_to_export.append((sf_name.upper(), prepare_block(df_b_sf, "SF")))
            
    for final_tier in FINAL_TIERS:
        df_b_f = klasemen_aktif[klasemen_aktif['Status'] == final_tier]
        if not df_b_f.empty:
            blocks_to_export.append((final_tier.upper(), prepare_block(df_b_f, "FINAL")))

# TOMBOL PUBLIKASI
col_pub, col_dl = st.columns(2)

with col_pub:
    if st.button("📢 SIMPAN & PUBLIKASI KE PENONTON", use_container_width=True):
        payload_data = {
            "kelas": selected_kelas,
            "tables": [(t_name, df_b.to_dict(orient="records")) for t_name, df_b in blocks_to_export]
        }
        db["live_payload"] = payload_data
        with open("live_standing.json", "w") as f:
            json.dump(payload_data, f)
        st.success("✅ Berhasil dipublikasikan! Format Bagan & Gate Start telah disesuaikan.")

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
        for title_suffix, df_bracket in blocks_to_export:
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
