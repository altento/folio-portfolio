# Целевой контрастный прогон v97

- URL: `http://127.0.0.1:8766/`
- Область: только shortcut-hint поиска и крестик закрытия detail dialog в обеих темах.
- Профиль: изолированный Chrome context, service workers отключены; пользовательская база не открывалась.

| Тема | Элемент | Цвет текста | Solid-фон | Контраст | Порог | Итог |
|---|---|---|---|---:|---:|---|
| light | projects_search_hint | #5f6368 | #f4f4f2 | 5.49 | 4.5 | PASS |
| light | project_detail_close | #25262a | #f5f5f3 | 13.85 | 3 | PASS |
| dark | projects_search_hint | #f0f0ed | #34353a | 10.72 | 4.5 | PASS |
| dark | project_detail_close | #25262a | #f5f5f3 | 13.85 | 3 | PASS |

Исходные computed styles и цепочка фона: `contrast-v97-targeted-results.json`.
