import streamlit as st
import pandas as pd
from io import BytesIO
import json
import os

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
# DATABASE GLOBAL (BERTAHAN DI SERVER STREAMLIT)
# ==========================================
@st.cache_resource
def get_global_database():
    return {
        "live_payload": None,
        "saved_df": None,
        "selected_kelas": None,
        "event_name": "BHINNEKA PUSHBIKE GRAND PRIX 2026",
        "logo_url": ""
    }

db = get_global_database()

# ==========================================
# NAVIGASI ROLE / PENGGUNA
# ==========================================
with st.sidebar:
    st.header("👤 Akses Pengguna")
    role = st.radio("Pilih Akses:", ["👥 Penonton (Live Score)", "🔑 Panitia / Juri (Input Skor)"])
    st.divider()

# ==========================================
# 1. TAMPILAN KHUSUS PENONTON / MC
# ==========================================
if role == "👥 Penonton (Live Score)":
    # BANNER HEADER & LOGO
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
    st.header("⚙️ Pengaturan Turnamen")
    db["event_name"] = st.text_input("Nama Event / Judul Banner:", value=db.get("event_name", "BHINNEKA PUSHBIKE GRAND PRIX 2026"))
    db["logo_url"] = st.text_input("URL Link Logo Eksternal (Opsional):", value=db.get("logo_url", ""))
    
    batas_gate = st.number_input("Kapasitas Rider per Gate/Podium", min_value=2, max_value=12, value=4)
    kuota_default = st.number_input("Kuota Standar per Kelas", min_value=4, max_value=100, value=12)
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

for col in ['Group', 'Team', 'Number plate', 'M1', 'M2', 'Hasil Repechage', 'Hasil Semi-Final', 'Hasil Akhir']:
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

klasemen_aktif['Status_Asli_Rep'] = "-"
klasemen_aktif['Status_Asli_SF'] = "-"

edited_rep, edited_sf, edited_final = None, None, None

