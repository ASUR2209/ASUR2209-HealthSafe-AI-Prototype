import sqlite3
import json
import uuid
from datetime import datetime

DB_PATH = 'healthsafe.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    # ── Family accounts table ─────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS family_accounts (
            id TEXT PRIMARY KEY,
            head_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # ── Family members table ──────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS family_members (
            id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            relationship TEXT,
            conditions TEXT,
            medications TEXT,
            allergies TEXT,
            is_head INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (family_id) REFERENCES family_accounts(id)
        )
    ''')

    # ── Scan history table ────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            member_id TEXT NOT NULL,
            product_name TEXT,
            ingredients_text TEXT,
            verdict TEXT,
            score INTEGER,
            score_label TEXT,
            flagged_count INTEGER,
            conflict_count INTEGER,
            flagged_ingredients TEXT,
            source TEXT,
            scanned_at TEXT NOT NULL,
            FOREIGN KEY (family_id) REFERENCES family_accounts(id),
            FOREIGN KEY (member_id) REFERENCES family_members(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized!")


# ── Family account functions ──────────────────────────────────
def create_family(head_name: str, email: str, password: str) -> dict:
    """Create a new family account."""
    import hashlib
    conn = get_db()
    try:
        family_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        now = datetime.now().isoformat()

        conn.execute('''
            INSERT INTO family_accounts (id, head_name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (family_id, head_name, email, password_hash, now))

        # Auto-create head of family as first member
        member_id = str(uuid.uuid4())
        conn.execute('''
            INSERT INTO family_members
            (id, family_id, name, age, gender, relationship,
             conditions, medications, allergies, is_head, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (member_id, family_id, head_name, None, None,
              'Self', '[]', '[]', '[]', 1, now))

        conn.commit()
        return {
            "success": True,
            "family_id": family_id,
            "member_id": member_id,
            "message": f"Family account created for {head_name}"
        }

    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered"}
    finally:
        conn.close()


def login_family(email: str, password: str) -> dict:
    """Login to family account."""
    import hashlib
    conn = get_db()
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        row = conn.execute('''
            SELECT * FROM family_accounts
            WHERE email = ? AND password_hash = ?
        ''', (email, password_hash)).fetchone()

        if not row:
            return {"success": False, "error": "Invalid email or password"}

        members = get_family_members(row['id'])
        return {
            "success": True,
            "family_id": row['id'],
            "head_name": row['head_name'],
            "email": row['email'],
            "members": members
        }
    finally:
        conn.close()


# ── Family member functions ───────────────────────────────────
def add_family_member(family_id: str, name: str, age: int,
                       gender: str, relationship: str,
                       conditions: list, medications: list,
                       allergies: list) -> dict:
    """Add a new member to the family."""
    conn = get_db()
    try:
        # Check member limit — max 6
        count = conn.execute(
            'SELECT COUNT(*) as c FROM family_members WHERE family_id = ?',
            (family_id,)
        ).fetchone()['c']

        if count >= 6:
            return {
                "success": False,
                "error": "Maximum 6 family members allowed per account"
            }

        member_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn.execute('''
            INSERT INTO family_members
            (id, family_id, name, age, gender, relationship,
             conditions, medications, allergies, is_head, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            member_id, family_id, name, age, gender, relationship,
            json.dumps(conditions),
            json.dumps(medications),
            json.dumps(allergies),
            0, now
        ))

        conn.commit()
        return {
            "success": True,
            "member_id": member_id,
            "message": f"{name} added to family"
        }
    finally:
        conn.close()


def get_family_members(family_id: str) -> list:
    """Get all members of a family."""
    conn = get_db()
    try:
        rows = conn.execute(
            'SELECT * FROM family_members WHERE family_id = ? ORDER BY is_head DESC, created_at ASC',
            (family_id,)
        ).fetchall()

        members = []
        for row in rows:
            members.append({
                "member_id": row['id'],
                "name": row['name'],
                "age": row['age'],
                "gender": row['gender'],
                "relationship": row['relationship'],
                "conditions": json.loads(row['conditions'] or '[]'),
                "medications": json.loads(row['medications'] or '[]'),
                "allergies": json.loads(row['allergies'] or '[]'),
                "is_head": bool(row['is_head'])
            })
        return members
    finally:
        conn.close()


def update_family_member(member_id: str, family_id: str,
                          updates: dict) -> dict:
    """Update a family member's health profile."""
    conn = get_db()
    try:
        # Verify member belongs to this family
        row = conn.execute(
            'SELECT * FROM family_members WHERE id = ? AND family_id = ?',
            (member_id, family_id)
        ).fetchone()

        if not row:
            return {"success": False, "error": "Member not found"}

        conn.execute('''
            UPDATE family_members
            SET name = ?,
                age = ?,
                gender = ?,
                relationship = ?,
                conditions = ?,
                medications = ?,
                allergies = ?
            WHERE id = ? AND family_id = ?
        ''', (
            updates.get('name', row['name']),
            updates.get('age', row['age']),
            updates.get('gender', row['gender']),
            updates.get('relationship', row['relationship']),
            json.dumps(updates.get('conditions', json.loads(row['conditions'] or '[]'))),
            json.dumps(updates.get('medications', json.loads(row['medications'] or '[]'))),
            json.dumps(updates.get('allergies', json.loads(row['allergies'] or '[]'))),
            member_id, family_id
        ))

        conn.commit()
        return {"success": True, "message": "Profile updated"}
    finally:
        conn.close()


