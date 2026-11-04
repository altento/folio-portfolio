from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новый проект")
        self.setAccessibleName("Форма нового проекта")
        self.resize(460, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit()
        self.title.setAccessibleName("Название проекта")
        self.title.setAccessibleDescription("Введите название новой работы")
        self.description = QTextEdit()
        self.description.setAccessibleName("Описание проекта")
        self.description.setAccessibleDescription("Кратко опишите задачу и результат")
        title_label = QLabel("Название")
        title_label.setBuddy(self.title)
        description_label = QLabel("Описание")
        description_label.setBuddy(self.description)
        form.addRow(title_label, self.title)
        form.addRow(description_label, self.description)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setAccessibleName("Отменить создание проекта")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setAccessibleName("Сохранить проект")
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)
        self.title.setFocus()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("folio — Qt accessibility proof")
        self.setAccessibleName("folio — рабочее пространство проектов")
        self.resize(1120, 700)

        central = QWidget()
        central.setAccessibleName("Рабочая область")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        heading = QLabel("Ваши проекты")
        heading.setObjectName("pageHeading")
        layout.addWidget(heading)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setAccessibleName("Поиск проектов")
        self.search.setAccessibleDescription("Ищите по названию, описанию и технологиям")
        self.search.setPlaceholderText("Поиск проектов")
        self.find = QPushButton("Найти")
        self.find.setAccessibleName("Найти проекты")
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.find)
        layout.addLayout(search_row)

        self.table = QTableWidget(2, 2)
        self.table.setAccessibleName("Список проектов")
        self.table.setHorizontalHeaderLabels(["Название", "Статус"])
        self.table.setItem(0, 0, QTableWidgetItem("Портфолио веб-разработчика"))
        self.table.setItem(0, 1, QTableWidgetItem("Опубликован"))
        self.table.setItem(1, 0, QTableWidgetItem("CRM для клининговой компании"))
        self.table.setItem(1, 1, QTableWidgetItem("В разработке"))
        layout.addWidget(self.table, 1)

        self.add = QPushButton("Добавить проект")
        self.add.setAccessibleName("Добавить проект")
        self.add.clicked.connect(self.open_add)
        layout.addWidget(self.add, alignment=Qt.AlignmentFlag.AlignLeft)

    def open_add(self):
        dialog = NewProjectDialog(self)
        dialog.exec()


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
