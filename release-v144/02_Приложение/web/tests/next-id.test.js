import test from 'node:test';
import assert from 'node:assert/strict';
import {
  duplicateProject,
  mergePortfolioImport,
  normalizeDeveloper,
  normalizeProject,
  parsePortfolioFile,
  restoreProjectsWithUniqueIds,
  serializePortfolio,
} from '../core.js';

function project(id, title = `Project ${id}`) {
  return normalizeProject({
    id,
    type: 'Сайт / лендинг',
    title,
    description: 'A portfolio case',
    created_at: '2026-11-05',
    status: 'Завершён',
    technologies: ['HTML'],
    page_count: 2,
  });
}

test('keeps the desktop high-water next_id when parsing and serializing a backup', () => {
  const model = parsePortfolioFile(JSON.stringify({ next_id: 47, projects: [project(5)] }));
  assert.equal(model.next_id, 47);
  assert.equal(serializePortfolio(model).next_id, 47);
});

test('duplicates a project with the persisted next_id instead of reusing a deleted ID', () => {
  const projects = [project(5)];
  const duplicate = duplicateProject(projects, 5, '2026-11-05', 47);
  assert.equal(duplicate.id, 47);
  assert.equal(projects.length, 2);
  assert.equal(serializePortfolio({
    title: 'folio',
    developer: normalizeDeveloper({ full_name: 'Author', specialization: 'Developer' }),
    projects,
    next_id: 48,
  }).next_id, 48);
});

test('keeps high-water IDs through import merging and copy collisions', () => {
  const merged = mergePortfolioImport(
    [project(4, 'Current')],
    [project(4, 'Incoming'), project(9, 'New')],
    'copy',
    20,
    30,
  );
  assert.deepEqual(merged.projects.map(item => item.id), [4, 30, 9]);
  assert.equal(merged.nextId, 31);
  assert.equal(merged.stats.copied, 1);
});

test('restores a deleted project with a fresh ID if an import reused its old ID', () => {
  const current = [project(5, 'Imported replacement')];
  const removed = [{ project: project(5, 'Deleted case'), index: 0 }];
  const restored = restoreProjectsWithUniqueIds(current, removed, 12);
  assert.deepEqual(restored.projects.map(item => [item.id, item.title]), [
    [12, 'Deleted case'],
    [5, 'Imported replacement'],
  ]);
  assert.equal(restored.nextId, 13);
  assert.equal(restored.restored[0].originalId, 5);
});

test('undo preserves an unclaimed deleted ID and does not lower the high-water mark', () => {
  const restored = restoreProjectsWithUniqueIds([project(8)], [{ project: project(5), index: 0 }], 20);
  assert.deepEqual(restored.projects.map(item => item.id), [5, 8]);
  assert.equal(restored.nextId, 20);
});