# LOGIKA PEMBAGIAN ALUR JIKA GRUP > 2
if jumlah_grup_aktif > 2:
    klasemen_aktif = klasemen_aktif.sort_values(by=['Group', 'Total Point', 'M2_Num', 'M1_Num'])
    klasemen_aktif['Rank di Grup'] = klasemen_aktif.groupby('Group').cumcount() + 1
    klasemen_aktif['Status'], klasemen_aktif['Gate'] = "Final Rookie", 99
    
    sf1_riders, sf2_riders, rep_riders, rookie_riders = [], [], [], []
    quota_sf_per_group = (batas_gate * 2) // jumlah_grup_aktif
    
    for idx_grup, grup_name in enumerate(grup_valid):
        for rank in range(1, quota_sf_per_group + 1):
            r = klasemen_aktif[(klasemen_aktif['Group'] == grup_name) & (klasemen_aktif['Rank di Grup'] == rank)]
            if not r.empty:
                if (idx_grup + rank) % 2 != 0: sf1_riders.append(r.index[0])
                else: sf2_riders.append(r.index[0])
        
        if jumlah_grup_aktif % 2 != 0:
            r_rep = klasemen_aktif[(klasemen_aktif['Group'] == grup_name) & (klasemen_aktif['Rank di Grup'] == quota_sf_per_group + 1)]
            if not r_rep.empty: rep_riders.append(r_rep.index[0])
            r_rookie = klasemen_aktif[(klasemen_aktif['Group'] == grup_name) & (klasemen_aktif['Rank di Grup'] > quota_sf_per_group + 1)]
            if not r_rookie.empty: rookie_riders.extend(r_rookie.index.tolist())
        else:
            r_rookie = klasemen_aktif[(klasemen_aktif['Group'] == grup_name) & (klasemen_aktif['Rank di Grup'] > quota_sf_per_group)]
            if not r_rookie.empty: rookie_riders.extend(r_rookie.index.tolist())
            
    for idx, r_idx in enumerate(sf1_riders): klasemen_aktif.at[r_idx, 'Status'], klasemen_aktif.at[r_idx, 'Gate'] = 'Semi-Final 1', idx + 1
    for idx, r_idx in enumerate(sf2_riders): klasemen_aktif.at[r_idx, 'Status'], klasemen_aktif.at[r_idx, 'Gate'] = 'Semi-Final 2', idx + 1
    for idx, r_idx in enumerate(rep_riders): klasemen_aktif.at[r_idx, 'Status'], klasemen_aktif.at[r_idx, 'Gate'] = 'Repechage', idx + 1
    for idx, r_idx in enumerate(rookie_riders): klasemen_aktif.at[r_idx, 'Status'], klasemen_aktif.at[r_idx, 'Gate'] = 'Final Rookie', idx + 1

    klasemen_aktif['Status_Asli_Rep'] = klasemen_aktif['Status']

    st.header("2. 🛟 Fase 2: Repechage")
    rep_df = klasemen_aktif[klasemen_aktif['Status'] == 'Repechage'].copy().sort_values('Gate')
    
    if jumlah_grup_aktif % 2 == 0:
        st.info("ℹ️ Repechage dilewati (Grup genap).")
    elif len(rep_df) > 0:
        rep_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
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
            if hr == '1': klasemen_aktif.at[idx, 'Status'] = 'Semi-Final 2'
            elif hr == '2': klasemen_aktif.at[idx, 'Status'] = 'Semi-Final 1'
            elif hr.isdigit() and int(hr) >= 3: klasemen_aktif.at[idx, 'Status'] = 'Final Rookie'

        for target_status in ['Semi-Final 1', 'Semi-Final 2', 'Final Rookie']:
            mask = klasemen_aktif['Status'] == target_status
            if mask.sum() > 0:
                df_temp = klasemen_aktif[mask].sort_values(by=['Total Point', 'M2_Num', 'M1_Num'])
                klasemen_aktif.loc[df_temp.index, 'Gate'] = range(1, len(df_temp) + 1)

    st.divider()

    st.header("3. ⚔️ Fase 3: Semi-Final")
    sf_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
    sf_df = klasemen_aktif[klasemen_aktif['Status'].str.contains('Semi-Final', na=False)].copy().sort_values(['Status', 'Gate'])
    
    if len(sf_df) > 0:
        klasemen_aktif.loc[sf_df.index, 'Status_Asli_SF'] = klasemen_aktif.loc[sf_df.index, 'Status']
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
                klasemen_aktif.at[idx, 'Status'] = 'Final Utama' if int(hsf) <= 2 else 'Final Novice'
                
        klasemen_aktif['SF_Pos_Num'] = pd.to_numeric(klasemen_aktif['Hasil Semi-Final'], errors='coerce').fillna(99)
        
        for target_final in ['Final Utama', 'Final Novice']:
            mask = klasemen_aktif['Status'] == target_final
            if mask.sum() > 0:
                df_temp = klasemen_aktif[mask].sort_values(by=['SF_Pos_Num', 'Total Point', 'M2_Num', 'M1_Num'])
                klasemen_aktif.loc[df_temp.index, 'Gate'] = range(1, len(df_temp) + 1)
else:
    st.header("2. 🛟 Fase 2: Repechage")
    st.info("ℹ️ Repechage dilewati.")
    st.divider()

    st.header("3. ⚔️ Fase 3: Semi-Final")
    st.info("ℹ️ Semi-Final dilewati.")
    
    # KETIKA GRUP <= 2: LANGSUNG GENERATE GATE FINAL BERDASARKAN TOTAL POIN MOTO
    if len(klasemen_aktif) > 0:
        klasemen_aktif = klasemen_aktif.sort_values(by=['Total Point', 'M2_Num', 'M1_Num', 'Group'])
        klasemen_aktif['Rank Keseluruhan'] = range(1, len(klasemen_aktif) + 1)
        klasemen_aktif['Status'] = klasemen_aktif['Rank Keseluruhan'].apply(
            lambda r: "Final Utama" if r <= batas_gate else ("Final Novice" if r <= batas_gate*2 else "Final Rookie")
        )
        klasemen_aktif['Gate'] = klasemen_aktif.groupby('Status').cumcount() + 1

