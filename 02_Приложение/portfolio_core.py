"""Framework-independent portfolio models and operations.

Kept free of Tk/Qt imports so desktop interfaces can share the same domain
behavior and storage payload.
"""
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

@dataclass
class Technology:
    name: str
    category: str = "Инструмент"
    version: str = ""

    def get_info(self) -> str:
        return f"{self.name} {self.version}".strip()


@dataclass
class Project(ABC):
    title: str
    description: str
    created_at: str = field(default_factory=lambda: date.today().isoformat())
    status: str = "Завершён"
    technologies: list[Technology] = field(default_factory=list)
    demo_url: str = ""
    project_id: int = 0
    role: str = ""
    outcome: str = ""
    tags: list[str] = field(default_factory=list)
    featured: bool = False
    cover_image: str = ""
    cover_image_data: str = ""
    cover_position: str = field(default="50% 46%", kw_only=True)
    gallery_images: list[dict[str, str]] = field(default_factory=list)
    sort_order: int = field(default=0, kw_only=True)
    context: str = field(default="", kw_only=True)
    solution: str = field(default="", kw_only=True)
    process: str = field(default="", kw_only=True)
    metrics: str = field(default="", kw_only=True)

    @property
    def project_type(self) -> str:
        return "Проект"

    @abstractmethod
    def get_main_link(self) -> str:
        """Вернуть главную ссылку; конкретную реализацию задаёт подкласс."""
        raise NotImplementedError

    def get_info(self) -> str:
        stack = ", ".join(t.get_info() for t in self.technologies) or "не указан"
        return f"{self.title} · {self.project_type} · {self.status}\nСтек: {stack}\n{self.description}"


@dataclass
class LandingProject(Project):
    page_count: int = 1

    @property
    def project_type(self) -> str:
        return "Сайт / лендинг"

    def get_main_link(self) -> str:
        return self.demo_url


@dataclass
class WebAppProject(Project):
    repository_url: str = ""
    backend_stack: str = ""

    @property
    def project_type(self) -> str:
        return "Веб-приложение"

    def get_main_link(self) -> str:
        return self.demo_url or self.repository_url


@dataclass
class Portfolio:
    title: str = "Портфолио веб-разработчика"
    projects: list[Project] = field(default_factory=list)
    next_id: int = 1

    def add(self, project: Project) -> None:
        project.project_id = self.next_id
        if project.sort_order < 1:
            project.sort_order = max((p.sort_order or p.project_id for p in self.projects), default=0) + 1
        self.next_id += 1
        self.projects.append(project)

    def delete(self, project_id: int) -> None:
        self.projects = [p for p in self.projects if p.project_id != project_id]

    def duplicate(self, project_id: int) -> Project | None:
        """Create an independent working copy without reusing external links."""
        source = next((p for p in self.projects if p.project_id == project_id), None)
        if source is None:
            return None
        duplicate = copy.deepcopy(source)
        duplicate.project_id = 0
        duplicate.title = f"{source.title[:82].rstrip()} — копия"
        duplicate.created_at = date.today().isoformat()
        duplicate.demo_url = ""
        if isinstance(duplicate, WebAppProject):
            duplicate.repository_url = ""
        duplicate.featured = False
        duplicate.sort_order = max((p.sort_order or p.project_id for p in self.projects if not p.featured), default=0) + 1
        self.add(duplicate)
        return duplicate

    def move(self, project_id: int, direction: int) -> bool:
        if direction not in (-1, 1):
            raise ValueError("Направление перемещения должно быть -1 или 1.")
        project = next((p for p in self.projects if p.project_id == project_id), None)
        if project is None:
            return False
        peers = sorted((p for p in self.projects if p.featured == project.featured),
                       key=lambda p: (p.sort_order or p.project_id, p.project_id))
        target_index = peers.index(project) + direction
        if not 0 <= target_index < len(peers):
            return False
        other = peers[target_index]
        current_order, other_order = project.sort_order or project.project_id, other.sort_order or other.project_id
        project.sort_order, other.sort_order = other_order, current_order
        return True

    def search(self, query: str) -> list[Project]:
        q = query.strip().casefold()
        if not q:
            return list(self.projects)
        return [p for p in self.projects if q in " ".join(
            [p.title, p.description, p.status, p.project_type, p.created_at,
             p.role, p.outcome, p.demo_url, str(getattr(p, "page_count", "")),
             getattr(p, "repository_url", ""), getattr(p, "backend_stack", ""),
             p.context, p.solution, p.process, p.metrics,
             *p.tags, *(t.get_info() for t in p.technologies)]).casefold()]


