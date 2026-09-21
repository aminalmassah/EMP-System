from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import sqlite3, os, hashlib, shutil, json as _json

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

DB_PATH = os.path.join(DATA_DIR, 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def next_code(table, prefix, col='code'):
    conn = get_db()
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    # توليد رمز فريد
    import time
    base = f"{prefix}{str(row+1).zfill(5)}"
    return base

def init_db():
    conn = get_db(); c = conn.cursor()

    # ===== التأهيل الشامل =====
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        role TEXT DEFAULT 'viewer', full_name TEXT DEFAULT '',
        employee_id INTEGER REFERENCES employees(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS systems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, erp_type TEXT NOT NULL,
        sys_category TEXT DEFAULT 'أساسي', description TEXT,
        active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 99
    )''')
    try: c.execute("ALTER TABLE systems ADD COLUMN sort_order INTEGER DEFAULT 99")
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, job_title TEXT, email TEXT, phone TEXT,
        active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 99,
        serial_code TEXT, branch TEXT,
        executor_type TEXT DEFAULT 'شركة الحلول النهائية لاعمال الحاسب الالي-منفذ',
        monthly_hours_goal INTEGER DEFAULT 0
    )''')
    for col in ['sort_order INTEGER DEFAULT 99','serial_code TEXT','branch TEXT',
                'executor_type TEXT','monthly_hours_goal INTEGER DEFAULT 0']:
        try: c.execute(f"ALTER TABLE employees ADD COLUMN {col}")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS qualifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER, system_id INTEGER,
        level_2025 INTEGER DEFAULT 4, level_2026_expected INTEGER DEFAULT 4, level_2026_actual INTEGER,
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (system_id) REFERENCES systems(id),
        UNIQUE(employee_id, system_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS training_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system_id INTEGER, trainer TEXT, days_count INTEGER,
        start_date TEXT, end_date TEXT, hours_per_day INTEGER DEFAULT 2,
        session TEXT DEFAULT 'مسائي', notes TEXT,
        FOREIGN KEY (system_id) REFERENCES systems(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS employee_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER, training_id INTEGER, completed INTEGER DEFAULT 0,
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (training_id) REFERENCES training_plan(id),
        UNIQUE(employee_id, training_id)
    )''')
    try: c.execute("ALTER TABLE employee_training ADD COLUMN completed INTEGER DEFAULT 0")
    except: pass

    # ===== الأعمال المنجزة =====
    c.execute('''CREATE TABLE IF NOT EXISTS exe_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, name TEXT NOT NULL, client_type TEXT DEFAULT 'شركة',
        country TEXT DEFAULT 'المملكة العربية السعودية', city TEXT,
        contact_name TEXT, phone TEXT, email TEXT, address TEXT,
        notes TEXT, active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS exe_task_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, name TEXT NOT NULL, description TEXT,
        color TEXT DEFAULT '#00c853', sort_order INTEGER DEFAULT 99, active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS exe_branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, name TEXT NOT NULL, company TEXT,
        address TEXT, phone TEXT, active INTEGER DEFAULT 1
    )''')

    # إسناد المهام - الهيكل الجديد
    c.execute('''CREATE TABLE IF NOT EXISTS exe_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, assignment_date TEXT,
        executor_id INTEGER REFERENCES employees(id),
        client_id INTEGER REFERENCES exe_clients(id),
        task_type TEXT, systems TEXT DEFAULT '[]',
        priority TEXT DEFAULT 'متوسطة',
        expected_hours REAL DEFAULT 0,
        planned_visits INTEGER DEFAULT 0,
        max_visits_per_client INTEGER DEFAULT 0,
        notes TEXT, status TEXT DEFAULT 'نشط',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # الخطط - الهيكل الجديد
    c.execute('''CREATE TABLE IF NOT EXISTS exe_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, assignment_id INTEGER REFERENCES exe_assignments(id),
        executor_id INTEGER REFERENCES employees(id),
        client_id INTEGER REFERENCES exe_clients(id),
        task_type TEXT, systems TEXT DEFAULT '[]',
        execution_time TEXT DEFAULT 'اليوم كامل',
        morning_hours REAL DEFAULT 3, evening_hours REAL DEFAULT 3,
        start_date TEXT, end_date TEXT,
        visit_hours REAL DEFAULT 3,
        planned_visits INTEGER DEFAULT 0,
        max_visits_per_client INTEGER DEFAULT 0,
        status TEXT DEFAULT 'نشط', notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # عمليات التنفيذ
    c.execute('''CREATE TABLE IF NOT EXISTS exe_execution_ops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, source TEXT DEFAULT 'بدون خطة',
        assignment_id INTEGER REFERENCES exe_assignments(id),
        plan_id INTEGER REFERENCES exe_plans(id),
        executor_id INTEGER REFERENCES employees(id),
        client_id INTEGER REFERENCES exe_clients(id),
        system_id INTEGER REFERENCES systems(id),
        visit_type TEXT DEFAULT 'زيارة ميدانية',
        completed_hours REAL DEFAULT 0,
        op_date TEXT, notes TEXT,
        is_extra INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # عمليات التدريب
    c.execute('''CREATE TABLE IF NOT EXISTS exe_training_ops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, source TEXT DEFAULT 'بدون خطة',
        assignment_id INTEGER REFERENCES exe_assignments(id),
        plan_id INTEGER REFERENCES exe_plans(id),
        trainer_id INTEGER REFERENCES employees(id),
        client_id INTEGER REFERENCES exe_clients(id),
        system_id INTEGER REFERENCES systems(id),
        training_type TEXT DEFAULT 'تدريب خارجي',
        is_first_time INTEGER DEFAULT 1,
        avg_hours_per_participant REAL DEFAULT 0.75,
        participants_count INTEGER DEFAULT 1,
        total_hours REAL DEFAULT 0.75,
        topics TEXT, train_date TEXT, notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # الاستشارات/الأنشطة
    c.execute('''CREATE TABLE IF NOT EXISTS exe_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, source TEXT DEFAULT 'بدون',
        assignment_id INTEGER REFERENCES exe_assignments(id),
        plan_id INTEGER REFERENCES exe_plans(id),
        executor_id INTEGER REFERENCES employees(id),
        client_id INTEGER REFERENCES exe_clients(id),
        activity_type TEXT DEFAULT 'استشارة',
        tickets_count INTEGER DEFAULT 1,
        avg_hours REAL DEFAULT 0.75,
        total_hours REAL DEFAULT 0.75,
        description TEXT, activity_date TEXT, notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # إضافة أعمدة قد تكون ناقصة في نسخ أقدم
    c.execute('''CREATE TABLE IF NOT EXISTS training_schedule_2026 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period TEXT NOT NULL,
        sort_order INTEGER DEFAULT 99,
        system_id INTEGER,
        sys_name TEXT,
        sys_no TEXT,
        lecturer_id INTEGER,
        lecturer_name TEXT,
        days_count INTEGER,
        start_date TEXT,
        end_date TEXT,
        hours_per_day REAL DEFAULT 2,
        total_hours REAL,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS training_schedule_attendees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        done INTEGER DEFAULT 0,
        UNIQUE(schedule_id, employee_id)
    )''')

    if c.execute("SELECT COUNT(*) FROM training_schedule_2026").fetchone()[0] == 0:
        _seed_rows = [
            ('morning',1,'الأونكس برو','101','نشوان الشميري',15,'2026-06-22','2026-07-15',2,30,''),
            ('evening',1,'نقاط البيع','102','محمود الشريف',3,'2026-06-17','2026-06-22',2,6,''),
            ('evening',2,'التوزيع','105','بسام الفقيه',4,'2026-06-23','2026-06-29',2,8,''),
            ('evening',3,'الموارد البشرية','103','بسام الفقيه',10,'2026-06-30','2026-07-15',2,20,''),
            ('evening',4,'الأصول','106','محفوظ حسان',3,'2026-07-16','2026-07-21',2,6,''),
            ('evening',5,'الإنتاج','104','محفوظ حسان',5,'2026-07-22','2026-07-29',2,10,''),
            ('evening',6,'المشاريع','113','محمود الشريف',6,'2026-07-30','2026-08-10',2,12,''),
            ('evening',7,'الورش','110','محمود الشريف',6,'2026-08-11','2026-08-19',2,12,''),
            ('evening',8,'المطاعم','108','امين المساح',6,'2026-08-20','2026-08-31',2,12,''),
            ('evening',9,'المستشفيات','111','هيثم عوض',4,'2026-09-01','2026-09-07',2,8,'تخلف اليوم الوطني'),
            ('evening',10,'صيانة الأصول','112','نشوان الشميري',4,'2026-09-08','2026-09-14',2,8,''),
            ('evening',11,'الأسطول','114','محفوظ حسان',4,'2026-09-15','2026-09-21',2,8,''),
        ]
        for period,order,sys_name,sys_no,lec_name,days,sd,ed,hpd,total,notes in _seed_rows:
            sys_row = c.execute("SELECT id FROM systems WHERE name=? LIMIT 1",(sys_name,)).fetchone()
            sys_id = sys_row[0] if sys_row else None
            lec_row = c.execute("SELECT id FROM employees WHERE name=? LIMIT 1",(lec_name,)).fetchone()
            lec_id = lec_row[0] if lec_row else None
            c.execute('''INSERT INTO training_schedule_2026
                (period,sort_order,system_id,sys_name,sys_no,lecturer_id,lecturer_name,days_count,start_date,end_date,hours_per_day,total_hours,notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (period,order,sys_id,sys_name,sys_no,lec_id,lec_name,days,sd,ed,hpd,total,notes))

    # إضافة المتدربين لكل دورة إن لم يكونوا موجودين
    seed_attendees_data = {
        'نقاط البيع':      ['محمود الشريف','نشوان الشميري','هيثم عوض','محمد سعيد','شهد الشريف','ترفة عبدالعزيز','وعد الغامدي','رفعت سمير','عدنان اليوسفي','صالح بالحارث','فائزة هتان'],
        'التوزيع':         ['هيثم عوض','شهد الشريف','رفعت سمير'],
        'الموارد البشرية': ['محمود الشريف','شهد الشريف','ترفة عبدالعزيز','رفعت سمير','طه عادل'],
        'الإنتاج':         ['محمود الشريف','نشوان الشميري','هيثم عوض','شهد الشريف','وعد الغامدي'],
        'المشاريع':        ['محمود الشريف','عمر الصلوي','محمد سعيد'],
        'المطاعم':         ['محمود الشريف'],
        'المستشفيات':      ['محمود الشريف','هيثم عوض','ترفة عبدالعزيز'],
        'صيانة الأصول':   ['محمود الشريف','نشوان الشميري','ترفة عبدالعزيز'],
        'الأسطول':         ['نشوان الشميري','عمر الصلوي','شهد الشريف','وعد الغامدي'],
        'الأونكس برو':     ['محمود الشريف','نشوان الشميري','هيثم عوض','عمر الصلوي','محمد سعيد','شهد الشريف','ترفة عبدالعزيز','وعد الغامدي','رفعت سمير','طه عادل','عدنان اليوسفي','صالح بالحارث'],
    }
    for sys_name, emp_names in seed_attendees_data.items():
        sched = c.execute("SELECT id FROM training_schedule_2026 WHERE sys_name=? LIMIT 1",(sys_name,)).fetchone()
        if not sched: continue
        sched_id = sched[0]
        for emp_name in emp_names:
            emp = c.execute("SELECT id FROM employees WHERE name=? LIMIT 1",(emp_name,)).fetchone()
            if not emp: continue
            try:
                c.execute("INSERT OR IGNORE INTO training_schedule_attendees (schedule_id,employee_id,done) VALUES (?,?,0)",(sched_id,emp[0]))
            except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS qual_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        system_id INTEGER NOT NULL,
        from_level INTEGER,
        to_level INTEGER NOT NULL,
        method TEXT,
        movement_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS login_ticker_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        sort_order INTEGER DEFAULT 99,
        active INTEGER DEFAULT 1
    )''')
    # تعبئة افتراضية إن كان الجدول فارغاً
    if c.execute("SELECT COUNT(*) FROM login_ticker_items").fetchone()[0] == 0:
        for i, label in enumerate(['التأهيل','التنفيذ','التدريب','الاستشارات','الجودة وتقييم الأداء'], 1):
            c.execute("INSERT INTO login_ticker_items (label, sort_order, active) VALUES (?,?,1)", (label, i*10))

    for _col in ['date_from TEXT','date_to TEXT','execution_time TEXT']:
        try: c.execute(f"ALTER TABLE exe_assignments ADD COLUMN {_col}")
        except: pass
    for _col in ['code TEXT','client_type TEXT','country TEXT','city TEXT','contact_name TEXT','address TEXT']:
        try: c.execute(f"ALTER TABLE exe_clients ADD COLUMN {_col}")
        except: pass
    for _tbl in ['exe_assignments','exe_plans','exe_execution_ops','exe_training_ops','exe_activities']:
        try: c.execute(f"ALTER TABLE {_tbl} ADD COLUMN code TEXT")
        except: pass

    # المستخدمون الافتراضيون
    admin_pass = hashlib.md5('admin123'.encode()).hexdigest()
    viewer_pass = hashlib.md5('view2026'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username,password,role,full_name) VALUES (?,?,?,?)",('admin',admin_pass,'admin','المدير'))
    c.execute("INSERT OR IGNORE INTO users (username,password,role,full_name) VALUES (?,?,?,?)",('viewer',viewer_pass,'viewer','مستخدم عرض'))

    # توليد رموز تسلسلية للموظفين بدون رمز
    emps_no_code = c.execute("SELECT id,rowid FROM employees WHERE serial_code IS NULL OR serial_code='' ORDER BY sort_order,id").fetchall()
    for i, emp in enumerate(emps_no_code, 1):
        c.execute("UPDATE employees SET serial_code=? WHERE id=?", (f"EX{i:04d}", emp[0]))

    conn.commit(); conn.close()

# ===== AUTH =====
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json; pw = hashlib.md5(d['password'].encode()).hexdigest()
    conn = get_db()
    user = conn.execute("SELECT u.*,e.name as emp_name, e.serial_code, e.branch, e.executor_type, e.monthly_hours_goal FROM users u LEFT JOIN employees e ON u.employee_id=e.id WHERE u.username=? AND u.password=?", (d['username'], pw)).fetchone()
    conn.close()
    if user: return jsonify({'success': True, 'user': dict(user)})
    return jsonify({'success': False, 'message': 'بيانات الدخول غير صحيحة'}), 401

# ===== USERS =====
@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    rows = conn.execute("SELECT u.id,u.username,u.role,u.full_name,u.employee_id,e.name as emp_name FROM users u LEFT JOIN employees e ON u.employee_id=e.id").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/users', methods=['POST'])
def add_user():
    d = request.json; pw = hashlib.md5(d['password'].encode()).hexdigest(); conn = get_db()
    conn.execute("INSERT INTO users (username,password,role,full_name,employee_id) VALUES (?,?,?,?,?)",
        (d['username'], pw, d.get('role','viewer'), d.get('full_name',''), d.get('employee_id')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    d = request.json; conn = get_db()
    if d.get('password'):
        pw = hashlib.md5(d['password'].encode()).hexdigest()
        conn.execute("UPDATE users SET role=?,full_name=?,password=?,employee_id=? WHERE id=?",
            (d['role'], d.get('full_name',''), pw, d.get('employee_id'), id))
    else:
        conn.execute("UPDATE users SET role=?,full_name=?,employee_id=? WHERE id=?",
            (d['role'], d.get('full_name',''), d.get('employee_id'), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    conn = get_db(); conn.execute("DELETE FROM users WHERE id=? AND username!='admin'", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== EMPLOYEES =====
@app.route('/api/employees', methods=['GET'])
def get_employees():
    conn = get_db()
    emps = conn.execute("SELECT * FROM employees WHERE active=1 ORDER BY COALESCE(sort_order,99),name").fetchall()
    result = []
    for e in emps:
        d = dict(e)
        d['total_systems'] = conn.execute("SELECT COUNT(*) FROM qualifications WHERE employee_id=?", (e['id'],)).fetchone()[0]
        d['done_systems'] = conn.execute("SELECT COUNT(*) FROM qualifications WHERE employee_id=? AND level_2025 IN (1,2)", (e['id'],)).fetchone()[0]
        result.append(d)
    conn.close(); return jsonify(result)

@app.route('/api/employees', methods=['POST'])
def add_employee():
    d = request.json; conn = get_db()
    # توليد رمز تسلسلي
    count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    serial = f"EX{count+1:04d}"
    conn.execute("INSERT INTO employees (name,job_title,email,phone,sort_order,serial_code,branch,executor_type,monthly_hours_goal) VALUES (?,?,?,?,?,?,?,?,?)",
        (d['name'], d.get('job_title',''), d.get('email',''), d.get('phone',''), d.get('sort_order',99),
         serial, d.get('branch',''), d.get('executor_type','شركة الحلول النهائية لاعمال الحاسب الالي-منفذ'), d.get('monthly_hours_goal',0)))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employees/<int:id>', methods=['PUT'])
def update_employee(id):
    d = request.json; conn = get_db()
    new_serial = d.get('serial_code','').strip()
    if new_serial:
        dup = conn.execute("SELECT id FROM employees WHERE serial_code=? AND id!=?", (new_serial, id)).fetchone()
        if dup:
            conn.close()
            return jsonify({'success':False,'message':'رمز الموظف مستخدم مسبقاً'}), 400
        conn.execute("UPDATE employees SET name=?,job_title=?,email=?,phone=?,sort_order=?,branch=?,executor_type=?,monthly_hours_goal=?,serial_code=? WHERE id=?",
            (d['name'], d.get('job_title',''), d.get('email',''), d.get('phone',''), d.get('sort_order',99),
             d.get('branch',''), d.get('executor_type',''), d.get('monthly_hours_goal',0), new_serial, id))
    else:
        conn.execute("UPDATE employees SET name=?,job_title=?,email=?,phone=?,sort_order=?,branch=?,executor_type=?,monthly_hours_goal=? WHERE id=?",
            (d['name'], d.get('job_title',''), d.get('email',''), d.get('phone',''), d.get('sort_order',99),
             d.get('branch',''), d.get('executor_type',''), d.get('monthly_hours_goal',0), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
def delete_employee(id):
    conn = get_db(); conn.execute("UPDATE employees SET active=0 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employees/<int:id>/remaining', methods=['GET'])
def get_remaining(id):
    conn = get_db()
    rows = conn.execute("""SELECT s.name,s.erp_type,q.level_2025 FROM systems s
        LEFT JOIN qualifications q ON q.system_id=s.id AND q.employee_id=?
        WHERE s.active=1 AND (q.level_2025 IS NULL OR q.level_2025 NOT IN (1,2))
        ORDER BY s.erp_type,s.name""", (id,)).fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

# ===== SYSTEMS =====
@app.route('/api/systems', methods=['GET'])
def get_systems():
    conn = get_db(); rows = conn.execute("SELECT * FROM systems WHERE active=1 ORDER BY erp_type,sys_category,sort_order,name").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/systems', methods=['POST'])
def add_system():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO systems (name,erp_type,sys_category,sort_order) VALUES (?,?,?,?)",
        (d['name'], d['erp_type'], d.get('sys_category','أساسي'), d.get('sort_order',99)))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/systems/<int:id>', methods=['PUT'])
def update_system(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE systems SET name=?,erp_type=?,sys_category=?,sort_order=? WHERE id=?",
        (d['name'], d['erp_type'], d.get('sys_category','أساسي'), d.get('sort_order',99), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/systems/<int:id>', methods=['DELETE'])
def delete_system(id):
    conn = get_db(); conn.execute("UPDATE systems SET active=0 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/systems/<int:id>/reorder', methods=['PUT'])
def reorder_system(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE systems SET sort_order=? WHERE id=?", (int(d['sort_order']), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== QUALIFICATIONS =====
@app.route('/api/qualifications', methods=['GET'])
def get_qualifications():
    conn = get_db()
    rows = conn.execute("SELECT q.*,e.name as emp_name,e.job_title,s.name as sys_name,s.erp_type,s.sys_category FROM qualifications q JOIN employees e ON q.employee_id=e.id JOIN systems s ON q.system_id=s.id WHERE e.active=1 AND s.active=1 ORDER BY e.name,s.erp_type,s.name").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/qualifications', methods=['POST'])
def save_qualification():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO qualifications (employee_id,system_id,level_2025,level_2026_expected,level_2026_actual) VALUES (?,?,?,?,?) ON CONFLICT(employee_id,system_id) DO UPDATE SET level_2025=excluded.level_2025,level_2026_expected=excluded.level_2026_expected,level_2026_actual=excluded.level_2026_actual",
        (d['employee_id'], d['system_id'], d.get('level_2025',4), d.get('level_2026_expected',4), d.get('level_2026_actual')))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== TRAINING PLAN =====
@app.route('/api/training', methods=['GET'])
def get_training():
    conn = get_db()
    rows = conn.execute("SELECT t.*,s.name as sys_name,s.erp_type FROM training_plan t JOIN systems s ON t.system_id=s.id ORDER BY t.start_date").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/training', methods=['POST'])
def add_training():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO training_plan (system_id,trainer,days_count,start_date,end_date,hours_per_day,session,notes) VALUES (?,?,?,?,?,?,?,?)",
        (d['system_id'], d['trainer'], d['days_count'], d['start_date'], d['end_date'], d.get('hours_per_day',2), d.get('session','مسائي'), d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/training/<int:id>', methods=['PUT'])
def update_training(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE training_plan SET system_id=?,trainer=?,days_count=?,start_date=?,end_date=?,hours_per_day=?,session=?,notes=? WHERE id=?",
        (d['system_id'], d['trainer'], d['days_count'], d['start_date'], d['end_date'], d.get('hours_per_day',2), d.get('session','مسائي'), d.get('notes',''), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/training/<int:id>', methods=['DELETE'])
def delete_training(id):
    conn = get_db(); conn.execute("DELETE FROM training_plan WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employee_training', methods=['GET'])
def get_emp_training():
    conn = get_db()
    rows = conn.execute("SELECT et.*,e.name as emp_name,e.job_title,s.name as sys_name,t.trainer,t.start_date,t.end_date,t.session FROM employee_training et JOIN employees e ON et.employee_id=e.id JOIN training_plan t ON et.training_id=t.id JOIN systems s ON t.system_id=s.id WHERE e.active=1 ORDER BY e.name,t.start_date").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/employee_training', methods=['POST'])
def save_emp_training():
    d = request.json; conn = get_db()
    conn.execute("INSERT OR IGNORE INTO employee_training (employee_id,training_id) VALUES (?,?)", (d['employee_id'], d['training_id']))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employee_training/<int:emp_id>/<int:train_id>', methods=['DELETE'])
def del_emp_training(emp_id, train_id):
    conn = get_db(); conn.execute("DELETE FROM employee_training WHERE employee_id=? AND training_id=?", (emp_id, train_id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/employee_training/complete', methods=['POST'])
def complete_emp_training():
    d = request.json; conn = get_db()
    conn.execute("UPDATE employee_training SET completed=? WHERE employee_id=? AND training_id=?", (d['completed'], d['employee_id'], d['training_id']))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = get_db()
    emp_count = conn.execute("SELECT COUNT(*) FROM employees WHERE active=1").fetchone()[0]
    sys_count = conn.execute("SELECT COUNT(*) FROM systems WHERE active=1").fetchone()[0]
    l25={1:0,2:0,3:0,4:0}; l26={1:0,2:0,3:0,4:0}
    for r in conn.execute("SELECT level_2025,COUNT(*) FROM qualifications q JOIN employees e ON q.employee_id=e.id WHERE e.active=1 GROUP BY level_2025").fetchall():
        if r[0]: l25[r[0]] = r[1]
    for r in conn.execute("SELECT level_2026_expected,COUNT(*) FROM qualifications q JOIN employees e ON q.employee_id=e.id WHERE e.active=1 GROUP BY level_2026_expected").fetchall():
        if r[0]: l26[r[0]] = r[1]
    total = sum(l25.values()) or 1; conn.close()
    return jsonify({'employees':emp_count,'systems':sys_count,'qual_percent':round((l25[1]+l25[2])/total*100),'levels_2025':l25,'levels_2026':l26,'total_qualifications':total})

# ==================== الأعمال المنجزة ====================

# --- العملاء ---
@app.route('/api/exe/clients', methods=['GET'])
def exe_clients():
    conn = get_db(); rows = conn.execute("SELECT * FROM exe_clients WHERE active=1 ORDER BY name").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/clients', methods=['POST'])
def exe_add_client():
    d = request.json; conn = get_db()
    # توليد رمز تلقائي دائماً (تجاهل ما أرسله المستخدم لمنع التكرار)
    code = next_code('exe_clients','CL')
    conn.execute("INSERT INTO exe_clients (code,name,client_type,country,city,contact_name,phone,email,address,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (code,d['name'],d.get('client_type','شركة'),d.get('country','المملكة العربية السعودية'),d.get('city',''),d.get('contact_name',''),d.get('phone',''),d.get('email',''),d.get('address',''),d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/clients/<int:id>', methods=['PUT'])
def exe_update_client(id):
    d = request.json; conn = get_db()
    # التحقق من تفرد الرمز عند التعديل
    new_code = d.get('code','').strip()
    if new_code:
        dup = conn.execute("SELECT id FROM exe_clients WHERE code=? AND id!=?", (new_code, id)).fetchone()
        if dup:
            conn.close()
            return jsonify({'success':False,'message':'رمز العميل مستخدم مسبقاً'}), 400
        conn.execute("UPDATE exe_clients SET code=?,name=?,client_type=?,country=?,city=?,contact_name=?,phone=?,email=?,address=?,notes=? WHERE id=?",
            (new_code,d['name'],d.get('client_type','شركة'),d.get('country',''),d.get('city',''),d.get('contact_name',''),d.get('phone',''),d.get('email',''),d.get('address',''),d.get('notes',''),id))
    else:
        conn.execute("UPDATE exe_clients SET name=?,client_type=?,country=?,city=?,contact_name=?,phone=?,email=?,address=?,notes=? WHERE id=?",
            (d['name'],d.get('client_type','شركة'),d.get('country',''),d.get('city',''),d.get('contact_name',''),d.get('phone',''),d.get('email',''),d.get('address',''),d.get('notes',''),id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/clients/<int:id>', methods=['DELETE'])
def exe_delete_client(id):
    conn = get_db(); conn.execute("UPDATE exe_clients SET active=0 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# --- أنواع المهام ---
@app.route('/api/exe/task_types', methods=['GET'])
def exe_task_types():
    conn = get_db(); rows = conn.execute("SELECT * FROM exe_task_types WHERE active=1 ORDER BY sort_order,name").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/task_types', methods=['POST'])
def exe_add_task_type():
    d = request.json; conn = get_db()
    code = next_code('exe_task_types','TT')
    conn.execute("INSERT INTO exe_task_types (code,name,description,color,sort_order) VALUES (?,?,?,?,?)",
        (code,d['name'],d.get('description',''),d.get('color','#00c853'),d.get('sort_order',99)))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/task_types/<int:id>', methods=['PUT'])
def exe_update_task_type(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE exe_task_types SET name=?,description=?,color=?,sort_order=? WHERE id=?",
        (d['name'],d.get('description',''),d.get('color','#00c853'),d.get('sort_order',99),id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/task_types/<int:id>', methods=['DELETE'])
def exe_delete_task_type(id):
    conn = get_db(); conn.execute("UPDATE exe_task_types SET active=0 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# --- الفروع ---
@app.route('/api/exe/branches', methods=['GET'])
def exe_branches():
    conn = get_db(); rows = conn.execute("SELECT * FROM exe_branches WHERE active=1 ORDER BY name").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/branches', methods=['POST'])
def exe_add_branch():
    d = request.json; conn = get_db()
    code = next_code('exe_branches','BR')
    conn.execute("INSERT INTO exe_branches (code,name,company,address,phone) VALUES (?,?,?,?,?)",
        (code,d['name'],d.get('company',''),d.get('address',''),d.get('phone','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/branches/<int:id>', methods=['PUT'])
def exe_update_branch(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE exe_branches SET name=?,company=?,address=?,phone=? WHERE id=?",
        (d['name'],d.get('company',''),d.get('address',''),d.get('phone',''),id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/branches/<int:id>', methods=['DELETE'])
def exe_delete_branch(id):
    conn = get_db(); conn.execute("UPDATE exe_branches SET active=0 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== إسناد المهام =====
@app.route('/api/exe/assignments', methods=['GET'])
def exe_get_assignments():
    conn = get_db()
    rows = conn.execute("""SELECT a.*,
        e.name as executor_name, e.serial_code as executor_code, e.job_title,
        c.name as client_name, c.city
        FROM exe_assignments a
        LEFT JOIN employees e ON a.executor_id=e.id
        LEFT JOIN exe_clients c ON a.client_id=c.id
        ORDER BY a.created_at DESC""").fetchall()
    result = []
    for r in rows:
        rd = dict(r)
        # إحصائيات الإسناد
        ex = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(completed_hours),0) as h FROM exe_execution_ops WHERE assignment_id=?", (r['id'],)).fetchone()
        tr = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(total_hours),0) as h FROM exe_training_ops WHERE assignment_id=?", (r['id'],)).fetchone()
        ac = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(total_hours),0) as h FROM exe_activities WHERE assignment_id=?", (r['id'],)).fetchone()
        plans_count = conn.execute("SELECT COUNT(*) FROM exe_plans WHERE assignment_id=?", (r['id'],)).fetchone()[0]
        rd['used_hours'] = float(ex['h']) + float(tr['h']) + float(ac['h'])
        rd['used_ops'] = ex['ops'] + tr['ops'] + ac['ops']
        rd['plans_count'] = plans_count
        result.append(rd)
    conn.close(); return jsonify(result)

@app.route('/api/exe/assignments', methods=['POST'])
def exe_add_assignment():
    d = request.json
    if not d.get('expected_hours') and not d.get('planned_visits'):
        return jsonify({'success':False,'message':'يجب تحديد الساعات المتوقعة أو عدد الزيارات المخططة'}), 400
    conn = get_db()
    code = next_code('exe_assignments','AS')
    conn.execute("INSERT INTO exe_assignments (code,assignment_date,executor_id,client_id,task_type,systems,priority,expected_hours,planned_visits,max_visits_per_client,execution_time,date_from,date_to,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, d.get('assignment_date',''), d.get('executor_id'), d['client_id'],
         d.get('task_type',''), _json.dumps(d.get('systems',[])),
         d.get('priority','متوسطة'), d.get('expected_hours',0),
         d.get('planned_visits',0), d.get('max_visits_per_client',0),
         d.get('execution_time','يوم كامل'), d.get('date_from',''), d.get('date_to',''),
         d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/assignments/<int:id>', methods=['PUT'])
def exe_update_assignment(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE exe_assignments SET assignment_date=?,executor_id=?,client_id=?,task_type=?,systems=?,priority=?,expected_hours=?,planned_visits=?,max_visits_per_client=?,execution_time=?,date_from=?,date_to=?,notes=?,status=?,updated_at=datetime('now','localtime') WHERE id=?",
        (d.get('assignment_date',''), d.get('executor_id'), d['client_id'],
         d.get('task_type',''), _json.dumps(d.get('systems',[])),
         d.get('priority','متوسطة'), d.get('expected_hours',0),
         d.get('planned_visits',0), d.get('max_visits_per_client',0),
         d.get('execution_time','يوم كامل'), d.get('date_from',''), d.get('date_to',''),
         d.get('notes',''), d.get('status','نشط'), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/assignments/<int:id>', methods=['DELETE'])
def exe_delete_assignment(id):
    conn = get_db(); conn.execute("DELETE FROM exe_assignments WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== الخطط =====
@app.route('/api/exe/plans', methods=['GET'])
def exe_get_plans():
    conn = get_db()
    rows = conn.execute("""SELECT p.*,
        e.name as executor_name, c.name as client_name,
        a.code as assignment_code
        FROM exe_plans p
        LEFT JOIN employees e ON p.executor_id=e.id
        LEFT JOIN exe_clients c ON p.client_id=c.id
        LEFT JOIN exe_assignments a ON p.assignment_id=a.id
        ORDER BY p.created_at DESC""").fetchall()
    result = []
    for r in rows:
        rd = dict(r)
        # انحراف الخطة
        ex = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(completed_hours),0) as h FROM exe_execution_ops WHERE plan_id=?", (r['id'],)).fetchone()
        tr = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(total_hours),0) as h FROM exe_training_ops WHERE plan_id=?", (r['id'],)).fetchone()
        daily_h = float(r['morning_hours'] or 0) + float(r['evening_hours'] or 0)
        rd['actual_hours'] = float(ex['h']) + float(tr['h'])
        rd['actual_visits'] = ex['ops'] + tr['ops']
        rd['daily_hours'] = daily_h
        rd['deviation_hours'] = rd['actual_hours'] - (float(r['planned_visits'] or 0) * float(r['visit_hours'] or 0))
        result.append(rd)
    conn.close(); return jsonify(result)

@app.route('/api/exe/plans', methods=['POST'])
def exe_add_plan():
    d = request.json; conn = get_db()
    code = next_code('exe_plans','PL')
    # جلب بيانات الإسناد تلقائياً إن وُجد
    aid = d.get('assignment_id')
    executor_id = d.get('executor_id')
    client_id = d.get('client_id')
    task_type = d.get('task_type','')
    systems = d.get('systems',[])
    if aid:
        a = conn.execute("SELECT * FROM exe_assignments WHERE id=?", (aid,)).fetchone()
        if a:
            if not executor_id: executor_id = a['executor_id']
            if not client_id: client_id = a['client_id']
            if not task_type: task_type = a['task_type']
            if not systems: systems = _json.loads(a['systems'] or '[]')
    conn.execute("INSERT INTO exe_plans (code,assignment_id,executor_id,client_id,task_type,systems,execution_time,morning_hours,evening_hours,start_date,end_date,visit_hours,planned_visits,max_visits_per_client,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, aid, executor_id, client_id, task_type, _json.dumps(systems),
         d.get('execution_time','اليوم كامل'), d.get('morning_hours',3), d.get('evening_hours',3),
         d.get('start_date',''), d.get('end_date',''),
         d.get('visit_hours',3), d.get('planned_visits',0), d.get('max_visits_per_client',0), d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/plans/<int:id>', methods=['PUT'])
def exe_update_plan(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE exe_plans SET execution_time=?,morning_hours=?,evening_hours=?,start_date=?,end_date=?,visit_hours=?,planned_visits=?,max_visits_per_client=?,systems=?,notes=?,status=? WHERE id=?",
        (d.get('execution_time','اليوم كامل'), d.get('morning_hours',3), d.get('evening_hours',3),
         d.get('start_date',''), d.get('end_date',''), d.get('visit_hours',3),
         d.get('planned_visits',0), d.get('max_visits_per_client',0),
         _json.dumps(d.get('systems',[])), d.get('notes',''), d.get('status','نشط'), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/plans/<int:id>', methods=['DELETE'])
def exe_delete_plan(id):
    conn = get_db(); conn.execute("DELETE FROM exe_plans WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== عمليات التنفيذ =====
@app.route('/api/exe/execution', methods=['GET'])
def exe_get_execution():
    conn = get_db()
    rows = conn.execute("""SELECT o.*,
        e.name as executor_name, c.name as client_name, s.name as sys_name,
        a.code as assignment_code, p.code as plan_code
        FROM exe_execution_ops o
        LEFT JOIN employees e ON o.executor_id=e.id
        LEFT JOIN exe_clients c ON o.client_id=c.id
        LEFT JOIN systems s ON o.system_id=s.id
        LEFT JOIN exe_assignments a ON o.assignment_id=a.id
        LEFT JOIN exe_plans p ON o.plan_id=p.id
        ORDER BY o.op_date DESC, o.created_at DESC""").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/execution', methods=['POST'])
def exe_add_execution():
    d = request.json; conn = get_db()
    code = next_code('exe_execution_ops','EX')
    # تحقق من الزيارات الإضافية
    is_extra = 0
    if d.get('plan_id'):
        plan = conn.execute("SELECT * FROM exe_plans WHERE id=?", (d['plan_id'],)).fetchone()
        if plan and plan['planned_visits'] > 0:
            used = conn.execute("SELECT COUNT(*) FROM exe_execution_ops WHERE plan_id=?", (d['plan_id'],)).fetchone()[0]
            if used >= plan['planned_visits']:
                is_extra = 1
    conn.execute("INSERT INTO exe_execution_ops (code,source,assignment_id,plan_id,executor_id,client_id,system_id,visit_type,completed_hours,op_date,notes,is_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, d.get('source','بدون خطة'), d.get('assignment_id'), d.get('plan_id'),
         d.get('executor_id'), d.get('client_id'), d.get('system_id'),
         d.get('visit_type','زيارة ميدانية'), d.get('completed_hours',0),
         d.get('op_date',''), d.get('notes',''), is_extra))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/execution/<int:id>', methods=['PUT'])
def exe_update_execution(id):
    d = request.json; conn = get_db()
    conn.execute("UPDATE exe_execution_ops SET executor_id=?,client_id=?,system_id=?,visit_type=?,completed_hours=?,op_date=?,notes=? WHERE id=?",
        (d.get('executor_id'), d.get('client_id'), d.get('system_id'),
         d.get('visit_type','زيارة ميدانية'), d.get('completed_hours',0), d.get('op_date',''), d.get('notes',''), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/execution/<int:id>', methods=['DELETE'])
def exe_delete_execution(id):
    conn = get_db(); conn.execute("DELETE FROM exe_execution_ops WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== عمليات التدريب =====
@app.route('/api/exe/training_ops', methods=['GET'])
def exe_get_training_ops():
    conn = get_db()
    rows = conn.execute("""SELECT o.*,
        e.name as trainer_name, c.name as client_name, s.name as sys_name,
        a.code as assignment_code, p.code as plan_code
        FROM exe_training_ops o
        LEFT JOIN employees e ON o.trainer_id=e.id
        LEFT JOIN exe_clients c ON o.client_id=c.id
        LEFT JOIN systems s ON o.system_id=s.id
        LEFT JOIN exe_assignments a ON o.assignment_id=a.id
        LEFT JOIN exe_plans p ON o.plan_id=p.id
        ORDER BY o.train_date DESC, o.created_at DESC""").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/training_ops', methods=['POST'])
def exe_add_training_op():
    d = request.json; conn = get_db()
    code = next_code('exe_training_ops','TR')
    total = float(d.get('avg_hours_per_participant', 0.75)) * int(d.get('participants_count', 1))
    conn.execute("INSERT INTO exe_training_ops (code,source,assignment_id,plan_id,trainer_id,client_id,system_id,training_type,is_first_time,avg_hours_per_participant,participants_count,total_hours,topics,train_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, d.get('source','بدون خطة'), d.get('assignment_id'), d.get('plan_id'),
         d.get('trainer_id'), d.get('client_id'), d.get('system_id'),
         d.get('training_type','تدريب خارجي'), 1 if d.get('is_first_time',True) else 0,
         d.get('avg_hours_per_participant',0.75), d.get('participants_count',1),
         total, d.get('topics',''), d.get('train_date',''), d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/training_ops/<int:id>', methods=['PUT'])
def exe_update_training_op(id):
    d = request.json; conn = get_db()
    total = float(d.get('avg_hours_per_participant',0.75)) * int(d.get('participants_count',1))
    conn.execute("UPDATE exe_training_ops SET trainer_id=?,client_id=?,system_id=?,training_type=?,is_first_time=?,avg_hours_per_participant=?,participants_count=?,total_hours=?,topics=?,train_date=?,notes=? WHERE id=?",
        (d.get('trainer_id'), d.get('client_id'), d.get('system_id'),
         d.get('training_type','تدريب خارجي'), 1 if d.get('is_first_time',True) else 0,
         d.get('avg_hours_per_participant',0.75), d.get('participants_count',1),
         total, d.get('topics',''), d.get('train_date',''), d.get('notes',''), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/training_ops/<int:id>', methods=['DELETE'])
def exe_delete_training_op(id):
    conn = get_db(); conn.execute("DELETE FROM exe_training_ops WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== الاستشارات/الأنشطة =====
@app.route('/api/exe/activities', methods=['GET'])
def exe_get_activities():
    conn = get_db()
    rows = conn.execute("""SELECT o.*,
        e.name as executor_name, c.name as client_name,
        a.code as assignment_code, p.code as plan_code
        FROM exe_activities o
        LEFT JOIN employees e ON o.executor_id=e.id
        LEFT JOIN exe_clients c ON o.client_id=c.id
        LEFT JOIN exe_assignments a ON o.assignment_id=a.id
        LEFT JOIN exe_plans p ON o.plan_id=p.id
        ORDER BY o.activity_date DESC, o.created_at DESC""").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/activities', methods=['POST'])
def exe_add_activity():
    d = request.json; conn = get_db()
    code = next_code('exe_activities','OA')
    total = float(d.get('avg_hours',0.75)) * int(d.get('tickets_count',1))
    conn.execute("INSERT INTO exe_activities (code,source,assignment_id,plan_id,executor_id,client_id,activity_type,tickets_count,avg_hours,total_hours,description,activity_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, d.get('source','بدون'), d.get('assignment_id'), d.get('plan_id'),
         d.get('executor_id'), d.get('client_id'), d.get('activity_type','استشارة'),
         d.get('tickets_count',1), d.get('avg_hours',0.75), total,
         d.get('description',''), d.get('activity_date',''), d.get('notes','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/activities/<int:id>', methods=['PUT'])
def exe_update_activity(id):
    d = request.json; conn = get_db()
    total = float(d.get('avg_hours',0.75)) * int(d.get('tickets_count',1))
    conn.execute("UPDATE exe_activities SET executor_id=?,client_id=?,activity_type=?,tickets_count=?,avg_hours=?,total_hours=?,description=?,activity_date=?,notes=? WHERE id=?",
        (d.get('executor_id'), d.get('client_id'), d.get('activity_type','استشارة'),
         d.get('tickets_count',1), d.get('avg_hours',0.75), total,
         d.get('description',''), d.get('activity_date',''), d.get('notes',''), id))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/activities/<int:id>', methods=['DELETE'])
def exe_delete_activity(id):
    conn = get_db(); conn.execute("DELETE FROM exe_activities WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== تأهيل الموظفين (الأعمال المنجزة) =====
@app.route('/api/exe/emp_quals', methods=['GET'])
def exe_emp_quals():
    conn = get_db()
    rows = conn.execute("""SELECT q.*,e.name as emp_name FROM exe_qualifications q
        LEFT JOIN employees e ON q.employee_id=e.id ORDER BY q.created_at DESC""").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/exe/emp_quals', methods=['POST'])
def exe_add_emp_qual():
    d = request.json; conn = get_db()
    code = next_code('exe_qualifications','QU')
    ccode = next_code('exe_qualifications','CRS')
    conn.execute("INSERT INTO exe_qualifications (code,employee_id,course_code,course_name,qual_date,hours,issuer,cert_number) VALUES (?,?,?,?,?,?,?,?)",
        (code,d.get('employee_id'),d.get('course_code',ccode),d['course_name'],d.get('qual_date',''),d.get('hours',40),d.get('issuer',''),d.get('cert_number','')))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/exe/emp_quals/<int:id>', methods=['DELETE'])
def exe_delete_emp_qual(id):
    conn = get_db(); conn.execute("DELETE FROM exe_qualifications WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({'success': True})

# ===== التقارير =====
@app.route('/api/exe/reports/summary', methods=['GET'])
def exe_reports_summary():
    conn = get_db()
    clients = conn.execute("SELECT * FROM exe_clients WHERE active=1 ORDER BY name").fetchall()
    result = []
    for cl in clients:
        cid = cl['id']
        ex = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(completed_hours),0) as h FROM exe_execution_ops WHERE client_id=?", (cid,)).fetchone()
        tr = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(total_hours),0) as h FROM exe_training_ops WHERE client_id=?", (cid,)).fetchone()
        ac = conn.execute("SELECT COUNT(*) as ops, COALESCE(SUM(total_hours),0) as h FROM exe_activities WHERE client_id=?", (cid,)).fetchone()
        asgns = conn.execute("SELECT * FROM exe_assignments WHERE client_id=?", (cid,)).fetchall()
        planned_h = sum(float(a['expected_hours'] or 0) for a in asgns)
        planned_v = sum(int(a['planned_visits'] or 0) for a in asgns)
        total_h = float(ex['h']) + float(tr['h']) + float(ac['h'])
        result.append({'id':cid,'name':cl['name'],'city':cl['city'],
            'exec_ops':ex['ops'],'train_ops':tr['ops'],'other_ops':ac['ops'],
            'total_hours':total_h,'planned_hours':planned_h,'planned_visits':planned_v,
            'assignments_count':len(asgns)})
    conn.close(); return jsonify(result)

# ===== النسخة الاحتياطية =====
@app.route('/api/backup/download', methods=['GET'])
def download_backup():
    backup = DB_PATH.replace('database.db','database_backup.db')
    shutil.copy2(DB_PATH, backup)
    return send_file(backup, as_attachment=True, download_name='database_backup.db')

@app.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    if 'file' not in request.files: return jsonify({'success':False,'message':'لا يوجد ملف'}), 400
    f = request.files['file']
    if not f.filename.endswith('.db'): return jsonify({'success':False,'message':'يجب رفع ملف .db'}), 400
    f.save(DB_PATH); return jsonify({'success':True,'message':'تم الاستعادة بنجاح'})



# --- شريط الواجهة الرئيسية (Login Ticker) ---
@app.route('/api/ticker', methods=['GET'])
def get_ticker():
    conn = get_db()
    rows = conn.execute("SELECT * FROM login_ticker_items WHERE active=1 ORDER BY sort_order, id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ticker/all', methods=['GET'])
def get_ticker_all():
    conn = get_db()
    rows = conn.execute("SELECT * FROM login_ticker_items ORDER BY sort_order, id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ticker', methods=['POST'])
def add_ticker():
    d = request.json
    if not d.get('label','').strip():
        return jsonify({'success':False,'message':'النص مطلوب'}), 400
    conn = get_db()
    max_order = conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM login_ticker_items").fetchone()[0]
    conn.execute("INSERT INTO login_ticker_items (label, sort_order, active) VALUES (?,?,1)",
        (d['label'].strip(), max_order+10))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/ticker/<int:id>', methods=['PUT'])
def update_ticker(id):
    d = request.json
    conn = get_db()
    conn.execute("UPDATE login_ticker_items SET label=?, sort_order=?, active=? WHERE id=?",
        (d.get('label','').strip(), d.get('sort_order',99), 1 if d.get('active',True) else 0, id))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/ticker/<int:id>', methods=['DELETE'])
def delete_ticker(id):
    conn = get_db()
    conn.execute("DELETE FROM login_ticker_items WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/ticker/reorder', methods=['POST'])
def reorder_ticker():
    d = request.json
    conn = get_db()
    for item in d.get('items',[]):
        conn.execute("UPDATE login_ticker_items SET sort_order=? WHERE id=?", (item['sort_order'], item['id']))
    conn.commit()
    conn.close()
    return jsonify({'success':True})



# --- حركات التأهيل (ترقيات المستوى) ---
@app.route('/api/qual_movements', methods=['GET'])
def get_qual_movements():
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, e.name as employee_name, e.serial_code as employee_code,
               s.name as system_name
        FROM qual_movements m
        LEFT JOIN employees e ON m.employee_id = e.id
        LEFT JOIN systems s ON m.system_id = s.id
        ORDER BY m.id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/qual_movements', methods=['POST'])
def add_qual_movement():
    d = request.json
    emp_id = d.get('employee_id')
    sys_id = d.get('system_id')
    to_level = d.get('to_level')
    if not emp_id or not sys_id or not to_level:
        return jsonify({'success':False,'message':'بيانات ناقصة'}), 400

    conn = get_db()
    # المستوى الحالي قبل الترقية (من qualifications)
    cur = conn.execute("SELECT level_2026_expected FROM qualifications WHERE employee_id=? AND system_id=?", (emp_id, sys_id)).fetchone()
    from_level = cur['level_2026_expected'] if cur else d.get('from_level', 4)

    # تسجيل الحركة
    conn.execute("""INSERT INTO qual_movements (employee_id,system_id,from_level,to_level,method,movement_date,notes)
                     VALUES (?,?,?,?,?,?,?)""",
        (emp_id, sys_id, from_level, to_level, d.get('method',''), d.get('movement_date',''), d.get('notes','')))

    # تحديث level_2026_expected في qualifications
    conn.execute("""INSERT INTO qualifications (employee_id,system_id,level_2025,level_2026_expected,level_2026_actual)
                     VALUES (?,?,?,?,?)
                     ON CONFLICT(employee_id,system_id) DO UPDATE SET level_2026_expected=excluded.level_2026_expected""",
        (emp_id, sys_id, 4, to_level, to_level))

    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/qual_movements/<int:id>', methods=['DELETE'])
def delete_qual_movement(id):
    conn = get_db()
    conn.execute("DELETE FROM qual_movements WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})



# --- خطة تدريب الأنظمة 2026 ---
@app.route('/api/training_schedule', methods=['GET'])
def get_training_schedule():
    conn = get_db()
    rows = conn.execute("SELECT * FROM training_schedule_2026 ORDER BY period, sort_order, id").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        att = conn.execute("""SELECT a.*, e.name as employee_name, e.serial_code as employee_code
                               FROM training_schedule_attendees a
                               LEFT JOIN employees e ON a.employee_id=e.id
                               WHERE a.schedule_id=?""", (d['id'],)).fetchall()
        d['attendees'] = [dict(x) for x in att]
        result.append(d)
    conn.close()
    return jsonify(result)

@app.route('/api/training_schedule/<int:id>', methods=['PUT'])
def update_training_schedule(id):
    d = request.json
    conn = get_db()
    sd = d.get('start_date','')
    ed = d.get('end_date','')
    hpd = d.get('hours_per_day', 2)
    days = d.get('days_count', 0)
    total = days * hpd
    conn.execute("""UPDATE training_schedule_2026 SET
        lecturer_id=?, lecturer_name=?, start_date=?, end_date=?, hours_per_day=?, total_hours=?, notes=?
        WHERE id=?""",
        (d.get('lecturer_id'), d.get('lecturer_name',''), sd, ed, hpd, total, d.get('notes',''), id))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/training_schedule/<int:id>/attendees', methods=['POST'])
def add_schedule_attendee(id):
    d = request.json
    emp_id = d.get('employee_id')
    if not emp_id:
        return jsonify({'success':False,'message':'الموظف مطلوب'}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO training_schedule_attendees (schedule_id, employee_id, done) VALUES (?,?,0)", (id, emp_id))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return jsonify({'success':True})

@app.route('/api/training_schedule/attendees/<int:att_id>', methods=['DELETE'])
def delete_schedule_attendee(att_id):
    conn = get_db()
    conn.execute("DELETE FROM training_schedule_attendees WHERE id=?", (att_id,))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/api/training_schedule/attendees/<int:att_id>/toggle', methods=['POST'])
def toggle_schedule_attendee(att_id):
    d = request.json
    done = 1 if d.get('done') else 0
    conn = get_db()
    att = conn.execute("SELECT * FROM training_schedule_attendees WHERE id=?", (att_id,)).fetchone()
    if not att:
        conn.close()
        return jsonify({'success':False,'message':'غير موجود'}), 404

    conn.execute("UPDATE training_schedule_attendees SET done=? WHERE id=?", (done, att_id))

    if done:
        sched = conn.execute("SELECT * FROM training_schedule_2026 WHERE id=?", (att['schedule_id'],)).fetchone()
        if sched and sched['system_id']:
            emp_id = att['employee_id']
            sys_id = sched['system_id']
            cur = conn.execute("SELECT level_2026_expected FROM qualifications WHERE employee_id=? AND system_id=?", (emp_id, sys_id)).fetchone()
            from_level = cur['level_2026_expected'] if cur else 4
            to_level = max(1, from_level - 1) if from_level else 3

            conn.execute("""INSERT INTO qual_movements (employee_id,system_id,from_level,to_level,method,movement_date,notes)
                             VALUES (?,?,?,?,?,?,?)""",
                (emp_id, sys_id, from_level, to_level, 'تدريب', sched['end_date'] or '', f"دورة {sched['sys_name']} ({sched['sys_no']})"))

            conn.execute("""INSERT INTO qualifications (employee_id,system_id,level_2025,level_2026_expected,level_2026_actual)
                             VALUES (?,?,?,?,?)
                             ON CONFLICT(employee_id,system_id) DO UPDATE SET level_2026_expected=excluded.level_2026_expected""",
                (emp_id, sys_id, 4, to_level, to_level))

    conn.commit()
    conn.close()
    return jsonify({'success':True})

if __name__ == '__main__':
    init_db()
    print("\n✅ التطبيق يعمل على: http://localhost:5000")
    print("✅ البيانات محفوظة في مجلد data\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
