import streamlit as st
import pandas as pd
from io import BytesIO
import json
import os

st.set_page_config(page_title="Pushbike Race Scoring System", layout="wide")

FILE_LIVE_DATA = "live_standing.json"

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
    st.title("🏆 Live Standing - Pushbike Race")
    
    if st.button("🔄 Refresh Data Terbaru"):
        st.rerun()

    if os.path.exists(FILE_LIVE_DATA):
        try:
            with open(FILE_LIVE_DATA, "r") as f:
                payload = json.load(f)
            
            st.info(f"📢 **Kelas Terakhir Diperbarui:** {payload.get('kelas', '-')}")
            
            for block_title, data_table in payload.get('tables', []):
                st.markdown(f"#### 🏁 {block_title}")
                df_view = pd.DataFrame(data_table)
                st.dataframe(df_view, hide_index=True, use_container_width=True)
                st.write("")
        except Exception as e:
            st.error(f"Gagal memuat data live: {e}")
    else:
        st.warning("Belum ada data race yang dipublikasikan oleh panitia. Silakan tunggu update juri.")
    
    st.stop()

# ==========================================
# 2. TAMPILAN ADMIN / PANITIA (DILINDUNGI PIN)
# ==========================================
with st.sidebar:
    pin = st.text_input("Masukkan PIN Panitia:", type="password")
    if pin != "1234":  # Ganti "1234" dengan PIN pilihan Anda
        st.error("Masukkan PIN yang benar untuk menginput skor.")
        st.stop()

    st.success("✅ Terverifikasi sebagai Panitia")
    st.header("⚙️ Pengaturan Turnamen")
    batas_gate = st.number_input("Kapasitas Rider per Gate/Podium", min_value=2, max_value=12, value=4)
    kuota_default = st.number_input("Kuota Standar per Kelas", min_value=4, max_value=100, value=12)
    st.divider()
    
    st.header("📋 Pengaturan Publikasi")
    fase_tampilan = st.selectbox(
        "Fase Live Score yang Ditampilkan:",
        ["Otomatis (Ikuti Alur)", "Pembagian Grup (Start List)", "Hanya Moto", "Hanya Repechage", "Hanya Semi-Final", "Hanya Final", "Semua Fase (Summary Final)"]
    )
    st.divider()

st.title("🛠️ Panel Panitia - Scoring System")

uploaded_file = st.file_uploader("📂 Upload Data Peserta (File Excel .xlsx atau CSV)", type=["xlsx", "csv"])

if uploaded_file is None:
    st.info("Silakan unggah file data peserta untuk mulai mengolah nilai.")
    st.stop()

try:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
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
    
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

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
    edited_g = st.data_editor(df_g[cols_to_show], column_config=col_cfg, hide_index=True, key=f"moto_{g}", use_container_width=True)
    
    if mode_input_moto == "Fokus Input Moto 1 Saja":
        edited_g['M2'] = df_g['M2'].values
    elif mode_input_moto == "Fokus Input Moto 2 Saja":
        edited_g['M1'] = df_g['M1'].values
    
    m1_vals = [v for v in edited_g['M1'].astype(str) if v not in ["-", "DNS", "DNF", "nan", ""]]
    m2_vals = [v for v in edited_g['M2'].astype(str) if v not in ["-", "DNS", "DNF", "nan", ""]]
    
    if len(m1_vals) != len(set(m1_vals)): 
        moto_errors.append(f"Grup {g} - Moto 1: Ditemukan nomor posisi sama.")
    if len(m2_vals) != len(set(m2_vals)): 
        moto_errors.append(f"Grup {g} - Moto 2: Ditemukan nomor posisi sama.")
        
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

