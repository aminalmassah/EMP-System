# -*- coding: utf-8 -*-
"""
سكربت حل تعارض جداول التدريب (أونكس برو × متكامل)
يحذف 3 سجلات حضور محددة فقط من training_schedule_attendees
(لا يلمس جدول training_schedule_2026 نفسه، ولا أي بيانات تأهيل أخرى)

القرارات المؤكدة من المستخدم:
  1) محمد الحسامي يحضر دورات الأونكس فقط (الموارد البشرية، الأصول، الإنتاج)
     => يُحذف من: الموارد البشرية متكامل (id=15) + المستشفيات متكامل (id=16)
  2) عمر الصلوي لا يحضر "الأصول" (أونكس، id=5)، يحضر بقية دوراته كما هي
     => يُحذف من: الأصول (id=5) فقط
  3) هيثم عوض: لا تعديل (لا تعارض فعلي بعد استثناء الأونكس برو من الحساب)

الاستخدام:
    python fix_schedule_conflicts.py
    أو
    python fix_schedule_conflicts.py "C:\\path\\to\\data\\database.db"
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
    print("   مرر المسار الصحيح كوسيطة: python fix_schedule_conflicts.py \"المسار\\data\\database.db\"")
    sys.exit(1)

print(f"📂 قاعدة البيانات: {DB_PATH}\n")

# ---- نسخة احتياطية تلقائية قبل أي تعديل ----
backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = os.path.join(backup_dir, f'database_before_fix_conflicts_{ts}.db')
shutil.copy2(DB_PATH, backup_path)
print(f"💾 نسخة احتياطية محفوظة في: {backup_path}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ---- التعديلات المطلوبة: (employee_name, schedule_id, sys_name_للعرض) ----
removals = [
    ('محمد الحسامي', 15, 'الموارد البشرية متكامل'),
    ('محمد الحسامي', 16, 'المستشفيات متكامل'),
    ('عمر الصلوي',   5,  'الأصول'),
]

# ---- 1) فحص مسبق: التأكد من وجود الموظفين والسجلات قبل أي حذف ----
print("=== فحص مسبق ===")
to_delete = []
errors = []
for emp_name, schedule_id, sys_label in removals:
    emp_row = c.execute("SELECT id FROM employees WHERE name=? LIMIT 1", (emp_name,)).fetchone()
    if not emp_row:
        errors.append(f"❌ الموظف '{emp_name}' غير موجود في employees")
        continue
    emp_id = emp_row['id']

    att_row = c.execute(
        "SELECT id FROM training_schedule_attendees WHERE schedule_id=? AND employee_id=?",
        (schedule_id, emp_id)
    ).fetchone()
    if not att_row:
        errors.append(f"❌ لا يوجد سجل حضور لـ '{emp_name}' في الدورة id={schedule_id} ({sys_label}) — لا شيء لحذفه")
        continue

    to_delete.append((att_row['id'], emp_name, schedule_id, sys_label))
    print(f"  ✅ وُجد: {emp_name} ← {sys_label} (schedule_id={schedule_id}, attendee_row_id={att_row['id']})")

if errors:
    print("\n".join(errors))
    print("\n❌ توقف — لم يتم حذف أي سجل بسبب الأخطاء أعلاه. لا تغييرات تمت على قاعدة البيانات.")
    conn.close()
    sys.exit(1)

if not to_delete:
    print("\n✅ لا توجد سجلات تطابق الشروط — لا شيء لحذفه.")
    conn.close()
    sys.exit(0)

# ---- 2) الحذف الفعلي ----
print(f"\n=== حذف {len(to_delete)} سجل حضور ===")
for att_id, emp_name, schedule_id, sys_label in to_delete:
    c.execute("DELETE FROM training_schedule_attendees WHERE id=?", (att_id,))
    print(f"  🗑️ حُذف: {emp_name} ← {sys_label} (schedule_id={schedule_id})")

conn.commit()

# ---- 3) فحص ما بعد الحذف: التأكد من النتيجة ----
print("\n=== فحص ما بعد الحذف ===")
all_ok = True
for emp_name, schedule_id, sys_label in removals:
    emp_row = c.execute("SELECT id FROM employees WHERE name=? LIMIT 1", (emp_name,)).fetchone()
    emp_id = emp_row['id']
    still_there = c.execute(
        "SELECT id FROM training_schedule_attendees WHERE schedule_id=? AND employee_id=?",
        (schedule_id, emp_id)
    ).fetchone()
    if still_there:
        print(f"  ❌ خطأ: {emp_name} ما زال موجوداً في {sys_label} (schedule_id={schedule_id})")
        all_ok = False
    else:
        print(f"  ✅ تأكد: {emp_name} لم يعد ضمن حضور {sys_label}")

conn.close()

if all_ok:
    print(f"\n🎉 تم بنجاح — حُذفت {len(to_delete)} سجلات حضور بدقة، ولم تُمس أي بيانات أخرى.")
    print(f"   النسخة الاحتياطية محفوظة في حال احتجت التراجع: {backup_path}")
else:
    print("\n⚠️ تنبيه: بعض الفحوصات بعد الحذف لم تنجح — راجع الرسائل أعلاه.")
