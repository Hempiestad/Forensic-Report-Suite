from __future__ import annotations

from domain.enums.notification_type import NotificationType
from domain.enums.template_category import TemplateCategory
from infrastructure.persistence.repositories.postgres_notification_repository import (
    PostgreSQLNotificationRepository,
)
from infrastructure.persistence.repositories.postgres_template_repository import (
    PostgreSQLTemplateRepository,
)


def test_postgres_template_repository_parse_category_fallback() -> None:
    assert PostgreSQLTemplateRepository._parse_category("memo") == TemplateCategory.MEMO
    assert PostgreSQLTemplateRepository._parse_category("unknown") == TemplateCategory.BASIC


def test_postgres_template_repository_parse_tags_variants() -> None:
    assert PostgreSQLTemplateRepository._parse_tags(None) == []
    assert PostgreSQLTemplateRepository._parse_tags(["a", "b"]) == ["a", "b"]
    assert PostgreSQLTemplateRepository._parse_tags('["x","y"]') == ["x", "y"]
    assert PostgreSQLTemplateRepository._parse_tags("invalid-json") == []


def test_postgres_notification_repository_parse_type_fallback() -> None:
    assert PostgreSQLNotificationRepository._parse_type("case_created") == NotificationType.CASE_CREATED
    assert PostgreSQLNotificationRepository._parse_type("unknown") == NotificationType.SYSTEM
