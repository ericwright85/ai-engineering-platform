import json
import sqlite3
from datetime import datetime, timezone

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, state TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
        ''')

    def event(self, task_id, kind, detail):
        self.db.execute('INSERT INTO events(task_id,at,kind,detail) VALUES(?,?,?,?)', (task_id, datetime.now(timezone.utc).isoformat(), kind, json.dumps(detail)))

    def create(self, task_id, payload):
        with self.db:
            cursor = self.db.execute('INSERT OR IGNORE INTO tasks VALUES(?,?,?)', (task_id, 'analyzed', json.dumps(payload)))
            if cursor.rowcount:
                self.event(task_id, 'analysis.completed', {'findings':len(payload['findings'])})
        return self.get(task_id)

    def get(self, task_id):
        row = self.db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown task')
        return dict(id=row['id'], state=row['state'], **json.loads(row['payload']))

    def transition(self, task_id, expected, state, kind, detail):
        with self.db:
            changed = self.db.execute('UPDATE tasks SET state=? WHERE id=? AND state=?', (state, task_id, expected)).rowcount
            if changed != 1:
                raise ValueError('State transition conflict')
            self.event(task_id, kind, detail)

    def events(self, task_id):
        return [dict(row) for row in self.db.execute('SELECT * FROM events WHERE task_id=? ORDER BY id', (task_id,))]
