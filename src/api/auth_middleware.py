"""Tenant context and role-based authorization middleware."""

from functools import wraps
import inspect
from typing import Callable, Optional, Sequence, Union
from flask import request, jsonify, current_app, session, g


def get_current_tenant_id() -> Optional[str]:
    """Resolves tenant ID from request headers, session, or parameters."""
    header_tenant = request.headers.get("X-Tenant-ID")
    if header_tenant and header_tenant.strip():
        return header_tenant.strip()

    tenant_id = request.args.get("tenant_id")
    if tenant_id and tenant_id.strip():
        return tenant_id.strip()

    if request.is_json:
        data = request.get_json(silent=True) or {}
        if isinstance(data, dict):
            t_id = data.get("tenant_id")
            if t_id and isinstance(t_id, str) and t_id.strip():
                return t_id.strip()

    session_tenant = session.get("tenant_id")
    if session_tenant:
        return str(session_tenant).strip()

    return None


def require_tenant(roles_or_func: Union[Callable, Sequence[str], None] = None, *, roles: Optional[Sequence[str]] = None):
    """Decorator ensuring request has authenticated session and valid tenant context.

    Can be used as:
        @require_tenant
        def my_view(tenant_id): ...

    Or:
        @require_tenant(roles=["hospital_admin"])
        def admin_view(tenant_id): ...
    """
    allowed_roles = None
    target_func = None

    if callable(roles_or_func):
        target_func = roles_or_func
    elif isinstance(roles_or_func, (list, tuple, set)):
        allowed_roles = set(roles_or_func)
    elif roles_or_func is not None:
        raise TypeError(
            f"Invalid argument to require_tenant: expected callable, list, tuple, or set, got {type(roles_or_func).__name__}"
        )

    if roles is not None:
        if not isinstance(roles, (list, tuple, set)):
            raise TypeError(
                f"Invalid 'roles' argument: expected list, tuple, or set, got {type(roles).__name__}"
            )
        allowed_roles = set(roles)

    def decorator(f: Callable) -> Callable:
        sig = inspect.signature(f)

        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify({"error": "Authentication required. Please log in."}), 401

            user_service = current_app.config["USER_SERVICE"]
            user = user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                return jsonify({"error": "User account not found or inactive."}), 401

            session_tenant_id = user.tenant_id
            tenant_service = current_app.config["TENANT_SERVICE"]
            tenant = tenant_service.get_tenant(session_tenant_id)
            if not tenant or not tenant.is_active:
                return jsonify({"error": f"Hospital workspace '{session_tenant_id}' does not exist or is inactive."}), 404

            # Enforce strict cross-tenant header match if X-Tenant-ID was supplied
            header_tenant = request.headers.get("X-Tenant-ID")
            if header_tenant and header_tenant.strip() != session_tenant_id:
                return jsonify({"error": "Cross-tenant access forbidden."}), 403

            # Enforce route param match if present (e.g. /api/tenants/<tenant_id>)
            route_tenant = kwargs.get("tenant_id")
            if route_tenant and route_tenant != session_tenant_id:
                return jsonify({"error": "Cross-tenant access forbidden."}), 403

            # Check role if required (empty allowed_roles denies all access)
            if allowed_roles is not None and user.role not in allowed_roles:
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403

            g.current_user = user
            g.current_tenant = tenant
            g.tenant_id = session_tenant_id

            if "tenant_id" in sig.parameters:
                kwargs["tenant_id"] = session_tenant_id

            return f(*args, **kwargs)

        return decorated_function

    if target_func is not None:
        return decorator(target_func)
    return decorator
