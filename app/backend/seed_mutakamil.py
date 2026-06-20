# -*- coding: utf-8 -*-
"""
سكربت إضافة دورات مديول "متكامل" إلى training_schedule_2026
يُشغَّل مرة واحدة من نفس مجلد app/backend (أو يُمرَّر مسار قاعدة البيانات كوسيطة أولى)

الاستخدام:
    python seed_mutakamil.py
    أو
    python seed_mutakamil.py "C:\\path\\to\\data\\database.db"
"""
import sqlite3, os, sys

# ---- تحديد مسار قاعدة البيانات ----
if len(sys.argv) > 1:
    DB_PATH = sys.argv[1]
else:
    # نفس منطق app.py: data/database.db بجانب مجلد app
    HERE = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(HERE, '..', '..', 'data', 'database.db')
    DB_PATH = os.path.abspath(DB_PATH)

if not os.path.exists(DB_PATH):
    print(f"❌ لم يتم إيجاد قاعدة البيانات في: {DB_PATH}")
    print("   مرر المسار الصحيح كوسيطة: python seed_mutakamil.py \"المسار\\data\\database.db\"")
    sys.exit(1)

print(f"📂 قاعدة البيانات: {DB_PATH}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ---- الدورات الست (period دائماً 'morning' حسب التأكيد) ----
# (sys_name, lecturer_name, days_count, start_date, end_date, hours_per_day)
courses = [
    ('المطاعم متكامل',          'حمد بلحارث',          4,  '2026-04-27', '2026-05-04', 3),
    ('الذهب متكامل',            'أحمد محمد عبد الله',  4,  '2026-07-06', '2026-07-09', 3),
    ('الموارد البشرية متكامل',  'أحمد محمد عبد الله',  6,  '2026-07-13', '2026-07-21', 3),
    ('المستشفيات متكامل',       'هيثم عوض',            10, '2026-07-27', '2026-08-11', 3),
    ('الفنادق متكامل',          'هيثم عوض',            4,  '2026-08-17', '2026-08-20', 3),
    ('النقل والطرود متكامل',    'أحمد محمد عبد الله',  4,  '2026-08-24', '2026-08-27', 3),
]

# ---- المتدربون لكل دورة ----
attendees_by_sys = {
    'المطاعم متكامل':  ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','ترفة عبدالعزيز','مصطفى شوشة','عمر الصلوي','محمد الحسامي'],
    'الذهب متكامل':        ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','عمر الصلوي'],
    'الموارد البشرية متكامل':  ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','مصطفى شوشة','عمر الصلوي','محمد الحسامي'],
    'المستشفيات متكامل':     ['أحمد محمد عبد الله','حمد بلحارث','هيثم عوض','محمد الحسامي'],
    'الفنادق متكامل':        ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','ترفة عبدالعزيز','مصطفى شوشة','محمد الحسامي'],
    'النقل والطرود متكامل':        ['أحمد محمد عبد الله','حمد بلحارث','هيثم عوض','عمر الصلوي','محمد الحسامي'],
}

# ---- 1) فحص مسبق: هل الأنظمة موجودة فعلاً بـ erp_type='متكامل'؟ ----
print("=== فحص الأنظمة في جدول systems ===")
missing_systems = []
sys_ids = {}
for sys_name, *_ in courses:
    row = c.execute("SELECT id, erp_type FROM systems WHERE name=? LIMIT 1", (sys_name,)).fetchone()
    if row:
        sys_ids[sys_name] = row['id']
        flag = "✅" if row['erp_type'] == 'متكامل' else f"⚠️ erp_type='{row['erp_type']}' (متوقع 'متكامل')"
        print(f"  {sys_name}: id={row['id']} {flag}")
    else:
        missing_systems.append(sys_name)
        print(f"  {sys_name}: ❌ غير موجود في جدول systems")

if missing_systems:
    print(f"\n❌ توقف — الأنظمة التالية غير موجودة في systems: {missing_systems}")
    print("   أضفها أولاً من شاشة 'إدارة البرامج' في النظام، ثم أعد تشغيل السكربت.")
    conn.close()
    sys.exit(1)

# ---- 2) فحص مسبق: هل الموظفون (محاضرون + متدربون) موجودون؟ ----
print("\n=== فحص الموظفين في جدول employees ===")
all_names = set()
for sys_name, lec_name, *_ in courses:
    all_names.add(lec_name)
for names in attendees_by_sys.values():
    all_names.update(names)

emp_ids = {}
missing_emps = []
for name in sorted(all_names):
    row = c.execute("SELECT id FROM employees WHERE name=? LIMIT 1", (name,)).fetchone()
    if row:
        emp_ids[name] = row['id']
    else:
        missing_emps.append(name)

if missing_emps:
    print(f"❌ توقف — الموظفون التالية غير موجودين في employees: {missing_emps}")
    conn.close()
    sys.exit(1)
print(f"  ✅ كل الموظفين ({len(emp_ids)}) موجودون")

# ---- 3) فحص: هل هذه الدورات مُضافة مسبقاً؟ (تجنب التكرار) ----
print("\n=== فحص عدم التكرار ===")
existing = c.execute("SELECT sys_name, start_date FROM training_schedule_2026").fetchall()
existing_pairs = {(r['sys_name'], r['start_date']) for r in existing}

to_insert = []
for sys_name, lec_name, days, sd, ed, hpd in courses:
    if (sys_name, sd) in existing_pairs:
        print(f"  ⏭ تخطّي '{sys_name}' ({sd}) — موجودة مسبقاً")
        continue
    to_insert.append((sys_name, lec_name, days, sd, ed, hpd))

if not to_insert:
    print("\n✅ لا توجد دورات جديدة لإضافتها (كلها موجودة مسبقاً)")
    conn.close()
    sys.exit(0)

# ---- 4) تحديد sort_order التالي (بعد آخر دورة موجودة) ----
max_order_row = c.execute("SELECT MAX(sort_order) as m FROM training_schedule_2026").fetchone()
next_order = (max_order_row['m'] or 0) + 1

# ---- 5) الإدراج الفعلي ----
print(f"\n=== إدراج {len(to_insert)} دورة جديدة ===")
inserted_schedule_ids = {}
for sys_name, lec_name, days, sd, ed, hpd in to_insert:
    total_hours = days * hpd
    sys_id = sys_ids[sys_name]
    lec_id = emp_ids[lec_name]
    c.execute('''INSERT INTO training_schedule_2026
        (period, sort_order, system_id, sys_name, sys_no, lecturer_id, lecturer_name,
         days_count, start_date, end_date, hours_per_day, total_hours, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        ('morning', next_order, sys_id, sys_name, '', lec_id, lec_name,
         days, sd, ed, hpd, total_hours, ''))
    new_id = c.lastrowid
    inserted_schedule_ids[sys_name] = new_id
    next_order += 1
    print(f"  ✅ {sys_name} (id={new_id}) — {sd} → {ed} | {days} يوم × {hpd}س = {total_hours}س")

# ---- 6) إضافة المتدربين لكل دورة جديدة ----
print(f"\n=== إضافة المتدربين ===")
att_count = 0
for sys_name, schedule_id in inserted_schedule_ids.items():
    for emp_name in attendees_by_sys.get(sys_name, []):
        emp_id = emp_ids[emp_name]
        try:
            c.execute("""INSERT INTO training_schedule_attendees (schedule_id, employee_id, done)
                         VALUES (?,?,0)""", (schedule_id, emp_id))
            att_count += 1
        except sqlite3.IntegrityError:
            pass  # موجود مسبقاً (UNIQUE constraint)
    print(f"  ✅ {sys_name}: {len(attendees_by_sys.get(sys_name, []))} متدرب")

conn.commit()
conn.close()

print(f"\n🎉 تم بنجاح — {len(to_insert)} دورة جديدة، {att_count} سجل حضور")
