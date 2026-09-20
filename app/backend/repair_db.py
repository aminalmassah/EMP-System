import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_DIR = os.path.join(ROOT, 'app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import app as backend_app

backend_app.init_db()
conn = backend_app.get_db()
print('users=', conn.execute('SELECT COUNT(*) FROM users').fetchone()[0])
print('employees=', conn.execute('SELECT COUNT(*) FROM employees').fetchone()[0])
print('systems=', conn.execute('SELECT COUNT(*) FROM systems').fetchone()[0])
print('qualifications=', conn.execute('SELECT COUNT(*) FROM qualifications').fetchone()[0])
conn.close()
print('Database initialized successfully.')
