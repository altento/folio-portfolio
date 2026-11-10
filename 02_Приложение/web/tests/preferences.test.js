import test from 'node:test';
import assert from 'node:assert/strict';
import { createPreferenceStore } from '../preferences.js';

test('optional preferences fall back to session memory when localStorage is blocked', () => {
  const preferences = createPreferenceStore(() => { throw new DOMException('Blocked', 'SecurityError'); });
  assert.equal(preferences.get('theme'), null);
  preferences.set('theme', 'dark');
  assert.equal(preferences.get('theme'), 'dark');
});

test('optional preferences use localStorage when available and fall back after an operation fails', () => {
  const values = new Map();
  let failReads = false;
  const preferences = createPreferenceStore(() => ({
    getItem(key) { if (failReads) throw new DOMException('Blocked', 'SecurityError'); return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, String(value)); },
  }));
  preferences.set('layout', 'list');
  assert.equal(preferences.get('layout'), 'list');
  failReads = true;
  preferences.set('layout', 'cards');
  assert.equal(preferences.get('layout'), 'cards');
});

test('backup status is never reported as persistent when localStorage cannot save it', () => {
  const blocked = createPreferenceStore(() => { throw new DOMException('Blocked', 'SecurityError'); });
  assert.equal(blocked.setPersistent('backup-status', 'saved'), false);
  assert.equal(blocked.get('backup-status'), null);

  const values = new Map();
  const available = createPreferenceStore(() => ({
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, String(value)); },
  }));
  assert.equal(available.setPersistent('backup-status', 'saved'), true);
  assert.equal(available.get('backup-status'), 'saved');
});
