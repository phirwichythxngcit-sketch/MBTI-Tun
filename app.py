"""แอปแนะแนวคณะมหาวิทยาลัย — Streamlit wizard 16 หน้า

หน้า 0      : Welcome
หน้า 1-5    : แบบสำรวจความสนใจ 5 หมวด (M/S/L/H/A) จาก data/ความชอบ2.txt
หน้า 6-13   : แบบสำรวจ Cognitive Functions 8 ฟังก์ชัน จาก data/MBTI_2.txt
หน้า 14     : คำถามงบประมาณ จาก data/การเงิน.txt
หน้า 15     : ผลลัพธ์ Top-10 คณะที่ Match% สูงสุด

รัน: streamlit run app.py
"""

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INTEREST_FILE = DATA_DIR / "ความชอบ2.txt"
FUNCTION_FILE = DATA_DIR / "MBTI_2.txt"
BUDGET_FILE = DATA_DIR / "การเงิน.txt"
FACULTY_DB_FILE = DATA_DIR / "faculty_database_v2.json"

CAT_KEYWORDS = [("M", "คณิต"), ("S", "วิทยาศาสตร์"), ("L", "ภาษา"), ("H", "สังคม"), ("A", "ศิลปะ")]
CAT_CODES = [code for _, code in CAT_KEYWORDS]
CAT_TH = {
    "M": "คณิตศาสตร์/คอมพิวเตอร์",
    "S": "วิทยาศาสตร์/เทคโนโลยี",
    "L": "ภาษา/วรรณกรรม",
    "H": "สังคมศึกษา/มนุษยศาสตร์",
    "A": "ศิลปะ/ดนตรี",
}

WELCOME_PAGE = 0
BUDGET_PAGE = 14
RESULTS_PAGE = 15
TOTAL_STEPS = 14

WEIGHT_MBTI = 0.3
WEIGHT_SUBJECT = 0.7
TOP_N = 10

INTEREST_SCALE = {1: "ไม่ใช่เลย", 2: "ไม่ค่อยใช่", 3: "กลางๆ", 4: "ค่อนข้างใช่", 5: "ใช่มากที่สุด"}
FUNCTION_SCALE = {
    1: "ไม่เห็นด้วยอย่างยิ่ง",
    2: "ไม่เห็นด้วย",
    3: "เฉยๆ / ไม่แน่ใจ",
    4: "เห็นด้วย",
    5: "เห็นด้วยอย่างยิ่ง",
}

DISCLAIMER = (
    "⚠️ **คำเตือน:** แบบสอบถามนี้จัดทำขึ้นเพื่อการเรียนรู้และสำรวจตนเอง "
    "ไม่ใช่เครื่องมือวินิจฉัยที่ผ่านการตรวจสอบมาตรฐานทางสถิติ (psychometric validation) "
    "ผลลัพธ์จึงเป็นเพียง**เครื่องมือช่วยตัดสินใจ ไม่ใช่คำชี้ขาด** "
    "ควรใช้ประกอบการปรึกษาครูแนะแนว ผู้ปกครอง และข้อมูลจริงของแต่ละสถาบันเสมอ"
)

GROUP_TH = {
    "STEM": "🔬 กลุ่มวิทยาศาสตร์/วิศวกรรม",
    "Health": "🏥 กลุ่มสุขภาพ",
    "Language": "🗣️ กลุ่มภาษา/มนุษยศาสตร์",
    "Social": "🏛️ กลุ่มสังคมศาสตร์",
    "Arts": "🎨 กลุ่มศิลปะ",
    "Hybrid": "🔀 กลุ่มสหศาสตร์",
}


def read_text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def normalize_function_code(code):
    """ทำรหัสฟังก์ชันให้เป็นรูปแบบเดียวกับ faculty_database_v2.json เช่น 'TI'/'ti' -> 'Ti'"""
    code = str(code).strip()
    return code[:1].upper() + code[1:].lower() if len(code) >= 2 else code.upper()


def cat_code_from_title(title, order_index):
    for code, keyword in CAT_KEYWORDS:
        if keyword in title:
            return code
    if order_index < len(CAT_CODES):
        return CAT_CODES[order_index]
    return f"X{order_index}"


