"""User authentication and role-based access service."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

from src.database.connection import Database
from src.database.models import User
from src.core.logging import logger

VALID_ROLES = {"hospital_admin", "ophthalmologist", "screening_operator"}


class UserService:
    """Handles user onboarding, authentication, and role authorization."""

    def __init__(self, db: Database):
        self.db = db

    def create_user(
        self,
        tenant_id: str,
        username: str,
        password: str,
        full_name: str,
        role: str,
        email: str,
        phone: Optional[str] = None,
        qualification: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> User:
        """Registers a new healthcare user under a specific hospital workspace."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of {VALID_ROLES}")

        clean_username = username.strip().lower()
        now = datetime.utcnow().isoformat()
        uid = user_id or f"USR-{uuid.uuid4().hex[:8].upper()}"
        pwd_hash = generate_password_hash(password)

        with self.db.session() as conn:
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (clean_username,)).fetchone()
            if existing:
                raise ValueError(f"Username '{clean_username}' already exists.")

            conn.execute(
                """
                INSERT INTO users (
                    id, tenant_id, username, password_hash, full_name,
                    role, email, phone, qualification, created_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    uid, tenant_id, clean_username, pwd_hash, full_name,
                    role, email, phone, qualification, now
                )
            )

        logger.info("Created user %s (%s) for tenant %s", clean_username, role, tenant_id)
        return self.get_user_by_id(uid)

    def authenticate(self, username: str, password: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Authenticates user credentials and checks tenant workspace match if provided."""
        clean_username = username.strip().lower()
        with self.db.session() as conn:
            query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
            params = [clean_username]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)

            row = conn.execute(query, params).fetchone()
            if not row:
                return None

            if not check_password_hash(row["password_hash"], password):
                return None

            return self._row_to_user(row)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a user by ID."""
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_user(row) if row else None

    def list_users_for_tenant(self, tenant_id: str, role: Optional[str] = None) -> List[User]:
        """Lists users belonging to a specific hospital workspace."""
        with self.db.session() as conn:
            query = "SELECT * FROM users WHERE tenant_id = ? AND is_active = 1"
            params = [tenant_id]
            if role:
                query += " AND role = ?"
                params.append(role)
            query += " ORDER BY full_name ASC"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_user(r) for r in rows]

    @staticmethod
    def _row_to_user(row: Any) -> User:
        return User(
            id=row["id"],
            tenant_id=row["tenant_id"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            email=row["email"],
            phone=row["phone"],
            qualification=row["qualification"],
            created_at=row["created_at"],
            is_active=row["is_active"],
        )

