# -*- coding: utf-8 -*-
"""Smoke test สำหรับ app.py: parser + อัลกอริทึม Match%"""
import importlib.util
import json
import sys
from pathlib import Path

APP = Path(r"C:\Users\phirw\Desktop\faculty-guidance\app.py")
spec = importlib.util.spec_from_file_location("guidance_app", APP)
m = importlib.util.module_from_spec(spec)
sys.modules["guidance_app"] = m
spec.loader.exec_module(m)

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)


# ---------- parse_interest_survey ----------
interest = m.parse_interest_survey(m.INTEREST_FILE)
check("interest: 5 sections", len(interest) == 5, f"got {len(interest)}")
check("interest codes", [s["code"] for s in interest] == ["M", "S", "L", "H", "A"],
      f"got {[s['code'] for s in interest]}")
check("interest 20 q each", all(len(s["questions"]) == 20 for s in interest),
      f"got {[len(s['questions']) for s in interest]}")
print("   titles:", [s["title"][:30] for s in interest])

# ---------- parse_function_survey ----------
funcs = m.parse_function_survey(m.FUNCTION_FILE)
expected_fns = ["Ti", "Te", "Fe", "Fi", "Se", "Si", "Ne", "Ni"]
check("functions: 8 sections", len(funcs) == 8, f"got {len(funcs)}")
check("function codes", [s["code"] for s in funcs] == expected_fns,
      f"got {[s['code'] for s in funcs]}")
check("functions 10 q each", all(len(s["questions"]) == 10 for s in funcs),
      f"got {[len(s['questions']) for s in funcs]}")

# ---------- parse_budget_tiers ----------
tiers = m.parse_budget_tiers(m.BUDGET_FILE)
check("budget: 3 tiers", len(tiers) == 3, f"got {len(tiers)}")
check("budget tiers B1-B3", [t["tier"] for t in tiers] == ["B1", "B2", "B3"])
for t in tiers:
    print(f"   {t['tier']} | {t['label']} | {t['desc'][:40]}...")

# ---------- db ----------
db = json.loads(m.read_text(m.FACULTY_DB_FILE))
faculties = db.get("facultyDatabase", [])
check("db faculties loaded", len(faculties) >= 60, f"got {len(faculties)}")
scopes = {}
for f in faculties:
    scopes[f["scope"]] = scopes.get(f["scope"], 0) + 1
    assert f.get("functions"), f"{f['name']} missing functions"
    for fn in f["functions"]:
        assert fn in expected_fns, f"{f['name']} bad function {fn}"
print("   scope distribution:", scopes)

# ---------- synthetic answers ----------
# M=80 S=80 H=80 A=80 L=20 (หมวดละ 20 ข้อ), functions: Ni=5 Ti=4 Te=2 Si=2 Ne=2 Fe=1 Fi=1 Se=1
responses = {}
cat_values = {"M": 4, "S": 4, "H": 4, "A": 4, "L": 1}
for s in interest:
    for i in range(len(s["questions"])):
        responses[m.ikey(s["code"], i)] = cat_values[s["code"]]
fn_values = {"Ni": 5, "Ti": 4, "Te": 2, "Si": 2, "Ne": 2, "Fe": 1, "Fi": 1, "Se": 1}
for s in funcs:
    for i in range(len(s["questions"])):
        responses[m.fkey(s["code"], i)] = fn_values[s["code"]]

cat_scores = m.category_scores(responses, interest)
strengths = m.function_strengths(responses, funcs)
dom_fn = m.dominant_function(strengths)

exp_cat = {"M": 80.0, "S": 80.0, "H": 80.0, "A": 80.0, "L": 20.0}
check("category_scores", cat_scores == exp_cat, f"got {cat_scores}")
exp_str = {"Ni": 100.0, "Ti": 75.0, "Te": 25.0, "Si": 25.0, "Ne": 25.0, "Fe": 0.0, "Fi": 0.0, "Se": 0.0}
check("function_strengths", strengths == exp_str, f"got {strengths}")
check("dominant = Ni", dom_fn == "Ni", f"got {dom_fn}")