def parse_interest_survey(path):
    """อ่าน data/ความชอบ2.txt → list ของ dict

    คืนค่า [{"code": "M", "title": "...", "questions": ["...", ...]}, ...]
    โดยจับหัวข้อจากบรรทัด '## N. Title' และข้อคำถามจากบรรทัด 'N. text'
    """
    sections = []
    current = None
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if line.startswith("##"):
            m_head = re.match(r"^#+\s*(\d+)\s*[.)]\s*(.+)$", line)
            current = None
            if m_head:
                title = m_head.group(2).strip()
                current = {
                    "code": cat_code_from_title(title, len(sections)),
                    "title": title,
                    "questions": [],
                }
                sections.append(current)
            continue
        m_q = re.match(r"^(\d{1,2})\s*[.)]\s+(.+)$", line)
        if m_q and current is not None:
            current["questions"].append(m_q.group(2).strip())
    return sections


def parse_function_survey(path):
    """อ่าน data/MBTI_2.txt → list ของ dict เรียงตามลำดับในไฟล์

    คืนค่า [{"code": "Ti", "title": "...", "questions": [...]}, ...] รวม 8 ฟังก์ชัน
    โดยจับหัวข้อจากบรรทัด '## XX — Full Name' และข้อคำถามจากบรรทัด 'N. text'
    """
    sections = []
    current = None
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if line.startswith("##"):
            m_head = re.match(r"^#+\s*([A-Za-z]{1,2})\s*[—–\-]\s*(.+)$", line)
            current = None
            if m_head:
                current = {
                    "code": normalize_function_code(m_head.group(1)),
                    "title": m_head.group(2).strip(),
                    "questions": [],
                }
                sections.append(current)
            continue
        m_q = re.match(r"^(\d{1,2})\s*\.\s+(.+)$", line)
        if m_q and current is not None:
            current["questions"].append(m_q.group(2).strip())
    return sections


def parse_budget_tiers(path):
    """อ่าน data/การเงิน.txt → [{"tier": "B1", "label": "...", "desc": "..."}, ...]

    จับบรรทัดรูปแบบ '1. **จำกัดสูง** — คำอธิบาย' เรียงตามลำดับเลข 1..3
    """
    tiers = []
    for raw in read_text(path).splitlines():
        m = re.match(r"^(\d+)[.)]\s*\*\*(.+?)\*\*\s*[—–\-]\s*(.+)$", raw.strip())
        if m:
            tiers.append(
                {"tier": f"B{m.group(1)}", "label": m.group(2).strip(), "desc": m.group(3).strip()}
            )
    return tiers


@st.cache_data(show_spinner=False)
def load_data():
    interest = parse_interest_survey(INTEREST_FILE)
    functions = parse_function_survey(FUNCTION_FILE)
    budget_tiers = parse_budget_tiers(BUDGET_FILE)
    db = json.loads(read_text(FACULTY_DB_FILE))
    problems = []
    if len(interest) != len(CAT_CODES) or any(len(s["questions"]) != 20 for s in interest):
        detail = ", ".join(f"{s['code']}={len(s['questions'])}" for s in interest)
        problems.append(
            f"ความชอบ2.txt: parse ได้ {len(interest)} หมวด [{detail}] — คาดว่าจะมี {len(CAT_CODES)} หมวด x 20 ข้อ"
        )
    if len(functions) != 8 or any(len(s["questions"]) != 10 for s in functions):
        detail = ", ".join(f"{s['code']}={len(s['questions'])}" for s in functions)
        problems.append(
            f"MBTI_2.txt: parse ได้ {len(functions)} ฟังก์ชัน [{detail}] — คาดว่าจะมี 8 ฟังก์ชัน x 10 ข้อ"
        )
    if len(budget_tiers) != 3:
        problems.append(f"การเงิน.txt: parse ได้ {len(budget_tiers)} ระดับ — คาดว่าจะมี 3 ระดับ")
    faculties = db.get("facultyDatabase", [])
    if not faculties:
        problems.append("faculty_database_v2.json: ไม่พบ facultyDatabase หรือไม่มีรายการคณะ")

    survey_fn_codes = {s["code"] for s in functions}
    interest_codes = {s["code"] for s in interest}
    for f in faculties:
        bad_fns = [fn for fn in f.get("functions", []) if normalize_function_code(fn) not in survey_fn_codes]
        if bad_fns:
            problems.append(f"faculty_database_v2.json: คณะ '{f.get('name')}' อ้างถึงฟังก์ชัน {bad_fns} ที่ไม่พบใน MBTI_2.txt")
        bad_cats = [c.get("cat") for c in f.get("conditions", []) if c.get("cat") not in interest_codes]
        if bad_cats:
            problems.append(f"faculty_database_v2.json: คณะ '{f.get('name')}' อ้างถึงหมวดวิชา {bad_cats} ที่ไม่พบใน ความชอบ2.txt")

    return interest, functions, budget_tiers, faculties, problems


