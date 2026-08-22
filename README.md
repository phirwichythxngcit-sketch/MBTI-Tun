# 🎓 แบบสอบถามแนะแนวคณะมหาวิทยาลัย (Faculty Guidance Web App)

เว็บแอป Streamlit สำหรับช่วยนักเรียนค้นพบคณะ/สาขามหาวิทยาลัยที่เหมาะกับตัวเอง
โดยวิเคราะห์ **3 ด้าน** แล้วจับคู่กับฐานข้อมูล **68 คณะ** เพื่อคำนวณ % ความเข้ากันได้ (Match%):

1. 📚 **ความสนใจรายวิชา** — 5 หมวด (M/S/L/H/A) หมวดละ 20 ข้อ ให้คะแนน 1–5
2. 🧠 **Cognitive Functions** — 8 ฟังก์ชัน (Ti Te Fe Fi Se Si Ne Ni) ฟังก์ชันละ 10 ข้อ ให้คะแนน 1–5
3. 💰 **งบประมาณต่อเทอม** — 3 ระดับ ใช้แนะนำมหาวิทยาลัยที่เข้าถึงได้ตามงบ

> ⚠️ ผลลัพธ์เป็น**เครื่องมือช่วยตัดสินใจ ไม่ใช่คำชี้ขาด** — ไม่ใช่การวินิจฉัยทางจิตวิทยา
> ที่ผ่านการตรวจสอบมาตรฐานทางสถิติ ควรใช้ประกอบการปรึกษาครูแนะแนวและผู้ปกครองเสมอ

## 🚀 วิธีรันบนเครื่อง (Local)

```bash
# 1. สร้าง virtual environment (แนะนำ)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. รันแอป
streamlit run app.py
```

เบราว์เซอร์จะเปิด `http://localhost:8501` อัตโนมัติ

## ☁️ วิธี Deploy ฟรี (Streamlit Community Cloud)

1. สร้าง GitHub repo ใหม่ (public) แล้ว push โค้ดทั้งหมดรวมโฟลเดอร์ `data/` ขึ้นไป:
   ```bash
   git init
   git add .
   git commit -m "feat: faculty guidance streamlit app"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo>.git
   git push -u origin main
   ```
2. ไปที่ [share.streamlit.io](https://share.streamlit.io) → ล็อกอินด้วย GitHub
3. กด **"New app"** → เลือก repo + branch (`main`) + ระบุ Main file path เป็น `app.py`
4. กด **Deploy** → ได้ลิงก์ `https://<app-name>.streamlit.app` ฟรีทันที
5. ทุกครั้งที่ `git push` โค้ดใหม่ขึ้น branch ที่ deploy ไว้ แอปจะ**อัปเดตอัตโนมัติ**

## 🗂️ โครงสร้างไฟล์

```
faculty-guidance/
├── app.py                      # Streamlit main app (wizard 16 หน้า + logic ทั้งหมด)
├── data/
│   ├── ความชอบ2.txt            # แบบสำรวจความสนใจ 5 หมวด x 20 ข้อ
│   ├── MBTI_2.txt              # แบบสำรวจ Cognitive Functions 8 ฟังก์ชัน x 10 ข้อ
│   ├── การเงิน.txt             # นิยามระดับงบประมาณ 3 ระดับ (B1/B2/B3)
│   └── faculty_database_v2.json # ฐานข้อมูลคณะ 68 คณะ + เงื่อนไข + มหาวิทยาลัยแนะนำตามงบ
├── requirements.txt             # streamlit, pandas
└── README.md
```

คำถามทั้งหมดอ่านจากไฟล์ใน `data/` เสมอ (parse ด้วย regex จากหัวข้อ `##` และเลขข้อ)
— แก้คำถามในไฟล์ txt ได้เลย **ไม่ต้องแก้โค้ด**

## 📱 ลำดับหน้าจอ (Wizard)

| หน้า | เนื้อหา |
|---|---|
| 1 | Welcome — อธิบายภาพรวม + ปุ่มเริ่ม |
| 2–6 | ความสนใจ 5 หมวด (หมวดละ 1 หน้า, 20 ข้อ/หน้า) |
| 7–14 | Cognitive Functions 8 ฟังก์ชัน (ฟังก์ชันละ 1 หน้า, 10 ข้อ/หน้า) |
| 15 | เลือกระดับงบประมาณ B1/B2/B3 |
| 16 | ผลลัพธ์ Top-10 คณะ + เหตุผล + มหาวิทยาลัยแนะนำ |

ต้อง**ตอบให้ครบทุกข้อ**ในหน้านั้นๆ ปุ่ม "ถัดไป" จึงจะกดได้ (ตรวจด้วย session state)

## 🧮 อัลกอริทึมการคำนวณ Match%

### 1. คะแนนหมวดความสนใจ (%)

```
% ของหมวด = ผลรวมคะแนน 20 ข้อ          (max = 20×5 = 100 พอดี)
```

### 2. คะแนนฟังก์ชัน (normalize 0–100)

```
raw = ผลรวมคะแนน 10 ข้อ                (10–50)
functionStrength = (raw − 10) / 40 × 100
```

### 3. Match% ต่อคณะ = 0.3 × mbtiScore + 0.7 × subjScore

**mbtiScore** (ตาม scope ของคณะ):
- `D/A` → max(functionStrength ของฟังก์ชันที่คณะกำหนด)
- `Dominant` → ถ้าฟังก์ชัน dominant ของผู้ใช้ (สูงสุดใน 8 ฟังก์ชัน) อยู่ในคณะ → ใช้ค่านั้นเต็มๆ / ถ้าไม่ → max × 0.5
- `Mixed` (คณะสถาปัตยกรรมฯ) → Ni เป็น dominant หรือ Ti แบบ D/A ปกติ → เอาค่ามากกว่าของสองแบบ

**subjScore** (เงื่อนไขหมวดวิชาหลายข้อ = AND):
```
ratio(เงื่อนไข) = min(คะแนนหมวดผู้ใช้ ÷ ค่า min × 100, 100)
subjScore = min(ratio ของทุกเงื่อนไข)
```

### 4. ระดับงบประมาณ

| Tier | ระดับ | เกณฑ์ (บาท/เทอม) |
|---|---|---|
| B1 | จำกัดสูง | ≤ 15,000 หรือต้องกู้ กยศ./ทุนเรียนฟรี |
| B2 | ปานกลาง | 15,001 – 40,000 |
| B3 | สูง/พร้อมสนับสนุน | ≥ 40,001 (รวมเอกชน/นานาชาติ) |

Tier ที่เลือกถูกใช้เลือกค่า `budget[tier]` ของแต่ละคณะเป็นคำแนะนำมหาวิทยาลัย