def delete_family_member(member_id: str, family_id: str) -> dict:
    """Delete a family member (cannot delete head of family)."""
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT * FROM family_members WHERE id = ? AND family_id = ?',
            (member_id, family_id)
        ).fetchone()

        if not row:
            return {"success": False, "error": "Member not found"}
        if row['is_head']:
            return {"success": False, "error": "Cannot delete head of family"}

        conn.execute(
            'DELETE FROM family_members WHERE id = ? AND family_id = ?',
            (member_id, family_id)
        )
        conn.commit()
        return {"success": True, "message": "Member removed"}
    finally:
        conn.close()


# ── Scan history functions ─────────────────────────────────────
def save_scan(family_id: str, member_id: str, product_name: str,
              ingredients_text: str, verdict: str, score: int,
              score_label: str, flagged_count: int, conflict_count: int,
              flagged_ingredients: list, source: str = "ocr") -> dict:
    """Save a scan result to history."""
    conn = get_db()
    try:
        scan_id = str(uuid.uuid4())
        conn.execute('''
            INSERT INTO scan_history
            (id, family_id, member_id, product_name, ingredients_text,
             verdict, score, score_label, flagged_count, conflict_count,
             flagged_ingredients, source, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scan_id, family_id, member_id, product_name,
            ingredients_text, verdict, score, score_label,
            flagged_count, conflict_count,
            json.dumps(flagged_ingredients),
            source, datetime.now().isoformat()
        ))
        conn.commit()
        return {"success": True, "scan_id": scan_id}
    finally:
        conn.close()


def get_scan_history(family_id: str, member_id: str = None,
                     limit: int = 20) -> list:
    """Get scan history for a family or specific member."""
    conn = get_db()
    try:
        if member_id:
            rows = conn.execute('''
                SELECT * FROM scan_history
                WHERE family_id = ? AND member_id = ?
                ORDER BY scanned_at DESC LIMIT ?
            ''', (family_id, member_id, limit)).fetchall()
        else:
            rows = conn.execute('''
                SELECT sh.*, fm.name as member_name
                FROM scan_history sh
                JOIN family_members fm ON sh.member_id = fm.id
                WHERE sh.family_id = ?
                ORDER BY sh.scanned_at DESC LIMIT ?
            ''', (family_id, limit)).fetchall()

        history = []
        for row in rows:
            history.append({
                "scan_id": row['id'],
                "member_id": row['member_id'],
                "member_name": row['member_name'] if 'member_name' in row.keys() else None,
                "product_name": row['product_name'],
                "verdict": row['verdict'],
                "score": row['score'],
                "score_label": row['score_label'],
                "flagged_count": row['flagged_count'],
                "conflict_count": row['conflict_count'],
                "source": row['source'],
                "scanned_at": row['scanned_at'],
            })
        return history
    finally:
        conn.close()


def get_family_dashboard(family_id: str) -> dict:
    """
    Get family health dashboard summary.
    Shows each member's recent scan stats and overall family score.
    """
    conn = get_db()
    try:
        members = get_family_members(family_id)
        dashboard = []

        for member in members:
            # Get last 10 scans for this member
            rows = conn.execute('''
                SELECT verdict, score, scanned_at
                FROM scan_history
                WHERE family_id = ? AND member_id = ?
                ORDER BY scanned_at DESC LIMIT 10
            ''', (family_id, member['member_id'])).fetchall()

            scans = [dict(r) for r in rows]
            total_scans = len(scans)

            if total_scans > 0:
                avg_score = round(sum(s['score'] for s in scans) / total_scans)
                unsafe_count = sum(1 for s in scans if s['verdict'] == 'Unsafe')
                last_scan = scans[0]['scanned_at']
            else:
                avg_score = None
                unsafe_count = 0
                last_scan = None

            dashboard.append({
                "member_id": member['member_id'],
                "name": member['name'],
                "relationship": member['relationship'],
                "age": member['age'],
                "conditions": member['conditions'],
                "is_head": member['is_head'],
                "stats": {
                    "total_scans": total_scans,
                    "avg_safety_score": avg_score,
                    "unsafe_scans": unsafe_count,
                    "last_scan": last_scan
                }
            })

        # Overall family score
        all_scores = [
            m['stats']['avg_safety_score']
            for m in dashboard
            if m['stats']['avg_safety_score'] is not None
        ]
        family_score = round(sum(all_scores) / len(all_scores)) if all_scores else None

        return {
            "family_id": family_id,
            "family_score": family_score,
            "members": dashboard
        }
    finally:
        conn.close()


# Initialize DB when module is imported
init_db()