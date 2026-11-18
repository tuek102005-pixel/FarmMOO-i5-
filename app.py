import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from supabase import create_client

st.set_page_config(page_title="ระบบจัดการหมูแม่พันธุ์", layout="wide")
st.title("🐖 ระบบจัดการข้อมูลสุขภาพฟาร์มหมูแม่พันธุ์ (Supabase)")
st.divider()

# ----------------- 1. เชื่อมต่อ Supabase -----------------
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบไฟล์ secrets.toml")
    st.stop()

# --- ฟังก์ชันโหลดข้อมูล ---
def load_sow_data():
    res = supabase.table("sow_data").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["Sow_ID", "Breed", "Entry_Date", "Parity", "Status", "Exit_Date", "Exit_Reason", "version"])
    df.fillna({"Exit_Date": "", "Exit_Reason": "", "version": 1}, inplace=True)
    df["version"] = df["version"].astype(int)
    df = df.sort_values(by="Sow_ID", ascending=True).reset_index(drop=True)
    return df

def load_production_data():
    res = supabase.table("production_data").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        cols = ["Record_ID", "Sow_ID", "Parity_Num", "Breed_Date", "Expected_Heat", "Expected_Farrow", "Sire_ID", "Breed_Count", "Farrow_Date", "Total_Born", "Born_Alive", "Stillborn", "Mummy", "Birth_Weight", "Wean_Date", "Weaned_Pigs", "Wean_Weight", "version"]
        return pd.DataFrame(columns=cols)
    df.fillna({
        "Farrow_Date": "", "Wean_Date": "", "Expected_Heat": "", "Expected_Farrow": "",
        "Total_Born": 0, "Born_Alive": 0, "Stillborn": 0, "Mummy": 0, "Birth_Weight": 0.0,
        "Weaned_Pigs": 0, "Wean_Weight": 0.0, "version": 1
    }, inplace=True)
    df["version"] = df["version"].astype(int)
    return df

def load_health_data():
    res = supabase.table("health_records").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["Record_ID", "Sow_ID", "Record_Date", "Category", "Detail", "Treatment", "Amount_CC", "Withdrawal_Days", "version"])
    df.fillna({"Treatment": "", "Amount_CC": 0.0, "Withdrawal_Days": 0, "version": 1}, inplace=True)
    df["version"] = df["version"].astype(int)
    return df

def load_zone_feed_data():
    res = supabase.table("zone_feed_records").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["Record_ID", "Record_Date", "Zone_Name", "Feed_Type", "Amount_KG", "version"])
    df.fillna({"version": 1}, inplace=True)
    return df

def load_batch_health_data():
    res = supabase.table("batch_health_records").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["Record_ID", "Record_Date", "Target_Group", "Vaccine_Name", "Lot_Number", "version"])
    df.fillna({"version": 1}, inplace=True)
    return df

sow_df = load_sow_data()
prod_df = load_production_data()
health_df = load_health_data()
zone_feed_df = load_zone_feed_data()
batch_health_df = load_batch_health_data()

# ----------------- 2. Dashboard (ภาพรวมฟาร์ม) -----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 ภาพรวมฟาร์ม (Dashboard)", 
    "📋 จัดการข้อมูลรายตัว (Profile)", 
    "📝 บันทึกข้อมูลรวม (โซน/ฝูง)", 
    "➕ เพิ่มแม่พันธุ์ใหม่", 
    "💀 ทะเบียนคัดทิ้ง/ตาย"
])