def ikey(code, i):
    return f"I:{code}:{i}"


def fkey(code, i):
    return f"F:{code}:{i}"


def init_state():
    st.session_state.setdefault("page", WELCOME_PAGE)
    st.session_state.setdefault("responses", {})
    st.session_state.setdefault("budget", None)


def go(page):
    st.session_state.page = page
    st.rerun()


def reset_all():
    st.session_state.clear()
    st.rerun()


def survey_keys(section, prefix, n_questions):
    return [f"{prefix}:{section['code']}:{qi}" for qi in range(n_questions)]


def keys_status(keys):
    responses = st.session_state.responses
    answered = sum(1 for k in keys if responses.get(k) is not None)
    return answered == len(keys), len(keys) - answered


def nav_buttons(prev_page, next_page, complete=True, missing=0, next_label="ถัดไป ➜"):
    col_back, col_next = st.columns(2, gap="small")
    with col_back:
        if st.button("⬅ ย้อนกลับ", width="stretch", disabled=prev_page is None):
            go(prev_page)
    with col_next:
        if st.button(next_label, type="primary", width="stretch", disabled=not complete):
            go(next_page)
    if not complete:
        st.warning(f"ยังตอบไม่ครบ เหลืออีก **{missing} ข้อ** กรุณาตอบให้ครบทุกข้อก่อนไปหน้าถัดไป")


def render_progress_bar(step_label):
    frac = min(st.session_state.page / TOTAL_STEPS, 1.0)
    st.progress(frac, text=f"ความคืบหน้ารวม {int(round(frac * 100))}% · {step_label}")


def render_question_radios(section, prefix, scale):
    keys = survey_keys(section, prefix, len(section["questions"]))
    for qi, question in enumerate(section["questions"]):
        key = keys[qi]
        value = st.session_state.responses.get(key)
        choice = st.radio(
            f"{qi + 1}. {question}",
            options=list(scale.keys()),
            format_func=lambda s, sc=scale: f"{s} · {sc[s]}",
            index=(value - 1) if value in scale else None,
            horizontal=True,
        )
        st.session_state.responses[key] = choice
    return keys


def render_welcome(n_faculties, n_interest_sections, n_function_sections, total_questions):
    st.title("🎓 แบบสอบถามแนะแนวคณะมหาวิทยาลัย")
    st.markdown(
        "แบบสอบถามนี้ช่วยให้คุณ**ค้นพบคณะ/สาขาที่เหมาะกับตัวเอง** "
        "โดยวิเคราะห์ 3 ด้าน ได้แก่ ความสนใจรายวิชา แนวโน้มการใช้ Cognitive Functions "
        "(Ti Te Fe Fi Se Si Ne Ni) และงบประมาณต่อเทอม แล้วจับคู่กับฐานข้อมูล "
        f"**{n_faculties} คณะ** เพื่อคำนวณ % ความเข้ากันได้ (Match%)"
    )

    c1, c2, c3 = st.columns(3)
    c1.info(f"📚 **{n_interest_sections * 20} ข้อ** ความสนใจ\n\n{n_interest_sections} หมวด (หมวดละ 20 ข้อ)")
    c2.info(f"🧠 **{n_function_sections * 10} ข้อ** Functions\n\n{n_function_sections} ฟังก์ชัน (ละ 10 ข้อ)")
    c3.info("💰 **1 คำถาม** งบประมาณ\n\nเลือก 1 จาก 3 ระดับ")

    st.divider()
    n_interest_pages = n_interest_sections
    total_pages = n_interest_pages + n_function_sections + 3
    st.markdown(
        f"""
        ### 📋 โครงสร้างแบบสอบถาม ({total_pages} หน้า)

        | ขั้นตอน | จำนวนหน้า | เนื้อหา |
        |---|---|---|
        | 1 | {n_interest_pages} หน้า | ความสนใจรายวิชา — ให้คะแนน 1–5 (1 = ไม่ใช่เลย, 5 = ใช่มากที่สุด) |
        | 2 | {n_function_sections} หน้า | Cognitive Functions — ให้คะแนน 1–5 ตามระดับที่ตรงกับตัวคุณ |
        | 3 | 1 หน้า | งบประมาณค่าใช้จ่ายต่อเทอมของครอบครัว |
        | 4 | 1 หน้า | ผลลัพธ์ 10 อันดับคณะ พร้อมเหตุผลและมหาวิทยาลัยแนะนำ |

        ⏱️ ใช้เวลาประมาณ **15–25 นาที** (รวม {total_questions} ข้อ) — ไม่มีคำตอบถูกหรือผิด
        ตอบตามความรู้สึกจริง และสามารถย้อนกลับมาแก้ไขข้อก่อนหน้าได้
        """
    )
    st.divider()
    st.warning(DISCLAIMER)

    if st.button("🚀 เริ่มทำแบบสอบถาม", type="primary", width="stretch"):
        go(1)


