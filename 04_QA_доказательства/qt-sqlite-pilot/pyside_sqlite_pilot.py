from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

QT_SITE = Path(tempfile.gettempdir()) / "folio-pyside-poc-20261102" / "site-packages"
def find_project_root() -> Path:
    configured = os.environ.get("FOLIO_PROJECT_ROOT")
    if configured:
        candidate = Path(configured).resolve()
        if (candidate / "sqlite_storage.py").is_file():
            return candidate
        if (candidate / "02_Приложение" / "sqlite_storage.py").is_file():
            return candidate / "02_Приложение"
        raise RuntimeError("FOLIO_PROJECT_ROOT does not contain sqlite_storage.py")
    for parent in Path(__file__).resolve().parents:
        if (parent / "sqlite_storage.py").is_file():
            return parent
        if (parent / "02_Приложение" / "sqlite_storage.py").is_file():
            return parent / "02_Приложение"
    raise RuntimeError("Place this pilot under the project or submission QA folder")


PROJECT_ROOT = find_project_root()
sys.path.insert(0, str(QT_SITE))
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QComboBox, QDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)
from sqlite_storage import SQLiteStore

PILOT_DIR = Path(tempfile.gettempdir()) / "folio-qt-sqlite-pilot-20261102"
DB_PATH = PILOT_DIR / "synthetic-portfolio.sqlite3"
RESULT_PATH = PILOT_DIR / "pilot-results.json"
PILOT_DIR.mkdir(parents=True, exist_ok=True)

INITIAL_PAYLOAD = {
    "schema_version": 1,
    "title": "Портфолио — изолированный Qt пилот",
    "next_id": 2,
    "developer": {
        "full_name": "Тестовый разработчик",
        "specialization": "Веб-разработчик",
        "introduction": "Только демонстрационные данные для локальной проверки.",
        "email": "", "website_url": "", "github_url": "",
        "include_email": False, "include_website": False, "include_github": False,
    },
    "projects": [{
        "id": 1, "type": "Веб-приложение", "title": "Демо-портфолио",
        "description": "Изолированная запись, созданная для Qt + SQLite proof of concept.",
        "created_at": "2026-11-02", "status": "Завершён",
        "technologies": [{"name": "Python", "category": "Язык", "version": "3.13"}],
        "demo_url": "", "repository_url": "", "backend_stack": "SQLite",
        "role": "Тест", "outcome": "Проверка формата хранения", "tags": ["демо", "sqlite"],
        "featured": True, "sort_order": 1,
        "context": "Изолированный пилот.", "solution": "Временная база.",
        "process": "Синтетическая запись.", "metrics": "Одна запись.",
    }],
}


class AddProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новый проект")
        self.setAccessibleName("Форма нового проекта")
        self.resize(520, 340)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit()
        self.title.setAccessibleName("Название проекта")
        self.title.setAccessibleDescription("Обязательное поле, максимум 120 символов")
        self.description = QTextEdit()
        self.description.setAccessibleName("Описание проекта")
        self.description.setAccessibleDescription("Кратко опишите работу, до 4000 символов")
        self.status = QComboBox()
        self.status.setAccessibleName("Статус проекта")
        self.status.addItems(["В разработке", "Завершён", "Опубликован", "Архив"])
        title_label = QLabel("Название")
        title_label.setBuddy(self.title)
        description_label = QLabel("Описание")
        description_label.setBuddy(self.description)
        status_label = QLabel("Статус")
        status_label.setBuddy(self.status)
        form.addRow(title_label, self.title)
        form.addRow(description_label, self.description)
        form.addRow(status_label, self.status)
        root.addLayout(form)
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setAccessibleName("Отменить создание проекта")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить проект")
        save.setAccessibleName("Сохранить проект")
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)
        self.title.setFocus()

    def record(self, project_id: int, sort_order: int) -> dict:
        title = self.title.text().strip()
        description = self.description.toPlainText().strip()
        if not title or not description:
            raise ValueError("Название и описание обязательны.")
        if len(title) > 120 or len(description) > 4000:
            raise ValueError("Название или описание превышают допустимую длину.")
        return {
            "id": project_id,
            "type": "Веб-приложение",
            "title": title,
            "description": description,
            "created_at": date.today().isoformat(),
            "status": self.status.currentText(),
            "technologies": [],
            "demo_url": "", "repository_url": "", "backend_stack": "",
            "role": "", "outcome": "", "tags": [], "featured": False,
            "sort_order": sort_order,
            "context": "", "solution": "", "process": "", "metrics": "",
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("folio — Qt + SQLite изолированный пилот")
        self.setAccessibleName("folio — рабочее пространство проектов")
        self.resize(1160, 740)
        SQLiteStore(DB_PATH).save(INITIAL_PAYLOAD)
        self.store = SQLiteStore(DB_PATH)
        self.payload = self.store.load()

        central = QWidget()
        central.setAccessibleName("Рабочая область проектов")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        heading = QLabel("Проекты из SQLite")
        heading.setAccessibleName("Заголовок списка проектов")
        layout.addWidget(heading)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setAccessibleName("Поиск проектов")
        self.search.setAccessibleDescription("Поиск по названию, описанию, статусу и технологиям")
        self.search.setPlaceholderText("Найти проект…")
        search_row.addWidget(self.search, 1)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 4)
        self.table.setAccessibleName("Список проектов из SQLite")
        self.table.setAccessibleDescription("Таблица демонстрационных записей; используйте стрелки для выбора строк")
        self.table.setHorizontalHeaderLabels(["Название", "Тип", "Статус", "Дата"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.empty_state = QLabel("Совпадений не найдено. Очистите поиск или измените запрос.")
        self.empty_state.setAccessibleName("Пустое состояние поиска")
        self.empty_state.setWordWrap(True)
        self.empty_state.hide()
        layout.addWidget(self.empty_state)

        footer = QHBoxLayout()
        self.message = QLabel("База: временная, синтетическая")
        self.message.setAccessibleName("Состояние сохранения")
        footer.addWidget(self.message, 1)
        self.add = QPushButton("Добавить проект")
        self.add.setAccessibleName("Добавить проект")
        footer.addWidget(self.add)
        layout.addLayout(footer)
        self.add.clicked.connect(self.open_add)
        self.search.textChanged.connect(self.refresh_rows)
        self.refresh_rows()

    def refresh_rows(self):
        query = self.search.text().strip().casefold()
        self.payload = self.store.load()
        self.table.setRowCount(0)
        shown = 0
        for project in self.payload["projects"]:
            searchable = " ".join([
                project.get("title", ""), project.get("description", ""),
                project.get("status", ""), project.get("type", ""),
                *project.get("tags", []),
                *(item.get("name", "") for item in project.get("technologies", [])),
            ]).casefold()
            if query and query not in searchable:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [project["title"], project["type"], project["status"], project["created_at"]]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, project["id"])
                self.table.setItem(row, column, item)
            shown += 1
        self.empty_state.setVisible(bool(query) and shown == 0)
        self.message.setText(f"Видно проектов: {shown} · запись выполняется только во временную SQLite")

    def open_add(self):
        dialog = AddProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = self.store.load()
            new_id = max(payload["next_id"], max((p["id"] for p in payload["projects"]), default=0) + 1)
            order = max((p.get("sort_order", p["id"]) for p in payload["projects"]), default=0) + 1
            payload["projects"].append(dialog.record(new_id, order))
            payload["next_id"] = new_id + 1
            self.store.save(payload)
            reread = self.store.load()
            persisted = any(p["id"] == new_id and p["title"] == dialog.title.text().strip() for p in reread["projects"])
            if not persisted:
                raise RuntimeError("Сохранённая запись не найдена при повторном чтении.")
            self.refresh_rows()
            self.message.setText(f"Проект «{dialog.title.text().strip()}» сохранён и перечитан из SQLite")
            RESULT_PATH.write_text(json.dumps({
                "scope": "isolated synthetic database only",
                "database": "Windows Temp / synthetic-portfolio.sqlite3",
                "project_count": len(reread["projects"]),
                "created_id": new_id,
                "created_title": dialog.title.text().strip(),
                "read_back_confirmed": persisted,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            box = QMessageBox(self)
            box.setWindowTitle("Не удалось сохранить")
            box.setAccessibleName("Сообщение об ошибке сохранения")
            box.setText(str(exc))
            box.setAccessibleDescription("Запись не подтверждена повторным чтением SQLite")
            box.exec()


app = QApplication([])
app.setApplicationName("folio Qt SQLite pilot")
window = MainWindow()
window.show()
app.exec()
