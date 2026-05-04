"""PostgreSQL-backed template repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_template_repository import ITemplateRepository
from domain.entities.template import Template
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.db_context import PostgreSQLDbContext


class PostgreSQLTemplateRepository(ITemplateRepository):
    """Concrete PostgreSQL adapter for template persistence."""

    def __init__(self, db_context: PostgreSQLDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Template]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM templates WHERE id = %s", (int(entity_id),))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Template]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM templates ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Template) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO templates (
                    id, name, category, html_content, description, is_published,
                    is_default, is_favorite, version_number, tags, usage_count,
                    last_used_at, parent_template_id, created_at, created_by,
                    modified_at, modified_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entity.id,
                    entity.name,
                    entity.category.value,
                    entity.html_content,
                    entity.description,
                    entity.is_published,
                    entity.is_default,
                    entity.is_favorite,
                    entity.version_number,
                    json.dumps(entity.tags),
                    entity.usage_count,
                    entity.last_used_at,
                    entity.parent_template_id,
                    entity.created_at,
                    entity.created_by,
                    entity.modified_at,
                    entity.modified_by,
                ),
            )
        self._persist_versions(entity)
        self._persist_placeholders(entity)

    def update(self, entity: Template) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                UPDATE templates
                SET name = %s,
                    category = %s,
                    html_content = %s,
                    description = %s,
                    is_published = %s,
                    is_default = %s,
                    is_favorite = %s,
                    version_number = %s,
                    tags = %s,
                    usage_count = %s,
                    last_used_at = %s,
                    parent_template_id = %s,
                    created_at = %s,
                    created_by = %s,
                    modified_at = %s,
                    modified_by = %s
                WHERE id = %s
                """,
                (
                    entity.name,
                    entity.category.value,
                    entity.html_content,
                    entity.description,
                    entity.is_published,
                    entity.is_default,
                    entity.is_favorite,
                    entity.version_number,
                    json.dumps(entity.tags),
                    entity.usage_count,
                    entity.last_used_at,
                    entity.parent_template_id,
                    entity.created_at,
                    entity.created_by,
                    entity.modified_at,
                    entity.modified_by,
                    entity.id,
                ),
            )
        self._persist_versions(entity)
        self._persist_placeholders(entity)

    def delete(self, entity_id: str) -> None:
        with self._db.connection.cursor() as cur:
            cur.execute("DELETE FROM templates WHERE id = %s", (int(entity_id),))

    def exists(self, entity_id: str) -> bool:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT 1 FROM templates WHERE id = %s LIMIT 1", (int(entity_id),))
            row = cur.fetchone()
        return row is not None

    def get_by_name(self, name: str) -> Optional[Template]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM templates WHERE name = %s LIMIT 1", (name,))
            row = cur.fetchone()
        return self._to_entity(row) if row else None

    def get_published(self) -> List[Template]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM templates WHERE is_published = TRUE ORDER BY id")
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_category(self, category: str) -> List[Template]:
        with self._db.connection.cursor() as cur:
            cur.execute("SELECT * FROM templates WHERE category = %s ORDER BY id", (category,))
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str) -> List[Template]:
        term = f"%{query.lower()}%"
        with self._db.connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM templates
                WHERE lower(name) LIKE %s
                   OR lower(coalesce(description, '')) LIKE %s
                   OR lower(html_content) LIKE %s
                ORDER BY id
                """,
                (term, term, term),
            )
            rows = cur.fetchall()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row) -> Template:
        tmpl = Template.create(
            id=int(row["id"]),
            name=row["name"],
            category=self._parse_category(row["category"]),
            html_content=row["html_content"],
            created_by=row["created_by"] or "",
            description=row["description"],
        )
        tmpl.is_published = bool(row["is_published"])
        tmpl.is_default = bool(row["is_default"])
        tmpl.is_favorite = bool(row["is_favorite"])
        tmpl.version_number = int(row["version_number"] or 1)
        tmpl.tags = self._parse_tags(row["tags"])
        tmpl.usage_count = int(row["usage_count"] or 0)
        tmpl.last_used_at = row["last_used_at"]
        tmpl.parent_template_id = row["parent_template_id"]
        tmpl.created_at = row["created_at"] or datetime.utcnow()
        tmpl.modified_at = row["modified_at"] or tmpl.created_at
        tmpl.modified_by = row["modified_by"]
        # Load version history from child table
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM template_versions WHERE template_id = %s ORDER BY version_number",
                (tmpl.id,),
            )
            ver_rows = cur.fetchall()
        for vr in ver_rows:
            from domain.entities.template_version import TemplateVersion
            v = TemplateVersion.create(
                version_number=int(vr["version_number"]),
                html_content=vr["html_content"],
                created_by=vr["created_by"] or "",
                notes=vr["notes"],
            )
            if not any(x.version_number == v.version_number for x in tmpl._versions):
                tmpl._versions.append(v)
        # Load placeholders from child table
        with self._db.connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM template_placeholders WHERE template_id = %s ORDER BY id",
                (tmpl.id,),
            )
            ph_rows = cur.fetchall()
        for pr in ph_rows:
            from domain.entities.template_placeholder import PlaceholderType, TemplatePlaceholder
            ph = TemplatePlaceholder(
                name=pr["name"],
                description=pr["description"],
                placeholder_type=self._parse_ph_type(pr["placeholder_type"]),
                is_required=bool(pr["is_required"]),
                default_value=pr["default_value"],
                sample_value=pr["sample_value"],
            )
            if not any(x.name == ph.name for x in tmpl._placeholders):
                tmpl._placeholders.append(ph)
        return tmpl

    @staticmethod
    def _parse_ph_type(raw: str):
        from domain.entities.template_placeholder import PlaceholderType
        try:
            return PlaceholderType(raw)
        except ValueError:
            return PlaceholderType.STRING

    def _persist_versions(self, entity: Template) -> None:
        """Upsert each version snapshot into template_versions."""
        for v in entity.version_history:
            with self._db.connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM template_versions WHERE template_id = %s AND version_number = %s LIMIT 1",
                    (entity.id, v.version_number),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO template_versions
                            (template_id, version_number, html_content, created_at, created_by, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            entity.id,
                            v.version_number,
                            v.html_content,
                            v.created_at or datetime.utcnow(),
                            v.created_by,
                            v.notes,
                        ),
                    )

    def _persist_placeholders(self, entity: Template) -> None:
        """Replace all placeholder rows for this template."""
        with self._db.connection.cursor() as cur:
            cur.execute(
                "DELETE FROM template_placeholders WHERE template_id = %s", (entity.id,)
            )
            for ph in entity.placeholders:
                cur.execute(
                    """
                    INSERT INTO template_placeholders
                        (template_id, name, description, placeholder_type,
                         is_required, default_value, sample_value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entity.id,
                        ph.name,
                        ph.description,
                        ph.placeholder_type.value,
                        ph.is_required,
                        ph.default_value,
                        ph.sample_value,
                    ),
                )

    @staticmethod
    def _parse_category(raw: str) -> TemplateCategory:
        try:
            return TemplateCategory(raw)
        except ValueError:
            return TemplateCategory.BASIC

    @staticmethod
    def _parse_tags(raw) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(v) for v in raw]
        if isinstance(raw, str):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return [str(v) for v in decoded]
            except Exception:
                return []
        return []