def render_interest_page(section, idx, total):
    render_progress_bar(f"หมวดที่ {idx}/{total}: {section['title']}")
    st.subheader(f"📚 หมวดที่ {idx}/{total}: {section['title']}")
    st.caption("ให้คะแนนแต่ละข้อ 1–5 · " + " · ".join(f"**{k}** = {v}" for k, v in INTEREST_SCALE.items()))
    st.divider()

    keys = render_question_radios(section, "I", INTEREST_SCALE)

    st.divider()
    complete, missing = keys_status(keys)
    prev_page = idx - 1
    next_page = idx + 1
    nav_buttons(prev_page, next_page, complete=complete, missing=missing)


def render_function_page(section, idx, total, n_interest_pages):
    render_progress_bar(f"ฟังก์ชันที่ {idx}/{total}: {section['code']}")
    st.subheader(f"🧠 ฟังก์ชันที่ {idx}/{total}: {section['code']} — {section['title']}")
    st.caption("ให้คะแนนตามระดับที่ข้อความตรงกับตัวคุณ · " + " · ".join(f"**{k}** = {v}" for k, v in FUNCTION_SCALE.items()))
    st.divider()

    keys = render_question_radios(section, "F", FUNCTION_SCALE)

    st.divider()
    complete, missing = keys_status(keys)
    current_page = n_interest_pages + idx
    nav_buttons(current_page - 1, current_page + 1, complete=complete, missing=missing)


def render_budget_page(tiers):
    render_progress_bar("คำถามงบประมาณ")
    st.subheader("💰 งบประมาณค่าใช้จ่ายทางการศึกษา")
    st.markdown("ค่าใช้จ่ายทางการศึกษาที่ครอบครัวสามารถสนับสนุนได้**ต่อเทอม** — เลือกระดับที่ตรงกับความเป็นจริงมากที่สุด")

    options = [t["tier"] for t in tiers]
    labels = {t["tier"]: f"{t['tier']} · {t['label']} — {t['desc']}" for t in tiers}
    choice = st.radio(
        "ระดับงบประมาณ",
        options=options,
        format_func=lambda tier: labels.get(tier, tier),
        index=options.index(st.session_state.budget) if st.session_state.budget in options else None,
        label_visibility="collapsed",
    )
    st.session_state.budget = choice

    st.divider()
    nav_buttons(BUDGET_PAGE - 1, RESULTS_PAGE, complete=choice is not None,
                missing=0 if choice else 1, next_label="📊 ดูผลลัพธ์ ➜")


def category_scores(responses, interest_sections):
    return {
        s["code"]: float(sum(responses[ikey(s["code"], i)] for i in range(len(s["questions"]))))
        for s in interest_sections
    }


def function_strengths(responses, function_sections):
    strengths = {}
    for s in function_sections:
        raw = sum(responses[fkey(s["code"], i)] for i in range(len(s["questions"])))
        strengths[s["code"]] = round((raw - 10) / (50 - 10) * 100, 1)
    return strengths


