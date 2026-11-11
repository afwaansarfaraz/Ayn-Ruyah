"""Tenant (Hospital / Clinic) management service."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3

from src.database.connection import Database
from src.database.models import Tenant
from src.core.exceptions import ConfigurationError
from src.core.logging import logger


class TenantService:
    """Manages hospital onboarding, configuration, and tenant workspace retrieval."""

    def __init__(self, db: Database):
        self.db = db

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        city: str,
        state: str,
        address: str,
        contact_email: str,
        contact_phone: str,
        registration_number: Optional[str] = None,
        logo_url: Optional[str] = None,
        tier: str = "Standard",
    ) -> Tenant:
        """Registers a new hospital screening facility."""
        clean_id = tenant_id.strip().lower().replace(" ", "-")
        now = datetime.utcnow().isoformat()

        with self.db.session() as conn:
            # Check existing
            existing = conn.execute("SELECT id FROM tenants WHERE id = ?", (clean_id,)).fetchone()
            if existing:
                raise ValueError(f"Hospital with workspace ID '{clean_id}' already exists.")

            conn.execute(
                """
                INSERT INTO tenants (
                    id, name, registration_number, logo_url, city, state,
                    address, contact_email, contact_phone, tier, created_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    clean_id, name, registration_number, logo_url, city, state,
                    address, contact_email, contact_phone, tier, now
                )
            )

        logger.info("Successfully registered hospital workspace: %s (%s)", name, clean_id)
        return self.get_tenant(clean_id)

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieves tenant details by workspace ID."""
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE id = ? AND is_active = 1", (tenant_id,)).fetchone()
            if not row:
                return None
            return Tenant(
                id=row["id"],
                name=row["name"],
                registration_number=row["registration_number"],
                logo_url=row["logo_url"],
                city=row["city"],
                state=row["state"],
                address=row["address"],
                contact_email=row["contact_email"],
                contact_phone=row["contact_phone"],
                tier=row["tier"],
                created_at=row["created_at"],
                is_active=row["is_active"],
            )

    def list_tenants(self) -> List[Tenant]:
        """Lists all active hospital workspaces."""
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM tenants WHERE is_active = 1 ORDER BY name ASC").fetchall()
            return [
                Tenant(
                    id=r["id"],
                    name=r["name"],
                    registration_number=r["registration_number"],
                    logo_url=r["logo_url"],
                    city=r["city"],
                    state=r["state"],
                    address=r["address"],
                    contact_email=r["contact_email"],
                    contact_phone=r["contact_phone"],
                    tier=r["tier"],
                    created_at=r["created_at"],
                    is_active=r["is_active"],
                )
                for r in rows
            ]

    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> Tenant:
        """Updates hospital profile and branding settings."""
        allowed_fields = [
            "name", "registration_number", "logo_url", "city", "state",
            "address", "contact_email", "contact_phone"
        ]
        set_clauses = []
        values = []

        for field, val in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(val)

        if not set_clauses:
            return self.get_tenant(tenant_id)

        values.append(tenant_id)
        with self.db.session() as conn:
            conn.execute(
                f"UPDATE tenants SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )

        logger.info("Updated profile settings for tenant: %s", tenant_id)
        return self.get_tenant(tenant_id)