# ALUR LANJUTAN (REPECHAGE & SEMI FINAL JIKA GRUP > 2)
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
        st.info("ℹ️ Repechage dilewati (Jumlah grup genap).")
    elif len(rep_df) > 0:
        rep_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
        editor_columns_rep = {"NO": None, "Name": st.column_config.TextColumn("Nama Rider", disabled=True), "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), "Hasil Repechage": st.column_config.SelectboxColumn("Posisi Finish", options=rep_options)}
        edited_rep = st.data_editor(rep_df[['Number plate', 'Name', 'Hasil Repechage']], column_config=editor_columns_rep, hide_index=True, use_container_width=True)
        
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

    st.header("3. ⚔️ Fase 3: Balap Semi-Final")
    sf_options = ["-"] + [str(i) for i in range(1, batas_gate + 1)]
    sf_df = klasemen_aktif[klasemen_aktif['Status'].str.contains('Semi-Final', na=False)].copy().sort_values(['Status', 'Gate'])
    
    if len(sf_df) > 0:
        klasemen_aktif.loc[sf_df.index, 'Status_Asli_SF'] = klasemen_aktif.loc[sf_df.index, 'Status']
        editor_columns_sf = {"Status": st.column_config.TextColumn("Grup SF", disabled=True), "Gate": st.column_config.TextColumn("Gate", disabled=True), "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), "Name": st.column_config.TextColumn("Nama Rider", disabled=True), "Hasil Semi-Final": st.column_config.SelectboxColumn("Posisi Finish SF", options=sf_options)}
        edited_sf = st.data_editor(sf_df[['Status', 'Gate', 'Number plate', 'Name', 'Hasil Semi-Final']], column_config=editor_columns_sf, hide_index=True, use_container_width=True)
        
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
    st.info("ℹ️ Fase Repechage dilewati.")
    st.divider()

    st.header("3. ⚔️ Fase 3: Semi-Final")
    st.info("ℹ️ Fase Semi-Final dilewati. Langsung ke Final.")
    
    if len(klasemen_aktif) > 0:
        klasemen_aktif = klasemen_aktif.sort_values(by=['Total Point', 'M2_Num', 'M1_Num', 'Group'])
        klasemen_aktif['Rank Keseluruhan'] = range(1, len(klasemen_aktif) + 1)
        klasemen_aktif['Status'] = klasemen_aktif['Rank Keseluruhan'].apply(lambda r: "Final Utama" if r <= batas_gate else ("Final Novice" if r <= batas_gate*2 else "Final Rookie"))
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
    "Number plate": st.column_config.TextColumn("No. Plate", disabled=True), "Name": st.column_config.TextColumn("Nama Rider", disabled=True),
    "Status": st.column_config.TextColumn("Tiket / Bracket Final", disabled=True), "Gate": st.column_config.TextColumn("No. Gate", disabled=True),
    "Hasil Akhir": st.column_config.SelectboxColumn("🏅 Input Juara Podium", options=pilihan_hasil)
}

if len(klasemen_aktif) > 0:
    edited_final = st.data_editor(klasemen_aktif[['Number plate', 'Name', 'Status', 'Gate', 'Hasil Akhir']], column_config=editor_columns_final, hide_index=True, use_container_width=True)
    klasemen_aktif['Hasil Akhir'] = edited_final['Hasil Akhir']

st.write("---")

# PERSIAPAN BLOK DATA
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
        res = df_filtered.sort_values('RankSort').copy()
        res = res[['Name', 'Number plate', 'Team', 'Hasil Akhir']]
        res.columns = ['Nama Rider', 'No. Plate', 'Komunitas', 'Hasil Podium']
        return res
    else:
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

# TOMBOL PUBLIKASI & DOWNLOAD
col_pub, col_dl = st.columns(2)

with col_pub:
    if st.button("📢 SIMPAN & PUBLIKASI KE PENONTON", use_container_width=True):
        payload_data = {
            "kelas": selected_kelas,
            "tables": [(t_name, df_b.to_dict(orient="records")) for t_name, df_b in blocks_to_export]
        }
        with open(FILE_LIVE_DATA, "w") as f:
            json.dump(payload_data, f)
        st.success("✅ Berhasil dipublikasikan! Penonton sekarang dapat melihat tabel ini secara real-time.")

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