def dominant_function(strengths):
    return max(strengths, key=lambda fn: strengths[fn])


def calc_mbti_score(faculty, strengths, dom_fn):
    """mbtiScore ตาม scope ของแต่ละคณะ

    - D/A      : ค่า functionStrength สูงสุดในบรรดาฟังก์ชันของคณะ
    - Dominant : ถ้าฟังก์ชัน dominant ของผู้ใช้อยู่ในคณะ → ใช้ค่าของฟังก์ชันนั้นเต็มๆ
                 ถ้าไม่ → ค่า max ในคณะ x 0.5 (เครดิตบางส่วน)
    - Mixed    : Ni ต้องเป็น dominant หรือ Ti อยู่ใน D/A แบบปกติ → เอา max ของสองแบบ
    """
    funcs = [normalize_function_code(fn) for fn in faculty.get("functions", [])]
    if not funcs:
        return 0.0
    best_in_faculty = max(strengths.get(fn, 0.0) for fn in funcs)
    scope = faculty.get("scope", "D/A")

    if scope == "Dominant":
        if dom_fn in funcs:
            return float(strengths.get(dom_fn, 0.0))
        return round(best_in_faculty * 0.5, 1)

    if scope == "Mixed":
        ni_dominant_score = strengths.get("Ni", 0.0) if dom_fn == "Ni" else 0.0
        return round(max(ni_dominant_score, best_in_faculty), 1)

    return round(best_in_faculty, 1)


def calc_subject_score(faculty, cat_scores):
    """subjScore = min(ratio ของทุกเงื่อนไข) เพราะเงื่อนไขหมวดวิชาหลายข้อเป็น AND"""
    ratios = []
    for cond in faculty.get("conditions", []):
        required = float(cond.get("min", 0))
        got = float(cat_scores.get(cond.get("cat"), 0.0))
        ratios.append(min(got / required * 100.0, 100.0) if required > 0 else 100.0)
    return round(min(ratios), 1) if ratios else 0.0


def build_reason(faculty, strengths, cat_scores, condition_ratios):
    funcs = [normalize_function_code(fn) for fn in faculty.get("functions", [])]
    parts = []
    if funcs:
        top_fn = max(funcs, key=lambda fn: strengths.get(fn, 0.0))
        parts.append(f"ฟังก์ชันเด่น **{top_fn}** ({strengths.get(top_fn, 0):.0f}%)")

    conds = faculty.get("conditions", [])
    if conds:
        best_i = max(range(len(conds)), key=lambda i: condition_ratios[i])
        cond = conds[best_i]
        parts.append(
            f"หมวดวิชาเด่น **{CAT_TH.get(cond['cat'], cond['cat'])}** "
            f"{cat_scores.get(cond['cat'], 0):.0f}/100 (คณะนี้ต้องการ ≥ {cond['min']})"
        )
    return " · ".join(parts)


def rank_faculties(db_faculties, strengths, dom_fn, cat_scores):
    rows = []
    for faculty in db_faculties:
        mbti_score = calc_mbti_score(faculty, strengths, dom_fn)
        subject_score = calc_subject_score(faculty, cat_scores)
        match = round(WEIGHT_MBTI * mbti_score + WEIGHT_SUBJECT * subject_score, 1)
        ratios = [
            min(cat_scores.get(c.get("cat"), 0.0) / float(c["min"]) * 100.0, 100.0)
            for c in faculty.get("conditions", [])
            if float(c.get("min", 0)) > 0
        ]
        rows.append(
            {
                "name": faculty["name"],
                "group": faculty.get("group", ""),
                "match": match,
                "mbtiScore": mbti_score,
                "subjScore": subject_score,
                "reason": build_reason(faculty, strengths, cat_scores, ratios),
                "faculty": faculty,
            }
        )
    rows.sort(key=lambda r: (-r["match"], r["name"]))
    return rows