with tab1:
    st.subheader("ข้อมูลสรุปประสิทธิภาพแม่พันธุ์ประจำปี (Sow Productivity KPIs)")
    thai_time = datetime.utcnow() + timedelta(hours=7) 
    current_date_str = thai_time.strftime("%d %B %Y")
    st.markdown(f"📅 **วันที่ปัจจุบัน:** {current_date_str}")
    
    if not sow_df.empty and not prod_df.empty:
        active_sows_df = sow_df[sow_df['Status'] != "คัดทิ้ง/ตาย"]
        dead_sows_df = sow_df[sow_df['Status'] == "คัดทิ้ง/ตาย"]
        total_active_sows = len(active_sows_df)
        total_dead = len(dead_sows_df)
        
        farrowed_records = prod_df[(prod_df['Farrow_Date'] != "") & (prod_df['Farrow_Date'].notna())]
        weaned_records = prod_df[(prod_df['Wean_Date'] != "") & (prod_df['Wean_Date'].notna())]
        
        total_farrowed_litters = len(farrowed_records)
        total_weaned_litters = len(weaned_records)
        
        lsy = total_farrowed_litters / total_active_sows if total_active_sows > 0 else 0
        
        sum_born_alive = farrowed_records['Born_Alive'].astype(float).sum() if not farrowed_records.empty else 0
        avg_born_alive = sum_born_alive / total_farrowed_litters if total_farrowed_litters > 0 else 0
        
        sum_weaned = weaned_records['Weaned_Pigs'].astype(float).sum() if not weaned_records.empty else 0
        avg_weaned = sum_weaned / total_weaned_litters if total_weaned_litters > 0 else 0
        psy = lsy * avg_weaned
        
        if not weaned_records.empty:
            born_alive_for_weaned = weaned_records['Born_Alive'].astype(float).sum()
            survival_rate = (sum_weaned / born_alive_for_weaned * 100) if born_alive_for_weaned > 0 else 0
        else:
            survival_rate = 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("จำนวนแม่พันธุ์ปัจจุบัน", f"{total_active_sows} ตัว", f"-{total_dead} คัดทิ้ง/ตาย")
        col2.metric("จำนวนครอกคลอดรวม", f"{total_farrowed_litters} ครอก")
        col3.metric("LSY (ครอก/แม่/ปี)", f"{lsy:.2f}")
        col4.metric("PSY (ลูกหย่านม/แม่/ปี)", f"{psy:.2f}")
        
        st.divider()
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("เฉลี่ยลูกมีชีวิต/ครอก", f"{avg_born_alive:.2f} ตัว")
        col6.metric("เฉลี่ยลูกหย่านม/ครอก", f"{avg_weaned:.2f} ตัว")
        col7.metric("อัตราลูกรอดชีวิต (%)", f"{survival_rate:.2f} %")
        col8.metric("จำนวนลูกหย่านมรวม", f"{sum_weaned} ตัว")
    else:
        st.info("ยังไม่มีข้อมูลเพียงพอสำหรับประมวลผลประสิทธิภาพแม่พันธุ์")

    # --- ข้อมูลสุขภาพและต้นทุนอาหาร ---
    st.divider()
    st.markdown("#### 💊 ข้อมูลสุขภาพและต้นทุนอาหาร (สะสมทั้งหมด)")
    
    total_feed_kg = zone_feed_df['Amount_KG'].astype(float).sum() if not zone_feed_df.empty else 0
    
    if not health_df.empty:
        sick_df = health_df[health_df['Category'] == 'อาการป่วย (Disease)']
        total_sick_events = len(sick_df)
        total_sick_pigs = sick_df['Sow_ID'].nunique() 
    else:
        total_sick_events = 0; total_sick_pigs = 0
        
    total_batch_vaccines = len(batch_health_df) if not batch_health_df.empty else 0
        
    c9, c10, c11 = st.columns(3)
    c9.metric("ปริมาณอาหารรวมทุกโซน", f"{total_feed_kg:,.2f} กก.")
    c10.metric("การป่วยฉุกเฉินรายตัว", f"{total_sick_events} ครั้ง", f"จากหมู {total_sick_pigs} ตัว", delta_color="off")
    c11.metric("การทำวัคซีนกลุ่ม", f"{total_batch_vaccines} รอบ")

    # --- แจ้งเตือน ---
    st.divider()
    st.subheader("🔔 ตารางแจ้งเตือน: กำหนดการเช็คกลับสัด และ รอคลอด")
    if not prod_df.empty:
        active_sow_ids = sow_df[sow_df['Status'] != "คัดทิ้ง/ตาย"]['Sow_ID'].tolist()
        active_prod_df = prod_df[prod_df['Sow_ID'].isin(active_sow_ids)]
        is_empty_date = active_prod_df['Farrow_Date'].astype(str).str.strip().isin(['', 'nan', 'None'])
        pending_records = active_prod_df[is_empty_date]
        
        if not pending_records.empty:
            alert_table = pending_records[['Sow_ID', 'Parity_Num', 'Breed_Date', 'Expected_Heat', 'Expected_Farrow']].copy()
            alert_table.columns = ['เบอร์แม่หมู', 'ท้องที่', 'วันที่ผสม', '📅 กำหนดเช็คกลับสัด (21วัน)', '📅 กำหนดคลอด (114วัน)']
            st.dataframe(alert_table.sort_values(by='📅 กำหนดเช็คกลับสัด (21วัน)'), use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ปัจจุบันยังไม่มีแม่หมูที่อยู่ในระหว่างรอเช็คสัดหรือรอคลอด")

# ----------------- 3. บันทึกข้อมูลรายตัว -----------------
with tab2:
    st.subheader("บันทึกเหตุการณ์หน้าคอกรายตัว")
    show_dead = st.toggle("แสดงรายชื่อแม่หมูที่ถูกคัดทิ้ง/ตายแล้วด้วย", value=False)
    
    if not sow_df.empty:
        display_df = sow_df if show_dead else sow_df[sow_df['Status'] != "คัดทิ้ง/ตาย"]
        if display_df.empty:
            st.info("ไม่มีแม่หมูในสถานะปัจจุบัน")
            
        for _, row in display_df.iterrows():
            sow_id, current_parity, status = row['Sow_ID'], int(row['Parity']), row['Status']
            status_emoji = "💀" if status == "คัดทิ้ง/ตาย" else "🐷"
            
            with st.expander(f"{status_emoji} เบอร์หู: {sow_id} | สถานะ: {status} | ท้องที่: {current_parity}"):
                
                if status == "คัดทิ้ง/ตาย":
                    st.error(f"แม่หมูตัวนี้ถูกคัดทิ้ง/ตาย เมื่อวันที่ {row.get('Exit_Date', '-')} | สาเหตุ: {row.get('Exit_Reason', '-')}")
                
                sub1, sub_return, sub2, sub3, sub4, sub5, sub6 = st.tabs([
                    "❤️ ผสมพันธุ์", "🔄 แจ้งกลับสัด", "🍼 คลอดลูก", "🐖 หย่านม", "🩺 รักษาฉุกเฉิน", "📖 สมุดประวัติรวม", "⚙️ ตั้งค่า/คัดทิ้ง"
                ])
                
                # --- ผสมพันธุ์ ---
                with sub1:
                    with st.form(key=f"b_{sow_id}"):
                        d_breed = st.date_input("วันที่ผสม", key=f"db_{sow_id}")
                        sire = st.text_input("เบอร์พ่อพันธุ์", key=f"sr_{sow_id}")
                        breed_count = st.selectbox("ครั้งที่ผสม", [1, 2, 3], key=f"b_count_{sow_id}")
                        if st.form_submit_button("บันทึกการผสมพันธุ์"):
                            try:
                                current_v = int(row.get("version", 1))
                                # เช็คเวอร์ชันที่แม่หมูก่อน (ต้องอัปเดตผ่านถึงจะยอมให้เซฟ)
                                res = supabase.table("sow_data").update({"Status": "อุ้มท้อง", "version": current_v + 1}).eq("Sow_ID", sow_id).eq("version", current_v).execute()
                                
                                if not res.data:
                                    st.error("⚠️ ข้อมูลถูกบันทึกโดยเครื่องอื่นไปแล้ว กรุณารีเฟรชหน้าเว็บเพื่อดูสถานะล่าสุดครับ")
                                else:
                                    exp_heat, exp_farrow = d_breed + timedelta(days=21), d_breed + timedelta(days=114)
                                    new_rec = {
                                        "Record_ID": f"PROD_{sow_id}_{current_parity+1}",
                                        "Sow_ID": sow_id, "Parity_Num": current_parity + 1,
                                        "Breed_Date": d_breed.strftime("%Y-%m-%d"), "Expected_Heat": exp_heat.strftime("%Y-%m-%d"), "Expected_Farrow": exp_farrow.strftime("%Y-%m-%d"),
                                        "Sire_ID": sire, "Breed_Count": str(breed_count),
                                        "Farrow_Date": "", "Total_Born": 0, "Born_Alive": 0, "Stillborn": 0, "Mummy": 0, "Birth_Weight": 0.0,
                                        "Wean_Date": "", "Weaned_Pigs": 0, "Wean_Weight": 0.0, "version": 1
                                    }
                                    supabase.table("production_data").insert(new_rec).execute()
                                    st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error("⚠️ ระบบตรวจพบข้อมูลซ้ำ! ท่านได้บันทึกการผสมพันธุ์ของรอบท้องนี้ไปแล้วครับ")

                # --- แจ้งกลับสัด ---
                with sub_return:
                    st.info("ใช้กรณีที่ผสมไปแล้ว 21 วัน แต่หมูแสดงอาการเป็นสัดอีกครั้ง เพื่อยกเลิกวันรอคลอดเดิมทิ้ง")
                    if st.button("🔄 ยืนยันหมูกลับสัด (ผสมไม่ติด)", key=f"r_{sow_id}", type="primary"):
                        try:
                            supabase.table("production_data").delete().eq("Sow_ID", sow_id).eq("Parity_Num", current_parity + 1).execute()
                            current_v = int(row.get("version", 1))
                            supabase.table("sow_data").update({"Status": "รอผสม", "version": current_v + 1}).eq("Sow_ID", sow_id).execute()
                            st.success("นำกลับสู่รอบรอผสมแล้ว"); time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรชหน้าเว็บ")

                # --- คลอดลูก ---
                with sub2:
                    with st.form(key=f"f_{sow_id}"):
                        d_farrow = st.date_input("วันที่คลอด", key=f"df_{sow_id}")
                        alive = st.number_input("ลูกมีชีวิต", min_value=0, key=f"al_{sow_id}")
                        stillborn = st.number_input("ตายคลอด", min_value=0, key=f"st_{sow_id}")
                        mummy = st.number_input("มัมมี่", min_value=0, key=f"mm_{sow_id}")
                        wt = st.number_input("น้ำหนักรวม (กก.)", min_value=0.0, step=0.1, key=f"wt_{sow_id}")
                        if st.form_submit_button("บันทึกการคลอด"):
                            try:
                                data = {"Farrow_Date": d_farrow.strftime("%Y-%m-%d"), "Total_Born": alive + stillborn + mummy, "Born_Alive": alive, "Stillborn": stillborn, "Mummy": mummy, "Birth_Weight": wt}
                                supabase.table("production_data").update(data).eq("Sow_ID", sow_id).eq("Parity_Num", current_parity + 1).execute()
                                current_v = int(row.get("version", 1))
                                supabase.table("sow_data").update({"Parity": current_parity + 1, "Status": "เลี้ยงลูก", "version": current_v + 1}).eq("Sow_ID", sow_id).execute()
                                st.success("บันทึกคลอดสำเร็จ"); time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error("⚠️ เกิดข้อผิดพลาดในการบันทึก กรุณารีเฟรชหน้าเว็บ")

                # --- หย่านม ---
                with sub3:
                    with st.form(key=f"w_{sow_id}"):
                        d_wean = st.date_input("วันที่หย่านม", key=f"dw_{sow_id}")
                        weaned = st.number_input("ลูกหย่านม", min_value=0, key=f"wp_{sow_id}")
                        wwt = st.number_input("น้ำหนักตอนหย่านม", min_value=0.0, step=0.1, key=f"wwt_{sow_id}")
                        if st.form_submit_button("บันทึกการหย่านม"):
                            try:
                                data = {"Wean_Date": d_wean.strftime("%Y-%m-%d"), "Weaned_Pigs": weaned, "Wean_Weight": wwt}
                                supabase.table("production_data").update(data).eq("Sow_ID", sow_id).eq("Parity_Num", current_parity).execute()
                                current_v = int(row.get("version", 1))
                                supabase.table("sow_data").update({"Status": "รอผสม", "version": current_v + 1}).eq("Sow_ID", sow_id).execute()
                                st.success("บันทึกหย่านมสำเร็จ"); time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error("⚠️ เกิดข้อผิดพลาดในการบันทึก กรุณารีเฟรชหน้าเว็บ")

                # --- รักษาฉุกเฉิน ---
               # --- รักษาฉุกเฉิน ---
                with sub4:
                    st.markdown("#### 🩺 บันทึกการรักษา / ฉีดยารายตัวฉุกเฉิน")
                    with st.form(key=f"health_{sow_id}"):
                        h_date = st.date_input("วันที่ฉีด/รักษา", key=f"h_date_{sow_id}")
                        
                        # 1. เพิ่มหมวดหมู่ "การให้ยา/รักษา" ลงไปในตัวเลือก
                        h_cat = st.radio("ประเภท", ["อาการป่วย (Disease)", "การให้ยา/รักษา (Medication)", "วัคซีนรายตัว (Individual Vaccine)"], key=f"h_cat_{sow_id}", horizontal=True)
                        
                        # 2. แยกช่องกรอกให้ละเอียดขึ้น
                        h_detail = st.text_input("ชื่อโรค / ชนิดยา / ชื่อวัคซีน", key=f"h_det_{sow_id}")
                        h_treat = st.text_input("การรักษา / หมายเหตุเพิ่มเติม", placeholder="เช่น ฉีดเข้ากล้ามเนื้อ, ให้วิตามินเสริม", key=f"h_tr_{sow_id}")
                        
                        col_cc, col_w = st.columns(2)
                        h_cc = col_cc.number_input("ปริมาณที่ฉีด (CC / ml)", min_value=0.0, step=0.5, key=f"h_cc_{sow_id}")
                        h_withdraw = col_w.number_input("ระยะหยุดยา (วัน)", min_value=0, step=1, help="จำนวนวันที่ต้องรอก่อนยาหมดฤทธิ์ เพื่อส่งโรงฆ่า", key=f"h_w_{sow_id}")
                        
                        if h_withdraw > 0:
                            safe_date = h_date + timedelta(days=h_withdraw)
                            st.warning(f"⚠️ **ห้ามส่งโรงฆ่าสัตว์ก่อนวันที่:** {safe_date.strftime('%d %B %Y')}")
                            
                        if st.form_submit_button("บันทึกการรักษา"):
                            if not h_detail:
                                st.error("กรุณาระบุ ชื่อโรค / ชนิดยา / ชื่อวัคซีน")
                            else:
                                try:
                                    # ปรับการสร้างรหัส ID ให้ใช้วินาที ป้องกันบันทึกยา 2 ชนิดในวันเดียวกันแล้วข้อมูลซ้ำ
                                    unique_health_id = f"H_{sow_id}_{(datetime.utcnow()+timedelta(hours=7)).strftime('%Y%m%d%H%M%S')}"
                                    
                                    supabase.table("health_records").insert({
                                        "Record_ID": unique_health_id, 
                                        "Sow_ID": sow_id, 
                                        "Record_Date": h_date.strftime("%Y-%m-%d"), 
                                        "Category": h_cat, 
                                        "Detail": h_detail, 
                                        "Treatment": h_treat, 
                                        "Amount_CC": h_cc, 
                                        "Withdrawal_Days": h_withdraw, 
                                        "version": 1
                                    }).execute()
                                    st.success("บันทึกสำเร็จ!"); time.sleep(1); st.rerun()
                                except Exception as e:
                                    st.error("⚠️ เกิดข้อผิดพลาดในการบันทึก กรุณารีเฟรชหน้าเว็บ")
                # --- สมุดประวัติรวม (แก้ไข/ลบ) ---
                with sub5:
                    with st.expander("1. ประวัติการผลิต", expanded=True):
                        sow_prod = prod_df[prod_df['Sow_ID'] == sow_id].copy()
                        if not sow_prod.empty:
                            edited_prod = st.data_editor(sow_prod, use_container_width=True, key=f"editor_prod_{sow_id}", hide_index=True, num_rows="dynamic", column_config={"Record_ID": None, "Sow_ID": None, "version": None})
                            if st.button("💾 บันทึกแก้ประวัติผลิต", key=f"save_prod_{sow_id}"):
                                try:
                                    deleted_ids = set(sow_prod['Record_ID']) - set(edited_prod['Record_ID'].dropna())
                                    for d_id in deleted_ids: supabase.table("production_data").delete().eq("Record_ID", d_id).execute()
                                    for idx in edited_prod.index:
                                        r_id = edited_prod.loc[idx, "Record_ID"]
                                        if pd.isna(r_id): continue
                                        orig_row = sow_prod[sow_prod['Record_ID'] == r_id].iloc[0]
                                        if not edited_prod.loc[idx].equals(orig_row):
                                            current_v = int(orig_row.get("version", 1))
                                            update_data = edited_prod.loc[idx].drop(["Record_ID", "Sow_ID", "version"]).to_dict()
                                            update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                                            update_data["version"] = current_v + 1
                                            res = supabase.table("production_data").update(update_data).eq("Record_ID", r_id).eq("version", current_v).execute()
                                            if not res.data: st.error("⚠️ ข้อมูลถูกแก้ไขโดยคนอื่นไปแล้ว กรุณารีเฟรชหน้าเว็บ"); st.stop()
                                    st.success("อัปเดตสำเร็จ!"); time.sleep(1); st.rerun()
                                except Exception as e:
                                    st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")
                        else:
                            st.info("ยังไม่มีประวัติการผลิต")
                            
                    with st.expander("2. ประวัติสุขภาพและวัคซีน"):
                        sow_health = health_df[health_df['Sow_ID'] == sow_id].sort_values(by="Record_Date", ascending=False).copy()
                        if not sow_health.empty:
                            edited_health = st.data_editor(sow_health, use_container_width=True, key=f"editor_health_{sow_id}", hide_index=True, num_rows="dynamic", column_config={"Record_ID": None, "Sow_ID": None, "version": None, "Treatment": None})
                            if st.button("💾 บันทึกแก้ประวัติสุขภาพ", key=f"save_health_{sow_id}"):
                                try:
                                    deleted_ids = set(sow_health['Record_ID']) - set(edited_health['Record_ID'].dropna())
                                    for d_id in deleted_ids: supabase.table("health_records").delete().eq("Record_ID", d_id).execute()
                                    for idx in edited_health.index:
                                        r_id = edited_health.loc[idx, "Record_ID"]
                                        if pd.isna(r_id): continue
                                        orig_row = sow_health[sow_health['Record_ID'] == r_id].iloc[0]
                                        if not edited_health.loc[idx].equals(orig_row):
                                            current_v = int(orig_row.get("version", 1))
                                            update_data = edited_health.loc[idx].drop(["Record_ID", "Sow_ID", "version"]).to_dict()
                                            update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                                            update_data["version"] = current_v + 1
                                            res = supabase.table("health_records").update(update_data).eq("Record_ID", r_id).eq("version", current_v).execute()
                                            if not res.data: st.error("⚠️ ข้อมูลถูกเขียนทับ กรุณารีเฟรช!"); st.stop()
                                    st.success("อัปเดตสำเร็จ!"); time.sleep(1); st.rerun()
                                except Exception as e:
                                    st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")
                        else:
                            st.info("ยังไม่มีประวัติสุขภาพ")

                # --- ตั้งค่า/คัดทิ้ง ---
                with sub6:
                    with st.form(key=f"edit_{sow_id}"):
                        st.markdown("#### แก้ไขข้อมูลพื้นฐาน & บันทึกคัดทิ้ง")
                        e_breed = st.text_input("สายพันธุ์", value=row['Breed'], key=f"e_b_{sow_id}")
                        status_options = ["รอผสม", "อุ้มท้อง", "เลี้ยงลูก", "คัดทิ้ง/ตาย"]
                        try:
                            current_status_idx = status_options.index(row['Status'])
                        except ValueError:
                            current_status_idx = 0
                            
                        e_status = st.selectbox("สถานะแม่หมู", status_options, index=current_status_idx, key=f"e_s_{sow_id}")
                        e_parity = st.number_input("ลำดับท้อง (Parity)", value=int(current_parity), min_value=0, step=1, key=f"e_p_{sow_id}")
                        
                        st.markdown("---")
                        st.markdown("*(กรอกเฉพาะกรณีเปลี่ยนสถานะเป็นคัดทิ้ง/ตาย)*")
                        e_exit_date = st.date_input("วันที่ตาย/คัดทิ้ง", key=f"ex_d_{sow_id}")
                        e_exit_reason = st.text_input("สาเหตุการตายหรือคัดทิ้ง", value=row.get('Exit_Reason', ''), key=f"ex_r_{sow_id}")
                        
                        if st.form_submit_button("💾 บันทึกการแก้ไข"):
                            try:
                                current_version = int(row.get("version", 1))
                                update_data = {"Breed": e_breed, "Status": e_status, "Parity": e_parity, "version": current_version + 1}
                                if e_status == "คัดทิ้ง/ตาย":
                                    update_data["Exit_Date"] = e_exit_date.strftime("%Y-%m-%d")
                                    update_data["Exit_Reason"] = e_exit_reason
                                else:
                                    update_data["Exit_Date"] = ""; update_data["Exit_Reason"] = ""
                                res = supabase.table("sow_data").update(update_data).eq("Sow_ID", sow_id).eq("version", current_version).execute()
                                if not res.data: st.error("⚠️ แจ้งเตือน: สถานะของแม่หมูตัวนี้ถูกเปลี่ยนโดยผู้ใช้งานท่านอื่นไปแล้ว กรุณารีเฟรชหน้าเว็บ!")
                                else: st.success("อัปเดตสำเร็จ!"); time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")

# ----------------- 4. บันทึกข้อมูลรวม (โซน/ฝูง) -----------------
with tab3:
    st.subheader("📝 บันทึกข้อมูลรวม (ลดภาระการจดรายตัว)")
    
    col_zone_feed, col_batch_vaccine = st.columns(2)
    
    zone_map = {
        "โซนหมูสาว (Gilt Pool)": "Z1",
        "โซนผสมพันธุ์และรอผสม (Mating & Weaning Zone)": "Z2",
        "โซนอุ้มท้อง (Gestation Zone)": "Z3",
        "โซนคลอด / ให้นม (Farrowing / Lactation Zone)": "Z4"
    }
    
    # --- แบบฟอร์ม 1: อาหารตามโซน ---
    with col_zone_feed:
        st.markdown("#### 🥣 บันทึกอาหารรวมตามโซนคอก (Weekly Feed Log)")
        st.caption("บันทึกภาพรวมรายสัปดาห์ ไม่ต้องจดแยกรายตัว")
        with st.form("zone_feed_form"):
            zf_date = st.date_input("วันที่เบิกใช้/บันทึก", key="zf_date")
            zf_zone = st.selectbox("เลือกโซนคอก", list(zone_map.keys()))
            zf_type = st.selectbox("สูตรอาหารที่ใช้", [
                "อาหารสูตรเตรียมพันธุ์",
                "อาหารสูตรกระตุ้นการกลับสัด",
                "อาหารหมูอุ้มท้อง",
                "อาหารหมูเลี้ยงลูก",
                "อื่นๆ"
            ])
            zf_amount = st.number_input("ปริมาณที่เบิกใช้จริง (กิโลกรัม)", min_value=0.0, step=1.0)
            
            if st.form_submit_button("💾 ยืนยันการเบิกใช้อาหาร"):
                if zf_amount <= 0:
                    st.error("กรุณาระบุปริมาณอาหารที่มากกว่า 0")
                else:
                    try:
                        unique_zf_id = f"ZF_{zone_map[zf_zone]}_{zf_date.strftime('%Y%m%d')}"
                        supabase.table("zone_feed_records").insert({
                            "Record_ID": unique_zf_id,
                            "Record_Date": zf_date.strftime("%Y-%m-%d"),
                            "Zone_Name": zf_zone,
                            "Feed_Type": zf_type,
                            "Amount_KG": zf_amount,
                            "version": 1
                        }).execute()
                        st.success(f"บันทึกอาหาร {zf_zone} เรียบร้อย!")
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error("⚠️ ข้อมูลซ้ำ! มีการบันทึกอาหารของโซนนี้ในวันนี้ไปแล้ว หากต้องการแก้ไขให้ไปที่ตารางประวัติด้านล่างครับ")

    # --- แบบฟอร์ม 2: วัคซีนกลุ่ม ---
    with col_batch_vaccine:
        st.markdown("#### 💉 การฉีดวัคซีนตามรอบโปรแกรม (Batch Vaccination)")
        st.caption("บันทึกรวดเดียวเมื่อฉีดเสร็จทั้งคอก/ทั้งกลุ่ม")
        with st.form("batch_vaccine_form"):
            bv_date = st.date_input("วันที่ฉีดวัคซีน", key="bv_date")
            bv_group = st.selectbox("กลุ่มแม่หมูเป้าหมาย", [
                "แม่หมูกลุ่มอุ้มท้องทั้งหมด",
                "แม่หมูกลุ่มรอผสม",
                "แม่หมูสาว (ทดแทน)",
                "แม่หมูทั้งฟาร์ม (Mass Vaccination)"
            ])
            bv_name = st.text_input("ชื่อวัคซีน (เช่น PRRS, FMD)", placeholder="ระบุชื่อวัคซีน")
            bv_lot = st.text_input("ล็อตนัมเบอร์ (Lot Number)", placeholder="ระบุเพื่อตรวจสอบย้อนหลัง")
            
            if st.form_submit_button("💾 ยืนยันการฉีดวัคซีนตามรอบ"):
                if not bv_name:
                    st.error("กรุณาระบุชื่อวัคซีน")
                else:
                    try:
                        safe_group = "".join(c for c in bv_group if c.isalnum())[:10]
                        safe_vac = "".join(c for c in bv_name if c.isalnum())[:10]
                        unique_bv_id = f"BV_{safe_group}_{safe_vac}_{bv_date.strftime('%Y%m%d')}"
                        
                        supabase.table("batch_health_records").insert({
                            "Record_ID": unique_bv_id,
                            "Record_Date": bv_date.strftime("%Y-%m-%d"),
                            "Target_Group": bv_group,
                            "Vaccine_Name": bv_name,
                            "Lot_Number": bv_lot,
                            "version": 1
                        }).execute()
                        st.success("บันทึกประวัติวัคซีนกลุ่มสำเร็จ!")
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error("⚠️ ข้อมูลซ้ำ! มีการบันทึกวัคซีนรอบนี้ไปแล้วครับ")

    # ================= ประวัติการบันทึกย้อนหลัง =================
    st.divider()
    st.markdown("#### 🕒 ประวัติการบันทึกย้อนหลัง (สามารถแก้ไข / ลบได้)")
    st.info("💡 **ทริค:** ดับเบิ้ลคลิกที่ช่องในตารางเพื่อแก้ไขข้อความหรือตัวเลข หรือคลิกเลือกหน้าแถวแล้วกดปุ่ม **Delete** บนคีย์บอร์ดเพื่อลบทิ้ง")
    
    with st.expander("1. ประวัติการเบิกอาหารรวมตามโซน", expanded=True):
        if not zone_feed_df.empty:
            zf_hist = zone_feed_df.sort_values(by="Record_Date", ascending=False).copy()
            edited_zf = st.data_editor(
                zf_hist, use_container_width=True, key="editor_zone_feed", hide_index=True, num_rows="dynamic", column_config={"Record_ID": None, "version": None}
            )
            if st.button("💾 บันทึกการแก้ไขประวัติอาหารโซน", type="primary", key="save_zf"):
                try:
                    deleted_ids = set(zf_hist['Record_ID']) - set(edited_zf['Record_ID'].dropna())
                    for d_id in deleted_ids: supabase.table("zone_feed_records").delete().eq("Record_ID", d_id).execute()
                    for idx in edited_zf.index:
                        r_id = edited_zf.loc[idx, "Record_ID"]
                        if pd.isna(r_id): continue
                        orig_row = zf_hist[zf_hist['Record_ID'] == r_id].iloc[0]
                        if not edited_zf.loc[idx].equals(orig_row):
                            current_v = int(orig_row.get("version", 1))
                            update_data = edited_zf.loc[idx].drop(["Record_ID", "version"]).to_dict()
                            update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                            update_data["version"] = current_v + 1
                            res = supabase.table("zone_feed_records").update(update_data).eq("Record_ID", r_id).eq("version", current_v).execute()
                            if not res.data: st.error("⚠️ ข้อมูลถูกเขียนทับโดยผู้ใช้อื่น กรุณารีเฟรช!"); st.stop()
                    st.success("อัปเดตประวัติอาหารโซนเรียบร้อย!"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")
        else:
            st.info("ยังไม่มีประวัติการเบิกอาหารโซน")

    with st.expander("2. ประวัติการฉีดวัคซีนกลุ่ม", expanded=False):
        if not batch_health_df.empty:
            bv_hist = batch_health_df.sort_values(by="Record_Date", ascending=False).copy()
            edited_bv = st.data_editor(
                bv_hist, use_container_width=True, key="editor_batch_vaccine", hide_index=True, num_rows="dynamic", column_config={"Record_ID": None, "version": None}
            )
            if st.button("💾 บันทึกการแก้ไขประวัติวัคซีนกลุ่ม", type="primary", key="save_bv"):
                try:
                    deleted_ids = set(bv_hist['Record_ID']) - set(edited_bv['Record_ID'].dropna())
                    for d_id in deleted_ids: supabase.table("batch_health_records").delete().eq("Record_ID", d_id).execute()
                    for idx in edited_bv.index:
                        r_id = edited_bv.loc[idx, "Record_ID"]
                        if pd.isna(r_id): continue
                        orig_row = bv_hist[bv_hist['Record_ID'] == r_id].iloc[0]
                        if not edited_bv.loc[idx].equals(orig_row):
                            current_v = int(orig_row.get("version", 1))
                            update_data = edited_bv.loc[idx].drop(["Record_ID", "version"]).to_dict()
                            update_data = {k: (None if pd.isna(v) else v) for k, v in update_data.items()}
                            update_data["version"] = current_v + 1
                            res = supabase.table("batch_health_records").update(update_data).eq("Record_ID", r_id).eq("version", current_v).execute()
                            if not res.data: st.error("⚠️ ข้อมูลถูกเขียนทับโดยผู้ใช้อื่น กรุณารีเฟรช!"); st.stop()
                    st.success("อัปเดตประวัติวัคซีนกลุ่มเรียบร้อย!"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")
        else:
            st.info("ยังไม่มีประวัติวัคซีนกลุ่ม")

# ----------------- 5. เพิ่มแม่พันธุ์ใหม่ -----------------
with tab4:
    st.subheader("➕ เพิ่มข้อมูลแม่พันธุ์ตัวใหม่เข้าสู่ฟาร์ม")
    with st.form("add_sow"):
        n_id = st.text_input("รหัสแม่พันธุ์ (Sow ID)")
        n_breed = st.text_input("สายพันธุ์ (เช่น ลาร์จไวต์, แลนด์เรซ)")
        n_date = st.date_input("วันที่เข้าฝูง / วันเกิด")
        n_parity = st.number_input("ลำดับการคลอดตั้งต้น (หมูสาว = 0)", min_value=0)
        
        if st.form_submit_button("💾 บันทึกลงฐานข้อมูล"):
            if not n_id: st.error("กรุณากรอกรหัส")
            else:
                try:
                    supabase.table("sow_data").insert({
                        "Sow_ID": n_id, "Breed": n_breed, "Entry_Date": n_date.strftime("%Y-%m-%d"), 
                        "Parity": n_parity, "Status": "รอผสม", "Exit_Date": "", "Exit_Reason": "", "version": 1
                    }).execute()
                    st.success(f"เพิ่มแม่หมูเบอร์ {n_id} สำเร็จ!"); time.sleep(1); st.rerun()
                except Exception as e: 
                    st.error(f"⚠️ ข้อมูลซ้ำ! มีแม่หมูเบอร์นี้ในระบบแล้วครับ")

# ----------------- 6. ทะเบียนคัดทิ้ง/ตาย -----------------
with tab5:
    st.subheader("💀 ทะเบียนแม่หมูคัดทิ้งและตาย")
    dead_sows = sow_df[sow_df['Status'] == "คัดทิ้ง/ตาย"].copy()
    
    if not dead_sows.empty:
        edit_cols = ["Sow_ID", "Breed", "Exit_Date", "Exit_Reason", "version"]
        dead_sows_display = dead_sows[edit_cols]
        
        edited_dead_sows = st.data_editor(dead_sows_display, use_container_width=True, disabled=["Sow_ID", "Breed"], key="editor_dead_sows", hide_index=True, column_config={"version": None})
        
        if st.button("💾 บันทึกการแก้ไขประวัติคัดทิ้ง", type="primary"):
            try:
                for idx in edited_dead_sows.index:
                    if not edited_dead_sows.loc[idx].equals(dead_sows_display.loc[idx]):
                        s_id = edited_dead_sows.loc[idx, "Sow_ID"]
                        current_v = int(edited_dead_sows.loc[idx, "version"])
                        new_date = "" if pd.isna(edited_dead_sows.loc[idx, "Exit_Date"]) else edited_dead_sows.loc[idx, "Exit_Date"]
                        new_reason = "" if pd.isna(edited_dead_sows.loc[idx, "Exit_Reason"]) else edited_dead_sows.loc[idx, "Exit_Reason"]
                        
                        res = supabase.table("sow_data").update({"Exit_Date": new_date, "Exit_Reason": new_reason, "version": current_v + 1}).eq("Sow_ID", s_id).eq("version", current_v).execute()
                        if not res.data: st.error(f"⚠️ ข้อมูลเบอร์ {s_id} ถูกแก้โดยคนอื่นไปแล้ว"); st.stop()
                st.success("อัปเดตข้อมูลเรียบร้อย!"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error("⚠️ เกิดข้อผิดพลาด กรุณารีเฟรช")
            
        st.divider()
        st.markdown("#### 🔄 ยกเลิกการคัดทิ้ง หรือ ลบข้อมูลถาวร")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("undo_cull_form"):
                st.markdown("**ดึงแม่หมูกลับเข้าระบบ**")
                undo_id = st.selectbox("เลือกเบอร์หู", dead_sows['Sow_ID'].tolist(), key="undo_id")
                if st.form_submit_button("🔄 ยกเลิกการคัดทิ้ง"):
                    try:
                        current_v = int(dead_sows[dead_sows['Sow_ID'] == undo_id].iloc[0]['version'])
                        supabase.table("sow_data").update({"Status": "รอผสม", "Exit_Date": "", "Exit_Reason": "", "version": current_v + 1}).eq("Sow_ID", undo_id).eq("version", current_v).execute()
                        st.success(f"ดึงเบอร์ {undo_id} กลับเข้าระบบแล้ว"); time.sleep(1.5); st.rerun()
                    except Exception as e:
                        st.error("⚠️ ข้อมูลถูกเขียนทับ กรุณารีเฟรช")
        with col2:
            with st.form("delete_cull_form"):
                st.markdown("**ลบข้อมูลถาวร** (ล้างประวัติทุกอย่าง)")
                del_id = st.selectbox("เลือกเบอร์หู", dead_sows['Sow_ID'].tolist(), key="del_id")
                confirm_del = st.checkbox("ยืนยันการลบถาวร")
                if st.form_submit_button("🚨 ลบข้อมูลถาวร"):
                    if confirm_del:
                        try:
                            supabase.table("production_data").delete().eq("Sow_ID", del_id).execute()
                            supabase.table("health_records").delete().eq("Sow_ID", del_id).execute()
                            supabase.table("sow_data").delete().eq("Sow_ID", del_id).execute()
                            st.success(f"ลบข้อมูล {del_id} ถาวรแล้ว!"); time.sleep(1.5); st.rerun()
                        except Exception as e:
                            st.error("⚠️ เกิดข้อผิดพลาด")
                    else: st.error("กรุณากดยืนยันก่อนลบ")
    else:
        st.success("🎉 ยังไม่มีประวัติแม่หมูคัดทิ้งหรือตาย")
