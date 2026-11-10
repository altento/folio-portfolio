from __future__ import annotations

import importlib.util
import json
import sys
import struct
import tempfile
import unittest
import zlib
from datetime import date
from pathlib import Path
from unittest.mock import patch

APP_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("portfolio_app_under_test", APP_PATH)
APP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


class DetailsStub:
    def __init__(self):
        self.value = ""
    def set(self, value):
        self.value = value


class PortfolioModelTests(unittest.TestCase):
    def test_tk_accessibility_is_enabled_when_runtime_supports_it(self):
        class TkStub:
            def __init__(self):
                self.calls = []

            def call(self, *args):
                self.calls.append(args)

        root = type("RootStub", (), {"tk": TkStub(), "_w": "."})()
        self.assertTrue(APP.enable_tk_accessibility(root))
        self.assertEqual(root.tk.calls, [("tk", "accessible", "add_acc_object", ".")])

    def test_tk_accessibility_falls_back_cleanly_on_tk_86(self):
        class TkStub:
            def call(self, *args):
                raise APP.tk.TclError("unknown subcommand")

        root = type("RootStub", (), {"tk": TkStub(), "_w": "."})()
        self.assertFalse(APP.enable_tk_accessibility(root))

    def test_frozen_desktop_app_keeps_database_in_local_app_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(APP.os.environ, {"LOCALAPPDATA": temp_dir}), \
                    patch.object(APP.sys, "frozen", True, create=True):
                path = APP.default_data_path()
                self.assertTrue(path.parent.is_dir())

        self.assertEqual(path.name, "portfolio_data.sqlite3")
        self.assertEqual(path.parent.name, "Folio")

    def test_source_desktop_app_keeps_database_next_to_main_module(self):
        with patch.object(APP.sys, "frozen", False, create=True):
            self.assertEqual(APP.default_data_path(), APP_PATH.with_name("portfolio_data.sqlite3"))

    def test_shared_portable_transfer_fixture_is_accepted_by_desktop(self):
        fixture = Path(__file__).parent / "fixtures" / "portable-transfer.json"
        target = object.__new__(APP.PortfolioApp)
        target.refresh = lambda: None
        target._set_details = lambda message: None
        portfolio, developer = target._read_data(fixture, set_active_store=False, apply=False)
        project = portfolio.projects[0]
        self.assertEqual((portfolio.title, portfolio.next_id), ("Портфолио для переноса", 8))
        self.assertEqual((developer.full_name, project.title, project.project_id),
                         ("Тестовый автор", "Кейс для проверки переноса", 7))
        self.assertEqual((project.technologies[0].category, project.technologies[0].version),
                         ("Frontend", "5"))
        self.assertEqual((project.context, project.role, project.outcome, project.tags, project.featured),
                         ("Проверить содержимое кейса при переносе между устройствами.",
                          "Дизайн и разработка", "Адаптивная витрина проекта", ["перенос", "проверка"], True))
        self.assertEqual((project.page_count, len(project.gallery_images)), (4, 1))
        self.assertEqual(project.cover_position, "35% 65%")
        self.assertEqual(project.cover_position_mobile, "12% 80%")

    def test_desktop_project_media_items_include_cover_then_described_gallery(self):
        project = APP.LandingProject(
            "Кейс", "Описание", cover_image="./assets/covers/case.png",
            cover_image_data="data:image/png;base64,AA==",
            gallery_images=[
                {"image_data": "data:image/png;base64,AQ==", "alt": "Первый экран", "position": "20% 30%"},
                {"image_data": "data:image/webp;base64,Ag==", "alt": "Мобильная версия", "position": "70% 80%"},
            ],
        )

        self.assertEqual(APP.desktop_project_media_items(project), [
            ("data:image/png;base64,AA==", "./assets/covers/case.png", "Обложка проекта", "50% 46%"),
            ("data:image/png;base64,AQ==", "", "Первый экран", "20% 30%"),
            ("data:image/webp;base64,Ag==", "", "Мобильная версия", "70% 80%"),
        ])

    def test_desktop_project_media_items_allow_empty_visuals(self):
        project = APP.WebAppProject("Кейс", "Описание")

        self.assertEqual(APP.desktop_project_media_items(project), [])

    def test_desktop_dashboard_hero_art_is_a_local_webp(self):
        content = APP.DESKTOP_HERO_ART_PATH.read_bytes()
        self.assertEqual(content[:4], b"RIFF")
        self.assertEqual(content[8:12], b"WEBP")

    def test_desktop_project_table_rows_alternate_subtle_surface(self):
        self.assertEqual(APP.desktop_table_row_tags(0), ())
        self.assertEqual(APP.desktop_table_row_tags(1), ("row-alt",))
        self.assertEqual(APP.desktop_table_row_tags(2), ())
        self.assertEqual(APP.desktop_table_row_tags(3), ("row-alt",))

    def test_desktop_layout_density_preserves_table_space_on_short_windows(self):
        self.assertEqual(APP.desktop_density_for_height(680), "tight")
        self.assertEqual(APP.desktop_density_for_height(860), "compact")
        self.assertEqual(APP.desktop_density_for_height(1080), "comfortable")
        self.assertLess(APP.desktop_detail_art_size("tight")[0],
                        APP.desktop_detail_art_size("compact")[0])
        self.assertLess(APP.desktop_detail_art_size("compact")[0],
                        APP.desktop_detail_art_size("comfortable")[0])

    def test_desktop_project_gallery_switches_to_single_column_and_scales_art(self):
        self.assertEqual(APP.desktop_project_card_layout(1360), (2, (624, 268)))
        self.assertEqual(APP.desktop_project_card_layout(1120), (2, (480, 206)))
        self.assertEqual(APP.desktop_project_card_layout(1119), (1, (780, 335)))
        self.assertEqual(APP.desktop_project_card_layout(1000), (1, (780, 335)))
        self.assertEqual(APP.desktop_project_card_layout(800), (1, (720, 310)))

    def test_desktop_fixed_action_toolbar_is_reserved_before_expandable_project_views(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index('bottom.pack(fill="x", side="bottom")'),
                        source.index('views.pack(fill="both", expand=True)'))
        self.assertLess(source.index('self.tree = ttk.Treeview(table'),
                        source.index('for label, callback, button_style in'))

    def test_desktop_empty_state_art_is_a_local_transparent_png(self):
        asset = APP_PATH.parent / "assets" / "portfolio-empty-illustration.png"
        content = asset.read_bytes()
        self.assertEqual(content[:8], b"\x89PNG\r\n\x1a\n")
        width, height, bit_depth, color_type = struct.unpack(">IIBB", content[16:26])
        self.assertLessEqual(max(width, height), 640)
        self.assertEqual(color_type, 6)  # RGBA keeps a transparent background.

    def test_desktop_window_uses_available_screen_size_and_preserves_large_layout(self):
        self.assertEqual(APP.desktop_window_dimensions(1920, 1080), ((1360, 860), (1000, 680)))
        self.assertEqual(APP.desktop_window_dimensions(1366, 768), ((1318, 672), (1000, 672)))
        size, minimum = APP.desktop_window_dimensions(800, 600)
        self.assertEqual(size, (752, 504))
        self.assertEqual(minimum, (752, 504))
        self.assertLessEqual(size[0], 800)
        self.assertLessEqual(size[1], 600)

    def test_detail_window_is_centered_and_stays_on_screen(self):
        self.assertEqual(APP.center_window_position(1920, 1080, 1040, 700), (440, 190))
        self.assertEqual(APP.center_window_position(1360, 900, 1040, 700), (160, 100))
        self.assertEqual(APP.center_window_position(800, 600, 752, 504), (24, 48))
        self.assertEqual(APP.center_window_position(320, 240, 400, 300), (0, 0))

    def test_desktop_dialog_geometry_fits_available_screen(self):
        self.assertEqual(APP.fit_window_dimensions(1920, 1080, (1180, 780), (720, 480)),
                         ((1180, 780), (720, 480)))
        self.assertEqual(APP.fit_window_dimensions(1366, 768, (1180, 780), (720, 480)),
                         ((1180, 672), (720, 480)))
        size, minimum = APP.fit_window_dimensions(800, 600, (1180, 780), (720, 480))
        self.assertEqual((size, minimum), ((752, 504), (720, 480)))
        self.assertEqual(APP.fit_window_dimensions(800, 600, (560, 650), (480, 440)),
                         ((560, 504), (480, 440)))
        self.assertEqual(APP.fit_window_dimensions(800, 600, (720, 540), (560, 430)),
                         ((720, 504), (560, 430)))
        self.assertEqual(APP.fit_window_dimensions(1920, 1080, (860, 560), (680, 460)),
                         ((860, 560), (680, 460)))
        self.assertEqual(APP.fit_window_dimensions(800, 600, (860, 560), (680, 460)),
                         ((752, 504), (680, 460)))

    def test_desktop_keyboard_focus_scroll_uses_grid_cell_height_as_extent(self):
        fraction = APP.canvas_focus_view_fraction(0, 801, 1107, 914, 30)
        self.assertAlmostEqual(fraction, (914 + 30 + 12 - 801) / 1107)
        self.assertAlmostEqual(APP.canvas_focus_view_fraction(300, 801, 1107, 250, 30),
                               (250 - 12) / 1107)
        self.assertIsNone(APP.canvas_focus_view_fraction(0, 801, 1107, 500, 30))
        self.assertAlmostEqual(APP.canvas_focus_view_fraction(0, 801, 1107, 760, 30),
                               (760 + 30 + 12 - 801) / 1107)
        self.assertAlmostEqual(APP.canvas_focus_view_fraction(0, 40, 1107, 0, 20, margin=12),
                               0)

    def test_desktop_multiline_editor_scrolls_inside_then_bubbles_at_edges(self):
        self.assertEqual(APP.desktop_text_wheel_target(120, (0.2, 0.7)), "text")
        self.assertEqual(APP.desktop_text_wheel_target(-120, (0.2, 0.7)), "text")
        self.assertEqual(APP.desktop_text_wheel_target(120, (0.0, 0.7)), "form")
        self.assertEqual(APP.desktop_text_wheel_target(-120, (0.2, 1.0)), "form")
        self.assertIsNone(APP.desktop_text_wheel_target(0, (0.0, 1.0)))

    def test_desktop_multiline_editor_wheel_binding_uses_inner_scroll_handler(self):
        source = APP_PATH.read_text(encoding="utf-8")
        form_events = source[source.index("        def bind_form_events(widget):"):]
        form_events = form_events[:form_events.index("        bind_form_events(frame)")]
        self.assertIn("isinstance(widget, tk.Text)", form_events)
        self.assertIn("scroll_multiline(event, target)", form_events)

    def test_desktop_keyboard_focus_skips_hidden_dynamic_controls(self):
        source = APP_PATH.read_text(encoding="utf-8")
        focus_handler = source[source.index("        def move_form_focus("):]
        focus_handler = focus_handler[:focus_handler.index("        focusable_controls =")]
        self.assertIn("widget.winfo_ismapped()", focus_handler)
        self.assertNotIn("widget.winfo_manager()", focus_handler)

    def test_nested_desktop_focus_control_resolves_its_scrollable_grid_anchor(self):
        class WidgetStub:
            def __init__(self, master=None, placement=None):
                self.master = master
                self.placement = placement or {}

            def grid_info(self):
                return self.placement

        frame = WidgetStub()
        cover_panel = WidgetStub(frame, {"row": "16", "column": "0", "rowspan": "1"})
        choose_cover = WidgetStub(cover_panel)
        other = WidgetStub()

        anchor, placement = APP.grid_anchor_in(frame, choose_cover)
        self.assertIs(anchor, cover_panel)
        self.assertEqual(placement["row"], "16")
        self.assertIsNone(APP.grid_anchor_in(frame, other))

    def test_author_profile_defaults_legacy_fields_and_validates_contact_consent(self):
        legacy = APP.normalize_developer_data({"full_name": "Имя", "specialization": "Frontend"})
        self.assertEqual(legacy["introduction"], "")
        self.assertFalse(legacy["include_email"])
        profile = APP.normalize_developer_data({**legacy, "email": "hello@example.net", "include_email": True})
        self.assertTrue(profile["include_email"])
        for invalid in ({**legacy, "email": "not-an-email"}, {**legacy, "website_url": "javascript:alert(1)"},
                        {**legacy, "include_github": "yes"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                APP.normalize_developer_data(invalid)

    def test_project_gallery_requires_descriptions_and_bounded_crop_positions(self):
        data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        gallery = APP.normalize_gallery_images([{"image_data": data, "alt": "Экран профиля", "position": "28% 72%"}])
        self.assertEqual(gallery[0]["position"], "28% 72%")
        expanded = APP.normalize_gallery_images([{"image_data": data, "alt": f"Экран {i}", "position": "50% 50%"} for i in range(10)])
        self.assertEqual(len(expanded), 10)
        oversized = "data:image/png;base64," + "A" * 1_333_312
        for invalid in ([{"image_data": data, "alt": "", "position": "50% 50%"}],
                        [{"image_data": data, "alt": "Описание", "position": "101% 50%"}],
                        [{"image_data": "data:image/svg+xml;base64,PHN2Zy8+", "alt": "Описание"}],
                        [{"image_data": data, "alt": "Описание"}] * 11,
                        [{"image_data": oversized, "alt": f"Деталь {i}", "position": "50% 50%"} for i in range(6)]):
            with self.subTest(invalid_gallery_count=len(invalid)), self.assertRaises(ValueError):
                APP.normalize_gallery_images(invalid)

    def test_embedded_cover_image_is_decoded_not_only_mime_checked(self):
        valid = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        self.assertTrue(APP.is_valid_cover_image(valid, data_url=True))
        self.assertFalse(APP.is_valid_cover_image("data:image/png;base64,AAAA", data_url=True))
        self.assertFalse(APP.is_valid_cover_image(valid.replace("image/png", "image/jpeg"), data_url=True))
        dimensions = struct.pack(">IIBBBBB", 5500, 5500, 8, 2, 0, 0, 0)
        header = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(dimensions)) + b"IHDR" + dimensions
        header += struct.pack(">I", zlib.crc32(b"IHDR" + dimensions) & 0xFFFFFFFF)
        oversized = "data:image/png;base64," + APP.base64.b64encode(header).decode("ascii")
        self.assertFalse(APP.is_valid_cover_image(oversized, data_url=True))
        with self.assertRaisesRegex(ValueError, "повреждено|PNG, JPEG"):
            APP.normalize_gallery_images([{"image_data": "data:image/png;base64,AAAA", "alt": "Пример"}])

    def test_failed_portfolio_save_restores_in_memory_mutations(self):
        original = APP.WebAppProject("Keep", "Local project", project_id=1, sort_order=4)
        portfolio = APP.Portfolio(projects=[original], next_id=2)
        app = object.__new__(APP.PortfolioApp)
        app.portfolio = portfolio
        app.data_path = Path("failure.sqlite3")
        app.save = lambda silent=False: False
        app.refresh = lambda: None

        snapshot = app._portfolio_snapshot()
        portfolio.projects[0] = APP.WebAppProject("Edited", "Unsaved edit", project_id=1, sort_order=9)
        portfolio.add(APP.WebAppProject("New", "Unsaved add"))

        self.assertFalse(app._persist_portfolio_change(snapshot))
        self.assertEqual(portfolio.projects, [original])
        self.assertIs(portfolio.projects[0], original)
        self.assertEqual((portfolio.next_id, original.sort_order), (2, 4))

    def test_desktop_muted_text_meets_normal_text_contrast_on_surfaces(self):
        def luminance(color):
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                      for value in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        foreground = luminance(APP.DESKTOP_PALETTE["muted"])
        for surface_name in ("background", "surface"):
            background = luminance(APP.DESKTOP_PALETTE[surface_name])
            lighter, darker = max(foreground, background), min(foreground, background)
            with self.subTest(surface=surface_name):
                self.assertGreaterEqual((lighter + 0.05) / (darker + 0.05), 4.5)

    def test_desktop_case_story_guide_counts_optional_blocks_like_web(self):
        empty = APP.case_story_completion_states(" ", "", "", "", "", "", False)
        self.assertEqual(empty, (False, False, False, False, False, False))
        metrics_only = APP.case_story_completion_states("", "", "", "", "", "рост заявок", False)
        self.assertEqual(metrics_only, (False, False, False, False, True, False))
        visuals_only = APP.case_story_completion_states("", "", "", "", "", "", True)
        self.assertEqual(visuals_only, (False, False, False, False, False, True))
        complete = APP.case_story_completion_states("Задача", "Роль", "Решение", "Этапы",
                                                    "Результат", "", True)
        self.assertEqual(complete, (True, True, True, True, True, True))

    def test_project_count_label_uses_correct_russian_plural_forms(self):
        for count, expected in ((0, "проектов"), (1, "проект"), (2, "проекта"),
                                (4, "проекта"), (5, "проектов"), (11, "проектов"),
                                (21, "проект"), (24, "проекта"), (25, "проектов")):
            with self.subTest(count=count):
                self.assertEqual(APP.project_count_label(count), expected)

    def test_project_is_abstract_and_subclasses_supply_links(self):
        with self.assertRaises(TypeError):
            APP.Project("Base", "Description")
        landing = APP.LandingProject("Site", "Description", demo_url="https://site.example")
        webapp = APP.WebAppProject("App", "Description", repository_url="https://code.example/repo")
        self.assertEqual(landing.get_main_link(), "https://site.example")
        self.assertEqual(webapp.get_main_link(), "https://code.example/repo")

    def test_reserved_example_links_are_not_mistaken_for_live_projects(self):
        for url in (
            "https://example.com",
            "https://www.example.org/map",
            "https://github.com/example/sample",
        ):
            with self.subTest(url=url):
                self.assertTrue(APP.is_placeholder_url(url))

    def test_json_import_merge_keeps_local_records_or_creates_independent_copies(self):
        local = APP.WebAppProject("Local", "My data", project_id=1, tags=["local"], sort_order=4)
        conflict = APP.WebAppProject("Imported", "Incoming data", project_id=1, tags=["incoming"], sort_order=1)
        addition = APP.LandingProject("New", "A new case", project_id=9, page_count=2, sort_order=1)
        current, incoming = APP.Portfolio("Local title", [local], 2), APP.Portfolio("Imported title", [conflict, addition], 10)

        merged, stats = APP.merge_portfolio_import(current, incoming, "keep-current")
        self.assertEqual(stats, {"added": 1, "copied": 0, "skipped": 1})
        self.assertEqual([project.title for project in merged.projects], ["Local", "New"])
        self.assertEqual((merged.title, merged.projects[0].tags, merged.projects[1].sort_order), ("Local title", ["local"], 5))
        self.assertEqual(current.projects[0].title, "Local")

        copied, stats = APP.merge_portfolio_import(current, incoming, "copy")
        duplicate = next(project for project in copied.projects if project.project_id != 1)
        self.assertEqual(stats, {"added": 1, "copied": 1, "skipped": 0})
        self.assertEqual((duplicate.project_id, duplicate.title), (2, "Imported — импорт"))
        duplicate.tags.append("independent")
        self.assertEqual(conflict.tags, ["incoming"])
        with self.assertRaisesRegex(ValueError, "стратегию"):
            APP.merge_portfolio_import(current, incoming, "replace")

    def test_validated_json_can_be_previewed_without_mutating_application(self):
        current = APP.Portfolio(projects=[APP.WebAppProject("Keep", "Local project", project_id=7)], next_id=8)
        target = object.__new__(APP.PortfolioApp)
        target.portfolio, target.developer = current, APP.Developer("Local", "Local role")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "incoming.json"
            record = APP.LandingProject("Incoming", "A valid project", project_id=1, page_count=1)
            payload = {"schema_version": 1, "title": "Incoming title", "developer": {"full_name": "Incoming", "specialization": "QA"},
                       "projects": [{"id": 1, "type": record.project_type, "title": record.title, "description": record.description,
                                     "created_at": record.created_at, "status": record.status, "page_count": 1, "technologies": []}]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            preview, developer = target._read_data(path, set_active_store=False, apply=False)
            for invalid_page_count in (1.5, True, "1", 0):
                broken = {**payload, "projects": [{**payload["projects"][0], "page_count": invalid_page_count}]}
                path.write_text(json.dumps(broken), encoding="utf-8")
                with self.subTest(page_count=invalid_page_count), self.assertRaises(ValueError):
                    target._read_data(path, set_active_store=False, apply=False)
        self.assertIs(target.portfolio, current)
        self.assertEqual((preview.projects[0].title, developer.full_name), ("Incoming", "Incoming"))

    def test_desktop_json_import_rejects_oversized_file_before_reading(self):
        target = object.__new__(APP.PortfolioApp)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "oversized.json"
            with path.open("wb") as handle:
                handle.truncate(APP.PORTFOLIO_IMPORT_MAX_BYTES + 1)
            with patch.object(Path, "open", side_effect=AssertionError("oversized JSON should not be read")):
                with self.assertRaisesRegex(ValueError, "больше 64 МиБ"):
                    target._read_data(path, set_active_store=False, apply=False)
        for url in ("https://github.com/daniil/portfolio", "https://my-portfolio.dev"):
            with self.subTest(url=url):
                self.assertFalse(APP.is_placeholder_url(url))

    def test_desktop_json_import_uses_strict_web_compatible_metadata(self):
        target = object.__new__(APP.PortfolioApp)
        base = {"schema_version": 1, "title": "Портфолио", "next_id": 2,
                "developer": {"full_name": "Автор", "specialization": "Разработчик"},
                "projects": [{"id": 1, "type": "Сайт / лендинг", "title": "Кейс",
                              "description": "Описание", "created_at": "2026-10-24",
                              "status": "Завершён", "technologies": [], "page_count": 1}]}
        invalid_payloads = [
            {"schema_version": "1"}, {"schema_version": True},
            {"next_id": "2"}, {"next_id": True}, {"next_id": 1.5},
            {"projects": [{**base["projects"][0], "id": 1.0}]},
            {"projects": [{**base["projects"][0], "featured": "false"}]},
            {"projects": [{**base["projects"][0], "title": "x" * 91}]},
            {"projects": [{**base["projects"][0], "description": "x" * 501}]},
            {"projects": [{**base["projects"][0], "role": "x" * 121}]},
            {"projects": [{**base["projects"][0], "outcome": "x" * 501}]},
            {"title": "x" * 121},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid-contract.json"
            for changes in invalid_payloads:
                payload = {**base, **changes}
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(change=next(iter(changes))), self.assertRaises(ValueError):
                    target._read_data(path, apply=False)

    def test_desktop_json_import_rejects_malformed_technology_fields(self):
        target = object.__new__(APP.PortfolioApp)
        existing = APP.Portfolio(projects=[APP.WebAppProject("Local", "Keep this project", project_id=7)], next_id=8)
        target.portfolio, target.developer = existing, APP.Developer("Local", "Developer")
        base = {"schema_version": 1, "title": "Portfolio", "next_id": 2,
                "developer": {"full_name": "Author", "specialization": "Developer"},
                "projects": [{"id": 1, "type": "Сайт / лендинг", "title": "Case", "description": "Description",
                              "created_at": "2026-10-24", "status": "Завершён", "page_count": 1,
                              "technologies": []}]}
        malformed = [
            [123],
            [{"name": 123}],
            [{"name": "Python", "category": 123}],
            [{"name": "Python", "version": 123}],
            [{"name": "x" * 61}],
            [{"name": "Python", "category": "x" * 61}],
            [{"name": "Python", "version": "x" * 41}],
            [{"name": " "}],
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid-technology.json"
            for technologies in malformed:
                payload = {**base, "projects": [{**base["projects"][0], "technologies": technologies}]}
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(technologies=technologies), self.assertRaises(ValueError):
                    target._read_data(path, set_active_store=False, apply=False)
        self.assertIs(target.portfolio, existing)
        self.assertEqual(target.portfolio.projects[0].title, "Local")

    def test_desktop_json_import_applies_shared_total_image_limits(self):
        target = object.__new__(APP.PortfolioApp)
        pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        project = {"id": 1, "type": "Сайт / лендинг", "title": "Кейс", "description": "Описание",
                   "created_at": "2026-10-24", "status": "Завершён", "technologies": [],
                   "page_count": 1, "gallery_images": [{"image_data": pixel, "alt": "Экран"}]}
        base = {"schema_version": 1, "title": "Портфолио", "next_id": 2,
                "developer": {"full_name": "Автор", "specialization": "Разработчик"}, "projects": []}
        too_many_images = {**base, "projects": [
            {**project, "id": i + 1, "gallery_images": [
                {"image_data": pixel, "alt": f"Экран {j}"} for j in range(10)]}
            for i in range(26)]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "too-many-images.json"
            path.write_text(json.dumps(too_many_images), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "не больше 250 изображений"):
                target._read_data(path, apply=False)

    def test_desktop_json_import_enforces_aggregate_decoded_pixel_budget(self):
        image_bytes = APP.io.BytesIO()
        APP.Image.new("1", (6000, 4000), 0).save(image_bytes, format="PNG", optimize=True)
        data = "data:image/png;base64," + APP.base64.b64encode(image_bytes.getvalue()).decode("ascii")
        base = {"type": "Сайт / лендинг", "title": "Кейс", "description": "Описание",
                "created_at": "2026-10-24", "status": "Завершён", "technologies": [], "page_count": 1,
                "cover_image_data": data}
        payload = {"schema_version": 1, "title": "Портфолио", "next_id": 7,
                   "developer": {"full_name": "Автор", "specialization": "Разработчик"},
                   "projects": [{**base, "id": index + 1} for index in range(6)]}
        target = object.__new__(APP.PortfolioApp)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pixel-budget.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "120 мегапикселей"):
                target._read_data(path, apply=False)

    def test_desktop_json_export_obeys_shared_file_size_boundary(self):
        payload = {"schema_version": 1, "title": "Портфолио", "next_id": 1,
                   "developer": {"full_name": "Автор", "specialization": "Разработчик"}, "projects": []}
        serialized = APP.serialize_portable_json(payload)
        size = len(serialized.encode("utf-8"))
        with patch.object(APP, "PORTFOLIO_IMPORT_MAX_BYTES", size):
            self.assertEqual(APP.serialize_portable_json(payload), serialized)
        with patch.object(APP, "PORTFOLIO_IMPORT_MAX_BYTES", size - 1):
            with self.assertRaisesRegex(ValueError, "больше 64 МиБ"):
                APP.serialize_portable_json(payload)

    def test_desktop_delete_confirmation_removes_only_selected_project(self):
        project = APP.WebAppProject("Synthetic QA case", "Temporary unit-test data", project_id=1)
        app = object.__new__(APP.PortfolioApp)
        app.portfolio = APP.Portfolio(projects=[project], next_id=2)
        app.data_path = None
        app.root = None
        app.selected = lambda: project
        app.refresh = lambda: None
        app._set_details = lambda message: setattr(app, "last_details_message", message)

        with patch.object(APP.messagebox, "askyesno", return_value=True) as confirm:
            app.delete()

        confirm.assert_called_once_with("Подтверждение", "Удалить «Synthetic QA case»?", parent=None)
        self.assertEqual(app.portfolio.projects, [])
        self.assertEqual(app.last_details_message, "Проект удалён.")
    def test_portfolio_model_repairs_a_stale_high_water_mark_before_allocating(self):
        existing = APP.WebAppProject("Existing", "Saved case", project_id=7)
        portfolio = APP.Portfolio(projects=[existing], next_id=1)

        self.assertEqual(portfolio.next_id, 8)
        portfolio.delete(existing.project_id)
        created = APP.WebAppProject("New", "New case")
        portfolio.add(created)
        self.assertEqual((created.project_id, portfolio.next_id), (8, 9))

    def test_portfolio_model_preserves_high_water_and_rejects_id_exhaustion(self):
        project = APP.WebAppProject("Existing", "Saved case", project_id=7)
        portfolio = APP.Portfolio(projects=[project], next_id=42)
        self.assertEqual(portfolio.next_id, 42)

        exhausted = APP.Portfolio(next_id=APP.PORTFOLIO_MAX_SAFE_INTEGER)
        with self.assertRaises(OverflowError):
            exhausted.add(APP.WebAppProject("Last", "No unsafe next id"))
        self.assertEqual((exhausted.projects, exhausted.next_id),
                         ([], APP.PORTFOLIO_MAX_SAFE_INTEGER))

    def test_ids_search_numeric_fields_and_delete(self):
        portfolio = APP.Portfolio()
        site = APP.LandingProject("Personal site", "A project", technologies=[APP.Technology("Python", version="3.13")], page_count=83, role="Student")
        app = APP.WebAppProject("CRM", "Orders", backend_stack="Flask", outcome="Faster tracking")
        portfolio.add(site)
        portfolio.add(app)
        self.assertEqual((site.project_id, app.project_id), (1, 2))
        self.assertEqual(portfolio.search(" PYTHON  "), [site])
        self.assertEqual(portfolio.search("83"), [site])
        self.assertEqual(portfolio.search("faster tracking"), [app])
        self.assertEqual(portfolio.search(""), [site, app])
        portfolio.delete(site.project_id)
        self.assertEqual(portfolio.projects, [app])

    def test_duplicate_creates_independent_unfeatured_copy_without_external_links(self):
        source = APP.WebAppProject(
            "CRM", "Клиентские заказы", created_at="2026-10-20", status="Опубликован",
            technologies=[APP.Technology("Python", version="3.13")], demo_url="https://example.com",
            repository_url="https://github.com/example/crm", backend_stack="Flask", tags=["CRM"],
            featured=True, context="Контекст", sort_order=1,
        )
        portfolio = APP.Portfolio()
        portfolio.add(source)
        duplicate = portfolio.duplicate(source.project_id)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.project_id, 2)
        self.assertEqual(duplicate.title, "CRM — копия")
        self.assertEqual(duplicate.created_at, date.today().isoformat())
        self.assertEqual((duplicate.demo_url, duplicate.repository_url), ("", ""))
        self.assertFalse(duplicate.featured)
        self.assertEqual((duplicate.context, duplicate.tags, duplicate.backend_stack), ("Контекст", ["CRM"], "Flask"))
        duplicate.technologies[0].version = "3.14"
        self.assertEqual(source.technologies[0].version, "3.13")
        self.assertIsNone(portfolio.duplicate(999))
        long_project = APP.LandingProject("X" * 100, "Long title")
        portfolio.add(long_project)
        long_copy = portfolio.duplicate(long_project.project_id)
        self.assertEqual(len(long_copy.title), 90)

    def test_validation_accepts_valid_records_and_rejects_bad_inputs(self):
        pages = APP.validate_project_input(" Site ", " Description ", "2026-10-24", "Завершён", "https://site.example", "", APP.PortfolioApp.TYPES[0], "3")
        self.assertEqual(pages, 3)
        web_pages = APP.validate_project_input("CRM", "Description", "2026-10-24", "В разработке", "", "https://code.example/repo", APP.PortfolioApp.TYPES[1], "unused")
        self.assertIsNone(web_pages)
        for value in ("0", "-2", "1.5", "abc"):
            with self.subTest(page_count=value), self.assertRaises(ValueError):
                APP.validate_project_input("Site", "Description", "2026-10-24", "Завершён", "", "", APP.PortfolioApp.TYPES[0], value)
        for url in ("ftp://site.example", "https://", "javascript:alert(1)", "https://user:pass@site.example/demo"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                APP.validate_project_input("Site", "Description", "2026-10-24", "Завершён", url, "", APP.PortfolioApp.TYPES[0], "1")
        with self.assertRaises(ValueError):
            APP.validate_project_input("  ", "Description", "2026-10-24", "Завершён", "", "", APP.PortfolioApp.TYPES[0], "1")

    def test_project_type_change_explains_fields_that_would_be_lost(self):
        landing, webapp = APP.PortfolioApp.TYPES
        self.assertEqual(APP.project_type_change_loss_fields(
            webapp, landing, "1", "https://code.example/repo", "Flask", True),
            ["Ссылка на репозиторий", "Серверная часть"])
        self.assertEqual(APP.project_type_change_loss_fields(
            landing, webapp, "7", "", "", True), ["Количество страниц (7)"])
        self.assertEqual(APP.project_type_change_loss_fields(
            landing, webapp, "1", "", "", False), [])
        self.assertEqual(APP.project_type_change_loss_fields(
            landing, webapp, "1", "", "", True), ["Количество страниц (1)"])
        self.assertEqual(APP.project_type_change_loss_fields(
            webapp, webapp, "1", "https://code.example/repo", "Flask", True), [])

    def test_json_round_trip_keeps_role_outcome_technology_and_featured(self):
        portfolio = APP.Portfolio(projects=[APP.LandingProject(
            "Site", "Description", "2026-10-24", "Опубликован",
            [APP.Technology("Python", "Language", "3.13")], "https://site.example",
            project_id=1, role="Frontend", outcome="Published", tags=["Образование", "Frontend"],
            context="Для небольшого учебного проекта", solution="Собрать витрину из карточек",
            process="Исследование, макет, разработка", metrics="Четыре отдельные страницы", featured=True, page_count=5)], next_id=2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "portfolio.json"
            source = object.__new__(APP.PortfolioApp)
            source.data_path, source.portfolio, source.developer = path, portfolio, APP.Developer("Student", "Developer")
            source.refresh = lambda: None
            source.save(silent=True)
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".json.tmp").exists())
            target = object.__new__(APP.PortfolioApp)
            target.refresh, target.details = lambda: None, DetailsStub()
            target._read_data(path)
            restored = target.portfolio.projects[0]
            self.assertEqual((restored.role, restored.outcome, restored.featured), ("Frontend", "Published", True))
            self.assertEqual(restored.tags, ["Образование", "Frontend"])
            self.assertEqual((restored.context, restored.solution, restored.process, restored.metrics),
                             ("Для небольшого учебного проекта", "Собрать витрину из карточек",
                              "Исследование, макет, разработка", "Четыре отдельные страницы"))
            self.assertEqual(restored.technologies[0].version, "3.13")
            self.assertEqual(target.portfolio.next_id, 2)

    def test_json_export_cannot_overwrite_active_store_and_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            active = Path(temp) / "portfolio.sqlite3"
            active.write_bytes(b"active sqlite bytes")
            app = object.__new__(APP.PortfolioApp)
            app.data_path = active
            app.portfolio = APP.Portfolio(projects=[APP.WebAppProject("Keep", "Description", project_id=1)])
            app.developer = APP.Developer("Student", "Developer")

            with self.assertRaisesRegex(ValueError, "активного файла данных"):
                app._write_json_export(active)
            self.assertEqual(active.read_bytes(), b"active sqlite bytes")

            destination = Path(temp) / "backup.json"
            destination.write_text("previous export", encoding="utf-8")
            app._write_json_export(destination)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["projects"][0]["title"], "Keep")
            self.assertEqual(list(Path(temp).glob(".backup.json.*.tmp")), [])

    def test_cover_art_survives_json_round_trip_and_rejects_remote_assets(self):
        pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
        project = APP.LandingProject("Site", "Description", "2026-10-24", "Завершён", project_id=1,
                                     cover_image_data=pixel,
                                     cover_position="28% 73%",
                                     cover_position_mobile="16% 88%",
                                     gallery_images=[{"image_data": pixel, "alt": "Экран страницы", "position": "35% 65%"}])
        portfolio = APP.Portfolio(projects=[project], next_id=2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "portfolio.json"
            source = object.__new__(APP.PortfolioApp)
            source.data_path, source.portfolio, source.developer = path, portfolio, APP.Developer("Student", "Developer")
            source.refresh = lambda: None
            source.save(silent=True)
            target = object.__new__(APP.PortfolioApp)
            target.refresh, target.details = lambda: None, DetailsStub()
            target._read_data(path)
            self.assertEqual(target.portfolio.projects[0].cover_image_data, pixel)
            self.assertEqual(target.portfolio.projects[0].cover_position, "28% 73%")
            self.assertEqual(target.portfolio.projects[0].cover_position_mobile, "16% 88%")
            self.assertEqual(target.portfolio.projects[0].gallery_images[0]["position"], "35% 65%")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["projects"][0]["cover_position"], "28% 73%")
            self.assertEqual(payload["projects"][0]["cover_position_mobile"], "16% 88%")
            payload["projects"][0]["cover_image"] = "https://example.org/remote.png"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "обложка"):
                target._read_data(path)

    def test_legacy_cover_position_defaults_and_invalid_crop_is_rejected(self):
        payload = {"projects": [{"id": 1, "type": "Сайт / лендинг", "title": "Case",
                                 "description": "Description", "created_at": "2026-10-24"}]}
        target = object.__new__(APP.PortfolioApp)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            portfolio, _ = target._read_data(path, apply=False)
            self.assertEqual(portfolio.projects[0].cover_position, "50% 46%")
            self.assertIsNone(portfolio.projects[0].cover_position_mobile)
            payload["projects"][0]["cover_position"] = "120% 50%"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "кадрирования"):
                target._read_data(path, apply=False)

    def test_invalid_json_does_not_replace_current_portfolio(self):
        current = APP.Portfolio(projects=[APP.WebAppProject("Keep", "Description", project_id=7)], next_id=8)
        target = object.__new__(APP.PortfolioApp)
        target.portfolio = current
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.json"
            path.write_text(json.dumps({"projects": [{"id": 1, "type": "Unknown", "title": "Bad", "description": "Bad", "created_at": "2026-10-24"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                target._read_data(path)
        self.assertIs(target.portfolio, current)

    def test_json_import_rejects_credentials_in_project_urls(self):
        target = object.__new__(APP.PortfolioApp)
        current = APP.Portfolio(projects=[APP.WebAppProject("Keep", "Description", project_id=7)], next_id=8)
        target.portfolio = current
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "userinfo.json"
            path.write_text(json.dumps({"projects": [{"id": 1, "type": APP.PortfolioApp.TYPES[1],
                "title": "Bad", "description": "Has credentials", "created_at": "2026-10-24",
                "demo_url": "https://user:pass@example.org/demo"}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "безопасной корректной ссылкой"):
                target._read_data(path, apply=False)
        self.assertIs(target.portfolio, current)

    def test_replace_import_backup_contains_complete_current_portfolio(self):
        project = APP.LandingProject(
            "Local case", "Keep this before replacement", project_id=41,
            page_count=7, tags=["local", "backup"], featured=True,
        )
        app = object.__new__(APP.PortfolioApp)
        app.root = None
        app.data_path = Path("active.sqlite3")
        app.portfolio = APP.Portfolio("Local title", [project], next_id=42)
        app.developer = APP.Developer("Student", "Developer")

        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "incoming.json"
            backup = Path(temp) / "before-replace.json"
            source.write_text('{"schema_version":1}', encoding="utf-8")
            with patch.object(APP.filedialog, "asksaveasfilename", return_value=str(backup)):
                self.assertTrue(app._backup_before_import_replace(source))

            payload = json.loads(backup.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], APP.DATA_SCHEMA_VERSION)
            self.assertEqual((payload["title"], payload["next_id"]), ("Local title", 42))
            self.assertEqual(payload["developer"]["full_name"], "Student")
            self.assertEqual(len(payload["projects"]), 1)
            self.assertEqual(
                (payload["projects"][0]["id"], payload["projects"][0]["title"],
                 payload["projects"][0]["page_count"], payload["projects"][0]["tags"]),
                (41, "Local case", 7, ["local", "backup"]),
            )
            self.assertFalse(backup.with_suffix(".json.tmp").exists())

    def test_replace_import_backs_up_before_persisting_replacement_to_sqlite(self):
        previous = APP.LandingProject(
            "Previous case", "Must be recoverable", project_id=7,
            page_count=3, featured=True,
        )
        incoming = APP.WebAppProject(
            "Incoming case", "Imported case", project_id=2,
            repository_url="https://example.test/repo", backend_stack="FastAPI",
        )

        with tempfile.TemporaryDirectory() as temp:
            active_db = Path(temp) / "portfolio.sqlite3"
            incoming_file = Path(temp) / "incoming.json"
            backup_file = Path(temp) / "before-replace.json"
            APP.SQLiteStore(active_db).save({
                "schema_version": APP.DATA_SCHEMA_VERSION,
                "title": "Previous portfolio",
                "next_id": 8,
                "developer": {"full_name": "Previous author", "specialization": "Developer"},
                "projects": [APP.PortfolioApp.record(object.__new__(APP.PortfolioApp), previous)],
            })
            incoming_file.write_text(json.dumps({
                "schema_version": APP.DATA_SCHEMA_VERSION,
                "title": "Imported portfolio",
                "next_id": 3,
                "developer": {"full_name": "Incoming author", "specialization": "Web developer"},
                "projects": [APP.PortfolioApp.record(object.__new__(APP.PortfolioApp), incoming)],
            }), encoding="utf-8")

            app = object.__new__(APP.PortfolioApp)
            app.root = None
            app.data_path = active_db
            app.portfolio = APP.Portfolio("Previous portfolio", [previous], next_id=8)
            app.developer = APP.Developer("Previous author", "Developer")
            app.refresh = lambda: None
            app._choose_import_strategy = lambda _candidate, _name: "replace"

            with patch.object(APP.filedialog, "askopenfilename", return_value=str(incoming_file)), \
                 patch.object(APP.filedialog, "asksaveasfilename", return_value=str(backup_file)), \
                 patch.object(APP.messagebox, "showinfo"):
                app.load()

            backup = json.loads(backup_file.read_text(encoding="utf-8"))
            stored = APP.SQLiteStore(active_db).load()
            self.assertEqual((backup["title"], backup["projects"][0]["title"]),
                             ("Previous portfolio", "Previous case"))
            self.assertEqual((stored["title"], stored["projects"][0]["title"]),
                             ("Imported portfolio", "Incoming case"))
            self.assertEqual(stored["developer"]["full_name"], "Incoming author")

    def test_replace_import_backup_cannot_overwrite_source_or_active_database(self):
        app = object.__new__(APP.PortfolioApp)
        app.root = None
        app.portfolio = APP.Portfolio()
        app.developer = APP.Developer("Student", "Developer")

        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "incoming.json"
            active = Path(temp) / "active.sqlite3"
            source.write_text("incoming", encoding="utf-8")
            active.write_text("active database", encoding="utf-8")
            app.data_path = active

            with patch.object(APP.messagebox, "showerror") as showerror:
                for protected_path in (source, active):
                    with self.subTest(path=protected_path.name):
                        with patch.object(APP.filedialog, "asksaveasfilename", return_value=str(protected_path)):
                            self.assertFalse(app._backup_before_import_replace(source))
                        showerror.assert_called_once()
                        showerror.reset_mock()

            self.assertEqual(source.read_text(encoding="utf-8"), "incoming")
            self.assertEqual(active.read_text(encoding="utf-8"), "active database")
            with patch.object(APP.filedialog, "asksaveasfilename", return_value=""):
                self.assertFalse(app._backup_before_import_replace(source))

    def test_markdown_export_includes_case_study_fields_and_featured_first(self):
        first = APP.WebAppProject("Regular", "A regular project", outcome="Visible outcome", tags=["учёт", "Портфолио"], context="A student team needs one source of truth.")
        featured = APP.LandingProject("Featured", "A selected project", role="Frontend", featured=True, page_count=1)
        featured.sort_order = 2
        first.sort_order = 1
        rendered = APP.render_portfolio_markdown(APP.Portfolio(projects=[first, featured]), APP.Developer("Student", "Web developer"))
        self.assertLess(rendered.index("## ★ Featured"), rendered.index("## Regular"))
        self.assertIn("**Моя роль:** Frontend", rendered)
        self.assertIn("**Результат:** Visible outcome", rendered)
        self.assertIn("**Теги:** учёт, Портфолио", rendered)
        self.assertIn("**Контекст задачи:**", rendered)

    def test_portfolio_add_assigns_stable_order_and_search_order_uses_it(self):
        portfolio = APP.Portfolio()
        second = APP.WebAppProject("A", "first alphabetically", sort_order=2)
        first = APP.WebAppProject("Z", "second alphabetically", sort_order=1)
        portfolio.add(second)
        portfolio.add(first)
        self.assertEqual([p.title for p in sorted(portfolio.projects, key=lambda p: p.sort_order)], ["Z", "A"])
        self.assertTrue(portfolio.move(second.project_id, -1))
        self.assertEqual([p.title for p in sorted(portfolio.projects, key=lambda p: p.sort_order)], ["A", "Z"])
        self.assertFalse(portfolio.move(second.project_id, -1))
        legacy = APP.WebAppProject("Legacy", "Without order")
        portfolio.add(legacy)
        self.assertEqual(legacy.sort_order, 3)

    def test_tag_normalization_and_search(self):
        self.assertEqual(APP.normalize_tags("Frontend, frontend, учебный кейс"), ["Frontend", "учебный кейс"])
        project = APP.WebAppProject("CRM", "Описание", tags=["учёт"])
        self.assertEqual(APP.Portfolio(projects=[project]).search("УЧЁТ"), [project])
        with self.assertRaises(ValueError):
            APP.normalize_tags(["x" * 33])
        with self.assertRaises(ValueError):
            APP.normalize_case_text("x" * 501, "Контекст", 500)

    def test_demo_projects_have_distinct_tags_for_first_run_filtering(self):
        app = object.__new__(APP.PortfolioApp)
        app.portfolio = APP.Portfolio()
        app._demo_data()
        self.assertTrue(any(project.tags for project in app.portfolio.projects))
        self.assertTrue(app.portfolio.projects[0].context)
        self.assertTrue(app.portfolio.projects[0].process)
        self.assertEqual(len(APP.Portfolio(projects=app.portfolio.search("автоматизация")).projects), 1)


    def test_desktop_demo_projects_have_distinct_local_covers_that_resolve_safely(self):
        app = object.__new__(APP.PortfolioApp)
        app.portfolio = APP.Portfolio()
        app._demo_data()
        projects = app.portfolio.projects
        expected = [
            "./assets/covers/portfolio-studio.webp",
            "./assets/covers/cleaning-crm.webp",
            "./assets/covers/city-courtyards.webp",
        ]
        self.assertEqual([project.cover_image for project in projects], expected)
        for project in projects:
            with self.subTest(cover=project.cover_image):
                self.assertTrue(APP.is_valid_cover_image(project.cover_image))
                resolved = APP.PortfolioApp._cover_source(app, "", project.cover_image)
                self.assertIsNotNone(resolved)
                self.assertTrue(resolved.is_file())
                self.assertEqual(resolved.parent.name, "covers")
        for legacy in (
            "./assets/covers/cleaning-crm.png",
            "./assets/covers/city-courtyards.png",
            "./assets/covers/portfolio-studio.png",
        ):
            with self.subTest(cover=legacy):
                resolved = APP.PortfolioApp._cover_source(app, "", legacy)
                self.assertIsNotNone(resolved)
                self.assertTrue(resolved.is_file())

    def test_reset_filters_clears_query_facets_and_featured_only(self):
        class VariableStub:
            def __init__(self, value):
                self.value = value
            def set(self, value):
                self.value = value
            def get(self):
                return self.value

        app = object.__new__(APP.PortfolioApp)
        app.query = VariableStub("python")
        app.type_filter = VariableStub(APP.PortfolioApp.TYPES[1])
        app.status_filter = VariableStub("Архив")
        app.tag_filter = VariableStub("Python")
        app.featured_only = VariableStub(True)
        refresh_calls = []
        app.refresh = lambda: refresh_calls.append(True)

        app.reset_filters()

        self.assertEqual(app.query.get(), "")
        self.assertEqual(app.type_filter.get(), "Все типы")
        self.assertEqual(app.status_filter.get(), "Все статусы")
        self.assertEqual(app.tag_filter.get(), "Все теги")
        self.assertFalse(app.featured_only.get())
        self.assertEqual(refresh_calls, [True])

    def test_search_facets_featured_filter_and_sort_apply_together(self):
        class VariableStub:
            def __init__(self, value):
                self.value = value
            def get(self):
                return self.value
            def set(self, value):
                self.value = value

        class WidgetStub:
            def configure(self, **_kwargs): pass
            def config(self, **_kwargs): pass
            def grid(self, **_kwargs): pass
            def grid_remove(self): pass
            def place_forget(self): pass

        projects = [
            APP.WebAppProject("Gamma", "portfolio crm case", status="В разработке", featured=True, tags=["Portfolio"]),
            APP.WebAppProject("Alpha", "portfolio crm case", status="В разработке", featured=True, tags=["portfolio"]),
            APP.WebAppProject("Beta", "portfolio crm case", status="В разработке", featured=True, tags=["Portfolio"]),
            APP.LandingProject("Delta", "portfolio crm case", status="В разработке", featured=True, tags=["Portfolio"]),
            APP.WebAppProject("Hidden", "portfolio crm case", status="Завершён", featured=True, tags=["Portfolio"]),
            APP.WebAppProject("Not featured", "portfolio crm case", status="В разработке", featured=False, tags=["Portfolio"]),
        ]
        app = object.__new__(APP.PortfolioApp)
        app.portfolio = APP.Portfolio(projects=projects, next_id=7)
        app.tree = WidgetStub()
        app.tree_vertical_scroll = WidgetStub()
        app.tree_horizontal_scroll = WidgetStub()
        app.tag_combo = WidgetStub()
        app.query = VariableStub("crm")
        app.type_filter = VariableStub(APP.PortfolioApp.TYPES[1])
        app.status_filter = VariableStub("В разработке")
        app.tag_filter = VariableStub("portfolio")
        app.featured_only = VariableStub(True)
        app.sort_column = "title"
        app.sort_ascending = False
        app.empty_state = WidgetStub()
        app.count_label = WidgetStub()
        app.footer = WidgetStub()
        app.developer = APP.Developer()
        app.data_path = None
        app.selected = lambda _notify=False: None
        app._render_visible = lambda _selected=None: None

        APP.PortfolioApp.refresh(app)

        self.assertEqual([project.title for project in app.visible], ["Gamma", "Beta", "Alpha"])

    def test_desktop_project_table_is_keyboard_focusable_before_row_actions(self):
        source = APP_PATH.read_text(encoding="utf-8")
        table_container = source.index("table = ttk.Frame(views)")
        action_container = source.index("bottom = ttk.Frame(outer)", table_container)
        tree = source.index("self.tree = ttk.Treeview(table", table_container)
        self.assertLess(table_container, action_container)
        self.assertIn('selectmode="browse", takefocus=True', source[tree:tree + 260])

    def test_desktop_sort_header_shows_and_toggles_direction_indicator(self):
        class TreeStub:
            def __init__(self):
                self.columns = ("title", "type", "status", "date", "pages", "tech", "featured")
                self.headings = {}
            def __getitem__(self, key):
                if key == "columns":
                    return self.columns
                raise KeyError(key)
            def heading(self, key, **kwargs):
                self.headings[key] = kwargs["text"]

        app = object.__new__(APP.PortfolioApp)
        app.tree = TreeStub()
        app.visible = [APP.WebAppProject("Gamma", "case"), APP.WebAppProject("Alpha", "case")]
        app.sort_column = "featured"
        app.sort_ascending = True
        app.selected = lambda _notify=False: None
        app._render_visible = lambda _selected=None: None

        APP.PortfolioApp.sort_by(app, "title")
        self.assertEqual(app.tree.headings["title"], "Название ↑")
        self.assertEqual([project.title for project in app.visible], ["Alpha", "Gamma"])

        APP.PortfolioApp.sort_by(app, "title")
        self.assertEqual(app.tree.headings["title"], "Название ↓")
        self.assertEqual([project.title for project in app.visible], ["Gamma", "Alpha"])


if __name__ == "__main__":
    unittest.main()




