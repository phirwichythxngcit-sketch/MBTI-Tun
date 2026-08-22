# -*- coding: utf-8 -*-
"""AppTest E2E: จำลองผู้ใช้เดิน wizard ครบทั้ง 16 หน้าจนถึงผลลัพธ์"""
import random
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(r"C:\Users\phirw\Desktop\faculty-guidance\app.py")

random.seed(42)
failures = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        failures.append(name)


def find_button(at, substr):
    matches = [b for b in at.button if substr in b.label]
    return matches[0] if matches else None


def answer_all_radios(at, value=None):
    """ตอบ radio ที่ยังไม่ได้เลือกทุกตัวในหน้าปัจจุบัน"""
    answered = []
    for i, r in enumerate(list(at.radio)):
        v = value if value is not None else random.randint(1, 5)
        r.set_value(v)
        answered.append((i, v))
    return answered


at = AppTest.from_file(str(APP), default_timeout=60)
at.run()
check("welcome: no exception", not at.exception, str(at.exception)[:200])
check("welcome: page=0", at.session_state["page"] == 0)
start_btn = find_button(at, "เริ่มทำแบบสอบถาม")
check("welcome: start button found", start_btn is not None)

start_btn.click()
at.run()
check("page1: no exception", not at.exception)
check("page1: page=1", at.session_state["page"] == 1)
check("page1: 20 radios", len(at.radio) == 20, f"got {len(at.radio)}")

next_btn = find_button(at, "ถัดไป")
check("page1: next disabled before answering", next_btn.disabled is True)
check("page1: incomplete warning shown", len(at.warning) > 0)

for i, r in enumerate(list(at.radio)):
    if i < 19:
        r.set_value(4)
at.run()
check("page1: next STILL disabled at 19/20", find_button(at, "ถัดไป").disabled is True)
check("page1: warning still shown", len(at.warning) > 0)

answer_all_radios(at, 4)
at.run()
nb = find_button(at, "ถัดไป")
check("page1: next ENABLED at 20/20", nb.disabled is False)
check("page1: warning cleared", len(at.warning) == 0)

nb.click()
at.run()
check("page2: advanced to page=2", at.session_state["page"] == 2)

back_btn = find_button(at, "ย้อนกลับ")
back_btn.click()
at.run()
check("back: returned page=1", at.session_state["page"] == 1)
restored = [r.value for r in at.radio]
check("back: answers restored from session_state", all(v == 4 for v in restored),
      f"got {set(restored)}")

find_button(at, "ถัดไป").click()
at.run()

for page_idx in range(2, 6):
    check(f"interest p{page_idx}: 20 radios", len(at.radio) == 20, f"got {len(at.radio)}")
    answer_all_radios(at)
    at.run()
    b = find_button(at, "ถัดไป")
    check(f"interest p{page_idx}: next enabled", b.disabled is False)
    b.click()
    at.run()
    check(f"after p{page_idx}: no exception", not at.exception)

check("fn p1: reached function section", at.session_state["page"] == 6,
      f"got {at.session_state['page']}")
check("fn p1: 10 radios", len(at.radio) == 10, f"got {len(at.radio)}")

for fn_page in range(1, 9):
    if fn_page > 1:
        pass
    check(f"function p{fn_page}: 10 radios", len(at.radio) == 10, f"got {len(at.radio)}")
    answer_all_radios(at)
    at.run()
    b = find_button(at, "ถัดไป")
    check(f"function p{fn_page}: next enabled", b.disabled is False)
    b.click()
    at.run()
    if not at.exception:
        pass
    else:
        check(f"function p{fn_page}: no exception", False, str(at.exception)[:200])

check("budget: reached page=14", at.session_state["page"] == 14,
      f"got {at.session_state['page']}")
check("budget: 1 radio", len(at.radio) == 1, f"got {len(at.radio)}")
opts = at.radio[0].options
check("budget: 3 tier options with desc", len(opts) == 3
      and any("B1" in o and "จำกัดสูง" in o for o in opts)
      and any("B3" in o and "สนับสนุน" in o for o in opts),
      f"got {len(opts)} options")

res_btn = find_button(at, "ดูผลลัพธ์")
check("budget: result button locked before choosing", res_btn.disabled is True)
check("budget: missing warning", len(at.warning) > 0)

at.radio[0].set_value("B2")
at.run()
res_btn = find_button(at, "ดูผลลัพธ์")
check("budget: unlocked after choose", res_btn.disabled is False)
check("budget: session budget=B2", at.session_state["budget"] == "B2")

res_btn.click()
at.run()
check("results: no exception", not at.exception, str(at.exception)[:300])
check("results: page=15", at.session_state["page"] == 15)
metrics = list(at.metric)
check("results: 10 faculty cards (Match% metrics)", len(metrics) == 10, f"got {len(metrics)}")
all_md = "\n".join(md.value for md in at.markdown)
check("results: reason text present", "ฟังก์ชันเด่น" in all_md)
all_info = "\n".join(x.value for x in at.info)
check("results: university rec present", all_info.count("มหาวิทยาลัยแนะนำ") == 10,
      f"got {all_info.count('มหาวิทยาลัยแนะนำ')}")
check("results: rec uses chosen tier B2", "งบ B2" in all_info)
all_warn = "\n".join(x.value for x in at.warning)
check("results: disclaimer present (warning)", "เครื่องมือช่วยตัดสินใจ ไม่ใช่คำชี้ขาด" in all_warn)
successes = " ".join(s.value for s in at.success)
check("results: top-1 banner", "Match" in successes, successes[:80])

reset_btn = find_button(at, "ทำแบบสอบถามใหม่")
check("results: reset button found", reset_btn is not None)
reset_btn.click()
at.run()
check("reset: back to welcome page=0", at.session_state["page"] == 0)
check("reset: responses cleared", at.session_state["responses"] == {})
check("reset: budget cleared", at.session_state["budget"] is None)
check("reset: no exception", not at.exception)

print()
if failures:
    print("FAILED:", failures)
    sys.exit(1)
print("E2E WIZARD: ALL CHECKS PASSED")