st.divider()

# FASE 4: FINAL
st.header("4. 🏆 Fase 4: Hasil Final & Input Podium")

status_order = {"Final Utama": 1, "Final Novice": 2, "Final Rookie": 3, "Semi-Final 1": 4, "Semi-Final 2": 5, "Repechage": 6}
if 'Status' in klasemen_aktif.columns:
    klasemen_aktif['Status_Order'] = klasemen_aktif['Status'].map(status_order).fillna(7)
    klasemen_aktif = klasemen_aktif.sort_values(by=['Status_Order', 'Gate'])

pilihan_hasil = ["-", "Gugur/DNF"]
for kat in ["Utama", "Novice", "Rookie", "Harapan"]:
    for i in range(1, batas_gate + 1): pilihan_hasil.append(f"Juara {i} {kat}")
        
editor_columns_final = {
    "Status_Order": None, "SF_Pos_Num": None, "Hasil Repechage": None, "Hasil Semi-Final": None, "NO": None,
    "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), 
    "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
    "Status": st.column_config.TextColumn("Tiket / Bracket Final", disabled=True),
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
    elif "Harapan" in hasil_str: base = 300
    num = ''.join(filter(str.isdigit, hasil_str))
    return base + int(num) if num else 997

def prepare_block(df_filtered, block_type="MOTO"):
    if block_type == "FINAL":
        df_filtered['RankSort'] = df_filtered['Hasil Akhir'].apply(extract_rank)
        has_podium = (df_filtered['Hasil Akhir'] != "-").any()
        if has_podium:
            res = df_filtered.sort_values('RankSort').copy()
        else:
            res = df_filtered.sort_values('Gate').copy()
            
        # Gate diletakkan di kolom paling akhir
        res = res[['Name', 'Number plate', 'Team', 'Hasil Akhir', 'Gate']]
        res.columns = ['Nama Rider', 'No. Plate', 'Komunitas', 'Hasil Podium', 'Gate']
        res['Gate'] = res['Gate'].astype(str)
        return res
    else:
        # Gate diletakkan di kolom paling akhir
        cols_base = ['Name', 'Number plate', 'Team', 'M1', 'M2', 'Total Point', 'Status', 'Gate']
        cols_rename = ['Nama Rider', 'No. Plate', 'Komunitas', 'M1', 'M2', 'Total Poin', 'Bracket Final', 'Gate']
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
        
    df_b_rep = klasemen_aktif[klasemen_aktif['Status_Asli_Rep'] == "Repechage"].sort_values('Gate')
    if not df_b_rep.empty:
        b_rep_prepared = prepare_block(df_b_rep, "REPECHAGE")
        b_rep_prepared['Bracket Final'] = "Repechage"
        blocks_to_export.append(("REPECHAGE", b_rep_prepared))
        
    for b in ["Semi-Final 1", "Semi-Final 2"]:
        df_b_sf = klasemen_aktif[klasemen_aktif['Status_Asli_SF'] == b].sort_values('Gate')
        if not df_b_sf.empty:
            b_sf_prepared = prepare_block(df_b_sf, "SEMI-FINAL")
            b_sf_prepared['Bracket Final'] = b
            blocks_to_export.append((b.upper(), b_sf_prepared))
            
    for b in ["Final Utama", "Final Novice", "Final Rookie", "Final Harapan"]:
        df_b_f = klasemen_aktif[klasemen_aktif['Status'] == b]
        if not df_b_f.empty:
            blocks_to_export.append((b.upper(), prepare_block(df_b_f, "FINAL")))

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
        st.success("✅ Berhasil dipublikasikan! Gate Start & Klasemen sekarang terlihat lengkap di kolom paling akhir.")

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
