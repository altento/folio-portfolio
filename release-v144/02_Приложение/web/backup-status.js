export const PORTFOLIO_BACKUP_STATUS_KEY = 'folio-portfolio-backup-status-v1';

export function inspectPortfolioBackup(currentRevision, preferences) {
  let stored;
  try {
    const raw = preferences.get(PORTFOLIO_BACKUP_STATUS_KEY);
    if (!raw) return { state: 'missing', savedAt: null };
    stored = JSON.parse(raw);
  } catch {
    return { state: 'unavailable', savedAt: null };
  }
  if (stored?.version !== 1 || !Number.isSafeInteger(stored.revision) || stored.revision < 0 ||
      !Number.isFinite(Date.parse(stored.savedAt))) {
    return { state: 'unavailable', savedAt: null };
  }
  return {
    state: stored.revision === currentRevision ? 'current' : 'stale',
    savedAt: stored.savedAt,
  };
}

export function recordPortfolioBackup(revision, preferences, now = new Date()) {
  const record = { version: 1, revision, savedAt: now.toISOString() };
  const persisted = Number.isSafeInteger(revision) && revision >= 0 &&
    preferences.setPersistent(PORTFOLIO_BACKUP_STATUS_KEY, JSON.stringify(record));
  return { persisted: Boolean(persisted), savedAt: record.savedAt };
}
