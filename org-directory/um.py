"""User management: passwords, sessions, profile, recommended files."""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPLOADS = HERE / "data" / "uploads"
DEMO_PASSWORD = "Demo@2026"
SESSION_HOURS = 12
COOKIE = "hnwms_session"
PBKDF2_ROUNDS = 120_000
MAX_UPLOAD = 8 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"}
ADMIN_ROLES = {"SYS_ADMIN", "ORG_ADMIN", "HR", "DON", "ADON", "WORKFORCE_MGR"}

DOC_TYPES = [
    ("NATIONAL_ID", "National ID / Iqama", "MANDATORY", "Copy of national ID or Iqama"),
    ("SCFHS_LICENSE", "SCFHS professional license", "MANDATORY", "Nursing registration / classification"),
    ("NURSING_QUAL", "Nursing qualification", "MANDATORY", "Diploma / BSN / higher degree"),
    ("BLS", "BLS / CPR certificate", "MANDATORY", "Basic life support"),
    ("MEDICAL_FIT", "Medical clearance", "MANDATORY", "Pre-employment fitness for duty"),
    ("CONTRACT", "Employment contract", "REQUIRED", "Signed contract"),
    ("PHOTO", "Staff photo", "REQUIRED", "ID photograph"),
    ("ACLS", "ACLS certificate", "REQUIRED", "For ICU / ED / critical care"),
    ("PALS", "PALS certificate", "ADDITIONAL", "For pediatrics / maternity"),
    ("SPECIALTY", "Specialty certificate", "ADDITIONAL", "Unit-specific qualification"),
    ("EXPERIENCE", "Experience letter", "ADDITIONAL", "Previous employer verification"),
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
    return salt, dk.hex()


def verify_password(password: str, salt: str, expected_hex: str) -> bool:
    _, got = hash_password(password, salt)
    return secrets.compare_digest(got, expected_hex)


def slug_username(name: str, code: str, used: set[str]) -> str:
    raw = re.sub(r"[^a-z0-9]+", ".", (name or "").lower()).strip(".")
    if not raw:
        raw = re.sub(r"[^a-z0-9]+", ".", code.lower()).strip(".")
    candidate = raw
    i = 2
    while candidate in used:
        extra = code.split(".")[-1].lower()
        candidate = f"{raw}.{extra}" if i == 2 else f"{raw}.{extra}{i}"
        i += 1
    used.add(candidate)
    return candidate


def cookie_token(header: str | None) -> str | None:
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE and v:
            return v.strip()
    return None


def request_token(headers, override: str | None = None) -> str | None:
    if override:
        return override.strip()
    auth = (headers.get("Authorization") if hasattr(headers, "get") else None) or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    extra = headers.get("X-Session-Token") if hasattr(headers, "get") else None
    if extra:
        return extra.strip()
    return cookie_token(headers.get("Cookie") if hasattr(headers, "get") else None)


def user_from_conn(conn, headers, token_override: str | None = None) -> dict | None:
    token = request_token(headers, token_override)
    if not token:
        return None
    now = now_iso()
    row = conn.execute(
        """SELECT u.user_id, u.username, u.status, u.must_change, u.last_login,
                  p.persona_id, p.persona_code, p.display_name, p.job_title, p.category
           FROM app_session s
           JOIN app_user u ON u.user_id = s.user_id
           JOIN persona p ON p.persona_id = u.persona_id
           WHERE s.token = ? AND s.expires_at >= ? AND u.status = 'ACTIVE'""",
        (token, now),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["roles"] = [
        r[0]
        for r in conn.execute(
            """SELECT r.role_code FROM role_grant g
               JOIN role r ON r.role_id = g.role_id
               WHERE g.persona_id = ? AND g.status = 'ACTIVE'""",
            (d["persona_id"],),
        ).fetchall()
    ]
    d["can_admin_users"] = any(r in ADMIN_ROLES for r in d["roles"])
    return d


def set_cookie(token: str, hours: int = SESSION_HOURS, secure: bool = False) -> str:
    parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", f"Max-Age={hours * 3600}"]
    if secure:
        parts.extend(["SameSite=None", "Secure"])
    else:
        parts.append("SameSite=Lax")
    return "; ".join(parts)


def clear_cookie(secure: bool = False) -> str:
    parts = [f"{COOKIE}=", "Path=/", "HttpOnly", "Max-Age=0"]
    if secure:
        parts.extend(["SameSite=None", "Secure"])
    else:
        parts.append("SameSite=Lax")
    return "; ".join(parts)


def login(conn, username: str, password: str) -> dict:
    username = (username or "").strip()
    password = (password or "").strip()
    key = username.lower()
    row = conn.execute(
        """SELECT u.*, p.persona_code, p.display_name, p.job_title
           FROM app_user u JOIN persona p ON p.persona_id = u.persona_id
           WHERE lower(u.username) = ?
              OR lower(p.persona_code) = ?
              OR lower(p.display_name) = ?
              OR lower(replace(p.display_name, ' ', '.')) = ?""",
        (key, key, key, key),
    ).fetchone()
    if not row or row["status"] != "ACTIVE" or not verify_password(password, row["password_salt"], row["password_hash"]):
        return {
            "error": "Invalid username or password. Pick a person from the list. Demo password is Demo@2026. Username looks like fatimah.al.harbi"
        }
    token = secrets.token_urlsafe(32)
    created = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO app_session (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, row["user_id"], created, expires),
    )
    conn.execute("UPDATE app_user SET last_login=? WHERE user_id=?", (created, row["user_id"]))
    conn.execute(
        "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
        (created, "LOGIN", row["persona_code"], row["username"]),
    )
    conn.commit()
    return {
        "ok": True,
        "token": token,
        "username": row["username"],
        "display_name": row["display_name"],
        "persona_code": row["persona_code"],
        "job_title": row["job_title"],
    }


def logout(conn, token: str | None):
    if token:
        conn.execute("DELETE FROM app_session WHERE token=?", (token,))
        conn.commit()
    return {"ok": True}


def public_me(user: dict) -> dict:
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "job_title": user["job_title"],
        "persona_code": user["persona_code"],
        "category": user["category"],
        "roles": user["roles"],
        "can_admin_users": user["can_admin_users"],
    }


