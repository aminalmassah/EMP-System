# -*- coding: utf-8 -*-
"""
سكربت إضافة دورات مديول "متكامل" إلى جدول training_plan
(هذا الجدول يغذّي شاشة "تأهيل الموظفين" — مختلف عن training_schedule_2026
 الذي يغذّي شاشة "خطة تدريب الأنظمة 2026")

يُشغَّل مرة واحدة من نفس مجلد app/backend (أو يُمرَّر مسار قاعدة البيانات كوسيطة أولى)

الاستخدام:
    python seed_mutakamil_training_plan.py
    أو
    python seed_mutakamil_training_plan.py "C:\\path\\to\\data\\database.db"
"""
import sqlite3, os, sys, shutil
from datetime import datetime

# ---- تحديد مسار قاعدة البيانات ----
if len(sys.argv) > 1:
    DB_PATH = sys.argv[1]
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(HERE, '..', '..', 'data', 'database.db')
    DB_PATH = os.path.abspath(DB_PATH)

if not os.path.exists(DB_PATH):
    print(f"❌ لم يتم إيجاد قاعدة البيانات في: {DB_PATH}")
    print("   مرر المسار الصحيح كوسيطة: python seed_mutakamil_training_plan.py \"المسار\\data\\database.db\"")
    sys.exit(1)

print(f"📂 قاعدة البيانات: {DB_PATH}\n")