def merge_portfolio_import(current: Portfolio, incoming: Portfolio, strategy: str = "keep-current") -> tuple[Portfolio, dict[str, int]]:
    """Merge validated JSON records without mutating either input portfolio."""
    if strategy not in {"keep-current", "copy"}:
        raise ValueError("Для слияния используйте стратегию keep-current или copy.")
    merged = copy.deepcopy(current)
    local_ids = {project.project_id for project in merged.projects}
    stats = {"added": 0, "copied": 0, "skipped": 0}
    next_id = max(merged.next_id, max(local_ids, default=0) + 1)
    for source in incoming.projects:
        conflict = source.project_id in local_ids
        if conflict and strategy == "keep-current":
            stats["skipped"] += 1
            continue
        project = copy.deepcopy(source)
        if conflict:
            project.project_id = next_id
            next_id += 1
            project.title = f"{project.title[:81].rstrip()} — импорт"
            stats["copied"] += 1
        else:
            stats["added"] += 1
        peers = [item for item in merged.projects if item.featured == project.featured]
        project.sort_order = max((item.sort_order or item.project_id for item in peers), default=0) + 1
        merged.projects.append(project)
        local_ids.add(project.project_id)
    merged.next_id = max(next_id, max((project.project_id for project in merged.projects), default=0) + 1)
    return merged, stats


@dataclass
class Developer:
    full_name: str = "Даниил Головин"
    specialization: str = "Веб-разработчик"
    introduction: str = ""
    email: str = ""
    website_url: str = ""
    github_url: str = ""
    include_email: bool = False
    include_website: bool = False
    include_github: bool = False

    def create_portfolio(self) -> Portfolio:
        return Portfolio()

def project_type_change_loss_fields(source_type: str, target_type: str, page_count: str,
                                   repository_url: str, backend_stack: str,
                                   has_saved_source: bool = False) -> list[str]:
    """List type-specific values that would be discarded by a form conversion."""
    if source_type == target_type:
        return []
    if target_type == "Сайт / лендинг":
        losses = []
        if repository_url.strip():
            losses.append("Ссылка на репозиторий")
        if backend_stack.strip():
            losses.append("Серверная часть")
        return losses
    if source_type == "Сайт / лендинг":
        value = page_count.strip()
        if has_saved_source or value not in {"", "1"}:
            label = f"Количество страниц ({value})" if value else "Количество страниц"
            return [label]
    return []


def render_portfolio_markdown(portfolio: Portfolio, developer: Developer) -> str:
    projects = sorted(portfolio.projects, key=lambda p: not p.featured)
    lines = [f"# {portfolio.title}", "", f"**{developer.full_name}** · {developer.specialization}", ""]
    if developer.introduction:
        lines.extend([developer.introduction, ""])
    contacts = []
    if developer.include_email and developer.email:
        contacts.append(f"[Email](mailto:{developer.email})")
    if developer.include_website and developer.website_url:
        contacts.append(f"[Сайт]({developer.website_url})")
    if developer.include_github and developer.github_url:
        contacts.append(f"[GitHub]({developer.github_url})")
    if contacts:
        lines.extend(["**Контакты:** " + " · ".join(contacts), ""])
    if not projects:
        lines.append("Пока нет добавленных проектов.")
    for project in projects:
        lines.extend([f"## {'★ ' if project.featured else ''}{project.title}", "",
            f"*{project.project_type} · {project.status} · {project.created_at}*", "",
            project.description, ""])
        if project.role:
            lines.extend([f"**Моя роль:** {project.role}", ""])
        if project.outcome:
            lines.extend([f"**Результат:** {project.outcome}", ""])
        for heading, content in (("Контекст задачи", project.context), ("Решение", project.solution),
                                 ("Этапы работы", project.process), ("Метрики", project.metrics)):
            if content:
                lines.extend([f"**{heading}:**", "", content, ""])
        if project.tags:
            lines.extend([f"**Теги:** {', '.join(project.tags)}", ""])
        stack = ", ".join(technology.get_info() for technology in project.technologies)
        if stack:
            lines.extend([f"**Технологии:** {stack}", ""])
        links = []
        if project.demo_url:
            links.append(f"[Демо]({project.demo_url})")
        if isinstance(project, WebAppProject) and project.repository_url:
            links.append(f"[Репозиторий]({project.repository_url})")
        if links:
            lines.extend([" · ".join(links), ""])
    return "\n".join(lines).rstrip() + "\n"

__all__ = [
    "Technology", "Project", "LandingProject", "WebAppProject", "Portfolio",
    "merge_portfolio_import", "Developer", "project_type_change_loss_fields",
    "render_portfolio_markdown",
]
