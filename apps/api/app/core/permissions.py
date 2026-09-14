"""Central definition of every permission code and which roles hold it.

This is the single source of truth used both to seed the roles/permissions
tables and to document the RBAC matrix. Server-side route dependencies
(app/api/deps.py) always check against the database-backed role/permission
assignment for the authenticated user — never against this dict directly —
so this module only defines the *intended* seed state (section 23).
"""

from app.models.enums import RoleName

PERMISSIONS = {
    "incident:create": "Create a new incident report",
    "incident:read": "View incidents",
    "incident:update": "Edit incident fields",
    "incident:change_status": "Change incident verification/status",
    "incident:delete": "Delete an incident",
    "evidence:upload": "Upload evidence to an incident",
    "evidence:read": "View/download evidence",
    "evidence:delete": "Delete evidence (originals are never overwritten)",
    "investigation:create": "Open an investigation",
    "investigation:assign": "Assign a team/officer to an investigation",
    "field_report:create": "Submit a field report",
    "ai:query": "Use the natural-language AI assistant",
    "ai:analyze_image": "Run AI image analysis on evidence",
    "risk:view": "View risk scores and explanations",
    "report:generate": "Generate intelligence/PRO reports",
    "communications:generate": "Generate PRO communications output",
    "analytics:view": "View analytics dashboards",
    "audit:view": "View audit logs",
    "admin:manage_users": "Create/edit users and role assignments",
    "admin:manage_settings": "Edit system settings",
}

# role -> set of permission codes
ROLE_PERMISSIONS: dict[RoleName, set[str]] = {
    RoleName.SUPER_ADMIN: set(PERMISSIONS.keys()),
    RoleName.NATIONAL_ADMIN: set(PERMISSIONS.keys()) - {"admin:manage_settings"},
    RoleName.OPERATIONS_MANAGER: {
        "incident:read", "incident:update", "incident:change_status",
        "evidence:read", "investigation:create", "investigation:assign",
        "field_report:create", "ai:query", "risk:view", "report:generate",
        "analytics:view",
    },
    RoleName.FIELD_SUPERVISOR: {
        "incident:read", "incident:update", "incident:change_status",
        "evidence:read", "investigation:assign", "field_report:create",
        "risk:view", "analytics:view",
    },
    RoleName.FIELD_OFFICER: {
        "incident:create", "incident:read", "evidence:upload", "evidence:read",
        "field_report:create", "risk:view",
    },
    RoleName.INTELLIGENCE_ANALYST: {
        "incident:read", "incident:update", "evidence:read", "ai:query",
        "ai:analyze_image", "risk:view", "report:generate", "analytics:view",
    },
    RoleName.ENVIRONMENTAL_ANALYST: {
        "incident:read", "evidence:read", "ai:query", "ai:analyze_image",
        "risk:view", "analytics:view",
    },
    RoleName.PRO: {
        "incident:read", "risk:view", "report:generate", "communications:generate",
        "analytics:view",
    },
    RoleName.REPORT_VIEWER: {
        "incident:read", "risk:view", "analytics:view",
    },
    RoleName.AUDITOR: {
        "audit:view", "incident:read", "analytics:view",
    },
}
