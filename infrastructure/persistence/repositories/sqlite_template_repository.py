"""SQLite-backed template repository implementation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from application.interfaces.i_template_repository import ITemplateRepository
from domain.entities.template import Template
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.db_context import SQLiteDbContext


class SQLiteTemplateRepository(ITemplateRepository):
    """Concrete SQLite adapter for template persistence."""

    def __init__(self, db_context: SQLiteDbContext) -> None:
        self._db = db_context

    def get_by_id(self, entity_id: str) -> Optional[Template]:
        row = self._db.connection.execute("SELECT * FROM templates WHERE id = ?", (int(entity_id),)).fetchone()
        return self._to_entity(row) if row else None

    def get_all(self) -> List[Template]:
        rows = self._db.connection.execute("SELECT * FROM templates ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def add(self, entity: Template) -> None:
        self._db.connection.execute(
            """
            INSERT INTO templates (
                id, name, category, html_content, description, is_published,
                is_default, is_favorite, version_number, tags, usage_count,
                last_used_at, parent_template_id, created_at, created_by,
                modified_at, modified_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row_values(entity),
        )
        self._persist_versions(entity)
        self._persist_placeholders(entity)

    def update(self, entity: Template) -> None:
        self._db.connection.execute(
            """
            UPDATE templates
            SET name = ?, category = ?, html_content = ?, description = ?,
                is_published = ?, is_default = ?, is_favorite = ?, version_number = ?,
                tags = ?, usage_count = ?, last_used_at = ?, parent_template_id = ?,
                created_at = ?, created_by = ?, modified_at = ?, modified_by = ?
            WHERE id = ?
            """,
            (
                entity.name,
                entity.category.value,
                entity.html_content,
                entity.description,
                1 if entity.is_published else 0,
                1 if entity.is_default else 0,
                1 if entity.is_favorite else 0,
                entity.version_number,
                json.dumps(entity.tags),
                entity.usage_count,
                self._dt_to_iso(entity.last_used_at),
                entity.parent_template_id,
                self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
                entity.created_by,
                self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
                entity.modified_by,
                entity.id,
            ),
        )
        self._persist_versions(entity)
        self._persist_placeholders(entity)

    def delete(self, entity_id: str) -> None:
        eid = int(entity_id)
        self._db.connection.execute("DELETE FROM template_versions WHERE template_id = ?", (eid,))
        self._db.connection.execute("DELETE FROM template_placeholders WHERE template_id = ?", (eid,))
        self._db.connection.execute("DELETE FROM templates WHERE id = ?", (eid,))

    def exists(self, entity_id: str) -> bool:
        row = self._db.connection.execute("SELECT 1 FROM templates WHERE id = ? LIMIT 1", (int(entity_id),)).fetchone()
        return row is not None

    def get_by_name(self, name: str) -> Optional[Template]:
        row = self._db.connection.execute("SELECT * FROM templates WHERE name = ? LIMIT 1", (name,)).fetchone()
        return self._to_entity(row) if row else None

    def get_published(self) -> List[Template]:
        rows = self._db.connection.execute("SELECT * FROM templates WHERE is_published = 1 ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_category(self, category: str) -> List[Template]:
        rows = self._db.connection.execute("SELECT * FROM templates WHERE category = ? ORDER BY id", (category,)).fetchall()
        return [self._to_entity(r) for r in rows]

    def search(self, query: str) -> List[Template]:
        term = f"%{query.lower()}%"
        rows = self._db.connection.execute(
            """
            SELECT * FROM templates
            WHERE lower(name) LIKE ?
               OR lower(coalesce(description, '')) LIKE ?
               OR lower(html_content) LIKE ?
            ORDER BY id
            """,
            (term, term, term),
        ).fetchall()
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
        tmpl.last_used_at = self._iso_to_dt(row["last_used_at"])
        tmpl.parent_template_id = row["parent_template_id"]
        tmpl.created_at = self._iso_to_dt(row["created_at"]) or tmpl.created_at
        tmpl.modified_at = self._iso_to_dt(row["modified_at"]) or tmpl.modified_at
        tmpl.modified_by = row["modified_by"]
        # Load version history from DB
        ver_rows = self._db.connection.execute(
            "SELECT * FROM template_versions WHERE template_id = ? ORDER BY version_number",
            (tmpl.id,),
        ).fetchall()
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
        # Load placeholders from DB
        ph_rows = self._db.connection.execute(
            "SELECT * FROM template_placeholders WHERE template_id = ? ORDER BY id",
            (tmpl.id,),
        ).fetchall()
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
        for v in entity.version_history:
            exists = self._db.connection.execute(
                "SELECT 1 FROM template_versions WHERE template_id = ? AND version_number = ? LIMIT 1",
                (entity.id, v.version_number),
            ).fetchone()
            if not exists:
                self._db.connection.execute(
                    """
                    INSERT INTO template_versions
                        (template_id, version_number, html_content, created_at, created_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        v.version_number,
                        v.html_content,
                        self._dt_to_iso(v.created_at) or datetime.utcnow().isoformat(),
                        v.created_by,
                        v.notes,
                    ),
                )

    def _persist_placeholders(self, entity: Template) -> None:
        # Replace all placeholders for this template
        self._db.connection.execute(
            "DELETE FROM template_placeholders WHERE template_id = ?", (entity.id,)
        )
        for ph in entity.placeholders:
            self._db.connection.execute(
                """
                INSERT INTO template_placeholders
                    (template_id, name, description, placeholder_type, is_required,
                     default_value, sample_value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    ph.name,
                    ph.description,
                    ph.placeholder_type.value,
                    1 if ph.is_required else 0,
                    ph.default_value,
                    ph.sample_value,
                ),
            )

    def _to_row_values(self, entity: Template) -> tuple:
        return (
            entity.id,
            entity.name,
            entity.category.value,
            entity.html_content,
            entity.description,
            1 if entity.is_published else 0,
            1 if entity.is_default else 0,
            1 if entity.is_favorite else 0,
            entity.version_number,
            json.dumps(entity.tags),
            entity.usage_count,
            self._dt_to_iso(entity.last_used_at),
            entity.parent_template_id,
            self._dt_to_iso(entity.created_at) or datetime.utcnow().isoformat(),
            entity.created_by,
            self._dt_to_iso(entity.modified_at) or datetime.utcnow().isoformat(),
            entity.modified_by,
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

    @staticmethod
    def _dt_to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @staticmethod
    def _iso_to_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
