import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const app = readFileSync(new URL('../app.js', import.meta.url), 'utf8');

test('settings describe local storage consistently in browser and standalone app shells', () => {
  assert.match(app, /head\('ПРОСТРАНСТВО','Настройки и данные','Данные остаются на устройстве\. Автосинхронизации нет\.'/);
  assert.match(app, /Данные хранятся локально в этом приложении\./);
  assert.match(app, /Все проекты будут удалены из этого приложения\. Их можно восстановить в течение 7 секунд; затем удаление станет окончательным\./);
  assert.match(app, /Удалить все проекты\? Их можно восстановить в течение 7 секунд\./);
  assert.doesNotMatch(app, /Ваши проекты сохранены только в этом браузере/);
});