# ---- نسخة احتياطية تلقائية قبل أي تعديل ----
backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = os.path.join(backup_dir, f'database_before_seed_training_plan_{ts}.db')
shutil.copy2(DB_PATH, backup_path)
print(f"💾 نسخة احتياطية محفوظة في: {backup_path}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ---- نفس الدورات الست بالضبط (session دائماً 'صباحي' بما يطابق period='morning' بالجدول الآخر) ----
# (sys_name, trainer_name, days_count, start_date, end_date, hours_per_day)
courses = [
    ('المطاعم متكامل',          'حمد بلحارث',          4,  '2026-04-27', '2026-05-04', 3),
    ('الذهب متكامل',            'أحمد محمد عبد الله',  4,  '2026-07-06', '2026-07-09', 3),
    ('الموارد البشرية متكامل',  'أحمد محمد عبد الله',  6,  '2026-07-13', '2026-07-21', 3),
    ('المستشفيات متكامل',       'هيثم عوض',            10, '2026-07-27', '2026-08-11', 3),
    ('الفنادق متكامل',          'هيثم عوض',            4,  '2026-08-17', '2026-08-20', 3),
    ('النقل والطرود متكامل',    'أحمد محمد عبد الله',  4,  '2026-08-24', '2026-08-27', 3),
]

# ---- نفس المتدربين بالضبط لكل دورة (مطابقة لما أُدرج بـ training_schedule_2026) ----
attendees_by_sys = {
    'المطاعم متكامل':         ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','ترفة عبدالعزيز','مصطفى شوشة','عمر الصلوي','محمد الحسامي'],
    'الذهب متكامل':           ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','عمر الصلوي'],
    'الموارد البشرية متكامل': ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','مصطفى شوشة','عمر الصلوي','محمد الحسامي'],
    'المستشفيات متكامل':      ['أحمد محمد عبد الله','حمد بلحارث','هيثم عوض','محمد الحسامي'],
    'الفنادق متكامل':         ['أحمد محمد عبد الله','حمد بلحارث','محمد المطيري','هيثم عوض','ترفة عبدالعزيز','مصطفى شوشة','محمد الحسامي'],
    'النقل والطرود متكامل':   ['أحمد محمد عبد الله','حمد بلحارث','هيثم عوض','عمر الصلوي','محمد الحسامي'],
}

# ملاحظة: تعديلات التعارض السابقة (محمد الحسامي وعمر الصلوي) كانت على training_schedule_2026 فقط.
# هذا الجدول (training_plan) منفصل تماماً ولا يتأثر بتلك الحذوفات تلقائياً.
# إن أردت نفس الاستثناءات هنا، يجب تطبيقها يدوياً لاحقاً بسكربت منفصل بعد التأكيد.

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
    conn.close()
    sys.exit(1)

# ---- 2) فحص مسبق: هل الموظفون (محاضرون + متدربون) موجودون؟ ----
print("\n=== فحص الموظفين في جدول employees ===")
all_names = set()
for sys_name, trainer_name, *_ in courses:
    all_names.add(trainer_name)
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

# ---- 3) فحص عدم التكرار: هل هذه الدورات مُضافة مسبقاً بـ training_plan؟ ----
print("\n=== فحص عدم التكرار ===")
existing = c.execute("""
    SELECT t.id, s.name as sys_name, t.start_date
    FROM training_plan t JOIN systems s ON t.system_id = s.id
""").fetchall()
existing_pairs = {(r['sys_name'], r['start_date']): r['id'] for r in existing}

to_insert = []
for sys_name, trainer_name, days, sd, ed, hpd in courses:
    if (sys_name, sd) in existing_pairs:
        print(f"  ⏭ تخطّي '{sys_name}' ({sd}) — موجودة مسبقاً (id={existing_pairs[(sys_name, sd)]})")
        continue
    to_insert.append((sys_name, trainer_name, days, sd, ed, hpd))

if not to_insert:
    print("\n✅ لا توجد دورات جديدة لإضافتها (كلها موجودة مسبقاً)")
    conn.close()
    sys.exit(0)

# ---- 4) الإدراج الفعلي بـ training_plan ----
print(f"\n=== إدراج {len(to_insert)} دورة جديدة في training_plan ===")
inserted_ids = {}
for sys_name, trainer_name, days, sd, ed, hpd in to_insert:
    sys_id = sys_ids[sys_name]
    c.execute('''INSERT INTO training_plan
        (system_id, trainer, days_count, start_date, end_date, hours_per_day, session, notes)
        VALUES (?,?,?,?,?,?,?,?)''',
        (sys_id, trainer_name, days, sd, ed, hpd, 'صباحي', ''))
    new_id = c.lastrowid
    inserted_ids[sys_name] = new_id
    print(f"  ✅ {sys_name} (training_plan id={new_id}) — {sd} → {ed} | {days} يوم × {hpd}س")

# ---- 5) إسناد المتدربين عبر employee_training ----
print(f"\n=== إسناد المتدربين (employee_training) ===")
att_count = 0
for sys_name, training_id in inserted_ids.items():
    for emp_name in attendees_by_sys.get(sys_name, []):
        emp_id = emp_ids[emp_name]
        try:
            c.execute("""INSERT INTO employee_training (employee_id, training_id, completed)
                         VALUES (?,?,0)""", (emp_id, training_id))
            att_count += 1
        except sqlite3.IntegrityError:
            pass  # موجود مسبقاً (UNIQUE constraint)
    print(f"  ✅ {sys_name}: {len(attendees_by_sys.get(sys_name, []))} منفذ مُسند")

conn.commit()

# ---- 6) فحص ما بعد الإدراج ----
print("\n=== فحص ما بعد الإدراج ===")
all_ok = True
for sys_name, training_id in inserted_ids.items():
    row = c.execute("SELECT t.*, s.name as sys_name, s.erp_type FROM training_plan t JOIN systems s ON t.system_id=s.id WHERE t.id=?", (training_id,)).fetchone()
    cnt = c.execute("SELECT COUNT(*) as n FROM employee_training WHERE training_id=?", (training_id,)).fetchone()['n']
    if row and row['erp_type'] == 'متكامل' and cnt > 0:
        print(f"  ✅ تأكد: {sys_name} (id={training_id}) | erp_type={row['erp_type']} | {cnt} منفذ مُسند")
    else:
        print(f"  ❌ خطأ بالتحقق: {sys_name} (id={training_id})")
        all_ok = False

conn.close()

if all_ok:
    print(f"\n🎉 تم بنجاح — {len(to_insert)} دورة جديدة في training_plan، {att_count} سجل إسناد منفذ.")
    print(f"   النسخة الاحتياطية محفوظة في حال احتجت التراجع: {backup_path}")
else:
    print("\n⚠️ تنبيه: بعض الفحوصات بعد الإدراج لم تنجح — راجع الرسائل أعلاه.")
