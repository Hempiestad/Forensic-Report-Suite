from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from application.interfaces.i_template_repository import ITemplateRepository
from application.services.template_service import TemplateService
from domain.entities.template import Template
from domain.enums.template_category import TemplateCategory


class InMemoryTemplateRepository(ITemplateRepository):
    def __init__(self, items: Optional[List[Template]] = None) -> None:
        self._items: Dict[str, Template] = {}
        for item in items or []:
            self._items[str(item.id)] = item

    def get_by_id(self, entity_id: str) -> Optional[Template]:
        return self._items.get(entity_id)

    def get_all(self) -> List[Template]:
        return list(self._items.values())

    def add(self, entity: Template) -> None:
        self._items[str(entity.id)] = entity

    def update(self, entity: Template) -> None:
        self._items[str(entity.id)] = entity

    def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._items

    def get_by_name(self, name: str) -> Optional[Template]:
        for item in self._items.values():
            if item.name == name:
                return item
        return None

    def get_published(self) -> List[Template]:
        return [i for i in self._items.values() if i.is_published]

    def get_by_category(self, category: str) -> List[Template]:
        return [i for i in self._items.values() if str(i.category) == category]

    def search(self, query: str) -> List[Template]:
        q = query.lower()
        return [i for i in self._items.values() if q in i.name.lower() or q in (i.description or "").lower()]


class StubAuditService:
    def log_event(self, *, event_type, description, actor, entity_id=None, metadata=None):
        pass


@pytest.fixture
def template_service() -> TemplateService:
    t1 = Template.create(
        id=1,
        name="SWGDE Base",
        category=TemplateCategory.SWGDE_NIST,
        html_content="<p>{case_number}</p>",
        created_by="admin",
        description="Primary template",
    )
    t1.publish("admin")

    t2 = Template.create(
        id=2,
        name="Memo",
        category=TemplateCategory.MEMO,
        html_content="<p>memo</p>",
        created_by="admin",
        description="Simple memo",
    )

    repo = InMemoryTemplateRepository([t1, t2])
    return TemplateService(repo, StubAuditService())  # type: ignore[arg-type]


def test_template_service_pass_through_reads(template_service: TemplateService) -> None:
    by_id = template_service.get_template_by_id(1)
    assert by_id is not None
    assert by_id.name == "SWGDE Base"

    by_name = template_service.get_template_by_name("Memo")
    assert by_name is not None
    assert by_name.template_id == 2

    assert len(template_service.get_all_templates()) == 2
    assert len(template_service.get_published_templates()) == 1
    assert len(template_service.get_templates_by_category("memo")) == 1
    assert len(template_service.search_templates("primary")) == 1


@pytest.mark.parametrize(
    "invocation",
    [
        lambda s: s.validate_template_html("<p>x</p>"),
        lambda s: s.get_templates_by_tag("x"),
        lambda s: s.get_recent_templates(),
        lambda s: s.get_most_used_templates(),
        lambda s: s.get_favorite_templates("admin"),
        lambda s: s.get_version_history(1),
        lambda s: s.get_template_version(1, 1),
        lambda s: s.record_usage(1),
        lambda s: s.get_statistics(1),
        lambda s: s.get_all_statistics(),
        lambda s: s.export_to_html(1),
        lambda s: s.export_to_json(1),
        lambda s: s.render_template_by_name("Memo", {}),
        lambda s: s.generate_preview(1),
        lambda s: s.validate_placeholder_values(1, {}),
        lambda s: s.get_placeholders(1),
        lambda s: s.auto_detect_placeholders(1),
        lambda s: s.add_to_favorites(1, "admin"),
        lambda s: s.remove_from_favorites(1, "admin"),
        lambda s: s.clone_template(1, "Copy", "admin"),
    ],
)
def test_template_service_methods_callable_without_error(
    invocation, template_service: TemplateService
) -> None:
    """All implemented methods should not raise NotImplementedError."""
    try:
        invocation(template_service)
    except NotImplementedError:
        pytest.fail("Method raised NotImplementedError — Phase 5 implementation missing.")