PROFILE_FIELDS = [
    "mobile",
    "national_id",
    "nationality",
    "gender",
    "date_of_birth",
    "license_no",
    "license_authority",
    "license_expiry",
    "scfhs_no",
    "employment_type",
    "fte",
    "hire_date",
    "emergency_name",
    "emergency_phone",
]


def _can_see(user: dict, persona_id: int) -> bool:
    return user["can_admin_users"] or user["persona_id"] == persona_id


def resolve_persona(conn, user: dict, persona_code: str | None) -> dict | None:
    code = (persona_code or user["persona_code"]).strip()
    row = conn.execute(
        "SELECT persona_id, persona_code, display_name, job_title, category FROM persona WHERE persona_code=?",
        (code,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    if not _can_see(user, d["persona_id"]):
        return None
    return d


def profile_payload(conn, persona: dict) -> dict:
    pid = persona["persona_id"]
    prof = conn.execute("SELECT * FROM staff_profile WHERE persona_id=?", (pid,)).fetchone()
    docs = [
        dict(r)
        for r in conn.execute(
            """SELECT d.document_id, d.doc_code, t.label, t.category, d.original_name, d.size_bytes,
                      d.uploaded_at, d.status, d.mime
               FROM staff_document d JOIN doc_type t ON t.doc_code = d.doc_code
               WHERE d.persona_id=? ORDER BY t.category, t.doc_code, d.document_id""",
            (pid,),
        ).fetchall()
    ]
    types = [dict(r) for r in conn.execute("SELECT * FROM doc_type ORDER BY category, doc_code").fetchall()]
    have = {d["doc_code"] for d in docs}
    missing_mandatory = [t["doc_code"] for t in types if t["category"] == "MANDATORY" and t["doc_code"] not in have]
    p = dict(prof) if prof else {k: None for k in PROFILE_FIELDS}
    required_fields = ["mobile", "national_id", "nationality", "license_no", "license_expiry", "scfhs_no"]
    missing_fields = [f for f in required_fields if not (p.get(f) or "").strip()]
    complete = not missing_fields and not missing_mandatory
    return {
        "persona": persona,
        "profile": {k: p.get(k) for k in PROFILE_FIELDS},
        "doc_types": types,
        "documents": docs,
        "missing_fields": missing_fields,
        "missing_mandatory_docs": missing_mandatory,
        "complete": complete,
    }


def save_profile(conn, user: dict, persona_code: str | None, payload: dict) -> dict:
    persona = resolve_persona(conn, user, persona_code)
    if not persona:
        return {"error": "not found or not allowed"}
    if user["persona_id"] != persona["persona_id"] and not user["can_admin_users"]:
        return {"error": "not allowed"}
    vals = {k: (payload.get(k) or "").strip() or None for k in PROFILE_FIELDS}
    conn.execute(
        f"""INSERT INTO staff_profile (persona_id, {", ".join(PROFILE_FIELDS)}, updated_at)
            VALUES (?, {", ".join("?" for _ in PROFILE_FIELDS)}, ?)
            ON CONFLICT(persona_id) DO UPDATE SET
            {", ".join(f"{k}=excluded.{k}" for k in PROFILE_FIELDS)}, updated_at=excluded.updated_at""",
        (persona["persona_id"], *[vals[k] for k in PROFILE_FIELDS], now_iso()),
    )
    new_pw = (payload.get("new_password") or "").strip()
    if new_pw:
        if len(new_pw) < 8:
            return {"error": "Password must be at least 8 characters"}
        salt, hashed = hash_password(new_pw)
        conn.execute(
            "UPDATE app_user SET password_salt=?, password_hash=?, must_change=0 WHERE persona_id=?",
            (salt, hashed, persona["persona_id"]),
        )
    conn.execute(
        "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
        (now_iso(), "PROFILE_SAVE", user["persona_code"], persona["persona_code"]),
    )
    conn.commit()
    return {"ok": True, **profile_payload(conn, persona)}


def save_document(conn, user: dict, persona_code: str | None, doc_code: str, filename: str, mime: str, data: bytes) -> dict:
    persona = resolve_persona(conn, user, persona_code)
    if not persona:
        return {"error": "not found or not allowed"}
    if user["persona_id"] != persona["persona_id"] and not user["can_admin_users"]:
        return {"error": "not allowed"}
    doc_code = (doc_code or "").strip().upper()
    row = conn.execute("SELECT doc_code FROM doc_type WHERE doc_code=?", (doc_code,)).fetchone()
    if not row:
        return {"error": "Unknown document type"}
    if not data:
        return {"error": "Empty file"}
    if len(data) > MAX_UPLOAD:
        return {"error": "File too large (max 8 MB)"}
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        return {"error": "Allowed types: PDF, JPG, PNG, WEBP, DOC, DOCX"}
    stored = f"{secrets.token_hex(8)}{ext}"
    dest_dir = UPLOADS / str(persona["persona_id"])
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / stored).write_bytes(data)
    conn.execute(
        """INSERT INTO staff_document
           (persona_id, doc_code, original_name, stored_name, mime, size_bytes, uploaded_at, status)
           VALUES (?,?,?,?,?,?,?, 'SUBMITTED')""",
        (persona["persona_id"], doc_code, Path(filename).name[:180], stored, mime, len(data), now_iso()),
    )
    conn.execute(
        "INSERT INTO registry_event (event_time, event_type, actor, detail) VALUES (?,?,?,?)",
        (now_iso(), "DOC_UPLOAD", user["persona_code"], f"{persona['persona_code']} {doc_code}"),
    )
    conn.commit()
    return {"ok": True, **profile_payload(conn, persona)}


def open_document(conn, user: dict, document_id: int):
    row = conn.execute(
        """SELECT d.*, p.persona_code FROM staff_document d
           JOIN persona p ON p.persona_id = d.persona_id WHERE d.document_id=?""",
        (document_id,),
    ).fetchone()
    if not row:
        return None, "not found"
    d = dict(row)
    if not _can_see(user, d["persona_id"]):
        return None, "not allowed"
    path = UPLOADS / str(d["persona_id"]) / d["stored_name"]
    if not path.exists():
        return None, "missing file"
    return d, path


def list_accounts(conn, user: dict) -> list[dict]:
    if not user["can_admin_users"]:
        return []
    rows = conn.execute(
        """SELECT u.user_id, u.username, u.status, u.last_login, u.must_change,
                  p.persona_code, p.display_name, p.job_title, p.category
           FROM app_user u JOIN persona p ON p.persona_id = u.persona_id
           ORDER BY p.category, p.display_name"""
    ).fetchall()
    return [dict(r) for r in rows]


def parse_multipart(content_type: str, body: bytes) -> dict:
    """Return {name: str|dict(filename, mime, data)}."""
    import email
    from email import policy

    msg = email.message_from_bytes(
        f"MIME-Version: 1.0\r\nContent-Type: {content_type}\r\n\r\n".encode("utf-8") + body,
        policy=policy.default,
    )
    out = {}
    if not msg.is_multipart():
        return out
    for part in msg.iter_parts():
        disp = part.get("Content-Disposition") or ""
        name = part.get_param("name", header="Content-Disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            out[name] = {
                "filename": filename,
                "mime": part.get_content_type(),
                "data": payload,
            }
        else:
            out[name] = payload.decode("utf-8", errors="replace")
    return out