def render_results(db_faculties, interest_sections, function_sections, budget_tiers):
    st.title("📊 ผลลัพธ์: คณะที่แนะนำสำหรับคุณ")

    responses = st.session_state.responses
    cat_scores = category_scores(responses, interest_sections)
    strengths = function_strengths(responses, function_sections)
    dom_fn = dominant_function(strengths)
    ranked = rank_faculties(db_faculties, strengths, dom_fn, cat_scores)

    chosen_budget = st.session_state.budget
    tier_info = next((t for t in budget_tiers if t["tier"] == chosen_budget), {})

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"##### 🧠 ฟังก์ชันเด่นของคุณ: **{dom_fn}**")
        df_fn = pd.DataFrame(
            sorted(strengths.items(), key=lambda kv: -kv[1]),
            columns=["ฟังก์ชัน", "ความแข็งแรง (%)"],
        ).set_index("ฟังก์ชัน")
        st.bar_chart(df_fn, height=300)
    with col_b:
        st.markdown("##### 📚 คะแนนความสนใจรายหมวด (เต็ม 100)")
        df_cat = pd.DataFrame(
            [(CAT_TH.get(code, code), val) for code, val in cat_scores.items()],
            columns=["หมวดวิชา", "คะแนน"],
        ).set_index("หมวดวิชา")
        st.bar_chart(df_cat, height=300)

    st.divider()

    if ranked:
        st.success(f"🎯 คณะที่ Match สูงสุด: **{ranked[0]['name']}** ({ranked[0]['match']:.1f}%)")

    for rank, row in enumerate(ranked[:TOP_N], start=1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        faculty = row["faculty"]
        uni_rec = faculty.get("budget", {}).get(chosen_budget, "— ไม่ระบุข้อมูล —")
        with st.container(border=True):
            head_l, head_r = st.columns([3, 1])
            head_l.markdown(f"### {medal} {row['name']}\n`{GROUP_TH.get(row['group'], row['group'])}`")
            head_r.metric(label="Match%", value=f"{row['match']:.1f}%")
            st.progress(
                min(row["match"] / 100.0, 1.0),
                text=(
                    f"Match {row['match']:.1f}% "
                    f"(MBTI 30% = {row['mbtiScore']:.1f} · หมวดวิชา 70% = {row['subjScore']:.1f})"
                ),
            )
            st.markdown(f"💡 {row['reason']}")
            st.info(
                f"🎓 **มหาวิทยาลัยแนะนำ** (งบ {chosen_budget} · {tier_info.get('label', '')}): {uni_rec}"
            )

    if len(ranked) > TOP_N:
        with st.expander(f"ดูผลลัพธ์ทั้งหมด {len(ranked)} คณะ"):
            df_all = pd.DataFrame(
                [
                    {
                        "อันดับ": i,
                        "คณะ": r["name"],
                        "Match%": r["match"],
                        "MBTI (30%)": r["mbtiScore"],
                        "Subj (70%)": r["subjScore"],
                        "กลุ่ม": r["group"],
                    }
                    for i, r in enumerate(ranked, start=1)
                ]
            )
            st.dataframe(df_all, width="stretch", hide_index=True)

    st.divider()
    st.warning(DISCLAIMER)

    if st.button("🔄 ทำแบบสอบถามใหม่", width="stretch"):
        reset_all()


def main():
    st.set_page_config(page_title="แบบสอบถามแนะแนวคณะมหาวิทยาลัย", page_icon="🎓", layout="centered")
    init_state()

    interest_sections, function_sections, budget_tiers, db_faculties, problems = load_data()

    if problems:
        st.error("**พบปัญหาเกี่ยวกับไฟล์ข้อมูล กรุณาตรวจสอบโฟลเดอร์ data/**")
        for p in problems:
            st.markdown(f"- {p}")
        st.stop()

    page = st.session_state.page
    n_interest = len(interest_sections)
    n_functions = len(function_sections)

    if page == WELCOME_PAGE:
        total_questions = sum(len(s["questions"]) for s in interest_sections + function_sections)
        render_welcome(len(db_faculties), n_interest, n_functions, total_questions)
    elif 1 <= page <= n_interest:
        idx = page
        render_interest_page(interest_sections[idx - 1], idx, n_interest)
    elif n_interest < page <= n_interest + n_functions:
        idx = page - n_interest
        render_function_page(function_sections[idx - 1], idx, n_functions, n_interest_pages=n_interest)
    elif page == BUDGET_PAGE:
        render_budget_page(budget_tiers)
    elif page == RESULTS_PAGE:
        render_results(db_faculties, interest_sections, function_sections, budget_tiers)
    else:
        go(WELCOME_PAGE)


if __name__ == "__main__":
    main()
