import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  inspectPortfolioBackup,
  recordPortfolioBackup,
  PORTFOLIO_BACKUP_STATUS_KEY,
} from '../backup-status.js';

function preferenceStore({ writable = true } = {}) {
  const values = new Map();
  return {
    values,
    get(key) { return values.get(key) ?? null; },
    setPersistent(key, value) {
      if (!writable) return false;
      values.set(key, String(value));
      return true;
    },
  };
}

test('backup marker is current for its saved revision and becomes stale after a successful portfolio write', () => {
  const storage = preferenceStore();
  const savedAt = new Date('2026-11-06T12:30:00.000Z');
  const recorded = recordPortfolioBackup(7, storage, savedAt);

  assert.equal(recorded.persisted, true);
  assert.deepEqual(inspectPortfolioBackup(7, storage), {
    state: 'current', savedAt: savedAt.toISOString(),
  });
  assert.deepEqual(inspectPortfolioBackup(8, storage), {
    state: 'stale', savedAt: savedAt.toISOString(),
  });
});

test('backup timestamp is not recorded when preferences cannot persist it', () => {
  const storage = preferenceStore({ writable: false });
  const result = recordPortfolioBackup(3, storage);

  assert.equal(result.persisted, false);
  assert.equal(storage.values.has(PORTFOLIO_BACKUP_STATUS_KEY), false);
  assert.deepEqual(inspectPortfolioBackup(3, storage), {
    state: 'missing', savedAt: null,
  });
});

test('invalid backup metadata never appears as a successful current backup', () => {
  const storage = preferenceStore();
  storage.values.set(PORTFOLIO_BACKUP_STATUS_KEY, '{bad json');

  assert.deepEqual(inspectPortfolioBackup(1, storage), {
    state: 'unavailable', savedAt: null,
  });
});

test('settings explain an unconfirmed download and refresh backup state after portfolio changes', () => {
  const app = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /Проверьте, что файл появился в загрузках/);
  assert.match(app, /Отметка не обновлена/);
  assert.match(app, /void refreshBackupStatus\(\)/);
});