# ---------- mbtiScore per scope ----------
by_name = {f["name"]: f for f in faculties}

cs = by_name["วิศวกรรมคอมพิวเตอร์/ซอฟต์แวร์"]          # D/A [Ti,Te]
check("D/A scope", m.calc_mbti_score(cs, strengths, dom_fn) == 75.0,
      f"got {m.calc_mbti_score(cs, strengths, dom_fn)}")

vet = by_name["สัตวแพทยศาสตร์"]                        # Dominant [Fi,Ni,Si]
check("Dominant in-funcs", m.calc_mbti_score(vet, strengths, dom_fn) == 100.0,
      f"got {m.calc_mbti_score(vet, strengths, dom_fn)}")

biz = by_name["บริหารธุรกิจ"]                          # Dominant [Te,Se,Fe] -> max25*0.5
check("Dominant not-in-funcs (x0.5)", m.calc_mbti_score(biz, strengths, dom_fn) == 12.5,
      f"got {m.calc_mbti_score(biz, strengths, dom_fn)}")

arch = by_name["สถาปัตยกรรมศาสตร์"]                    # Mixed [Ni,Ti]
check("Mixed (Ni dominant)", m.calc_mbti_score(arch, strengths, dom_fn) == 100.0,
      f"got {m.calc_mbti_score(arch, strengths, dom_fn)}")
arch2 = dict(arch)
s2 = dict(strengths)
s2["Ni"] = 30.0                                        # dominant จะเป็น Ti(75) แทน
dom2 = m.dominant_function(s2)
check("Mixed fallback to D/A way", m.calc_mbti_score(arch2, s2, dom2) == 75.0,
      f"got {m.calc_mbti_score(arch2, s2, dom2)} (dom={dom2})")

# ---------- subjScore (AND => min) ----------
commarts = by_name["นิเทศศาสตร์/วารสารศาสตร์"]         # L>=45, A>=35 -> min(44.4,100)
check("subjScore AND-min", m.calc_subject_score(commarts, cat_scores) == round(min(20/45*100, 100.0), 1),
      f"got {m.calc_subject_score(commarts, cat_scores)}")

# ---------- rank + Match formula spot check ----------
ranked = m.rank_faculties(faculties, strengths, dom_fn, cat_scores)
check("ranked count = db count", len(ranked) == len(faculties))
matches = [r["match"] for r in ranked]
check("sorted desc", matches == sorted(matches, reverse=True))

row_cs = next(r for r in ranked if r["name"] == cs["name"])
expect_match = round(0.3 * 75.0 + 0.7 * 100.0, 1)
check("Match formula (CompEng)", row_cs["match"] == expect_match,
      f"got {row_cs['match']} expect {expect_match}")

row_ca = next(r for r in ranked if r["name"] == commarts["name"])
mbti_ca = 75.0                                          # Ne,Se,Fe -> max=Ne25? no: [Ne,Se,Fe]->max 25
mbti_ca = m.calc_mbti_score(commarts, strengths, dom_fn)
subj_ca = m.calc_subject_score(commarts, cat_scores)
expect_match_ca = round(0.3 * mbti_ca + 0.7 * subj_ca, 1)
check("Match formula (CommArts)", row_ca["match"] == expect_match_ca,
      f"got {row_ca['match']} expect {expect_match_ca}")

print("\n--- TOP 10 ---")
for i, r in enumerate(ranked[:10], 1):
    print(f"{i:2}. {r['match']:6.1f}%  {r['name']}  [{r['group']}]")
    print(f"      {r['reason']}")
    print(f"      B1: {r['faculty']['budget'].get('B1','-')}")

# ---------- budget recommendation wiring ----------
b1_row = ranked[0]["faculty"]["budget"].get("B1")
check("budget rec exists for B1", isinstance(b1_row, str) and len(b1_row) > 0)

print()
if failures:
    print("FAILED:", failures)
    sys.exit(1)
print(f"ALL CHECKS PASSED ({len(faculties)} faculties)")

