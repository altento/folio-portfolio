// Small optional preferences must never prevent the main portfolio from opening.
// If the browser blocks localStorage, keep values in memory for this session.
export function createPreferenceStore(storageProvider = () => globalThis.localStorage, fallback = new Map()) {
  return {
    get(key) {
      try {
        const storage = storageProvider();
        if (!storage) throw new Error("Storage unavailable");
        return storage.getItem(key);
      } catch {
        return fallback.get(key) ?? null;
      }
    },
    set(key, value) {
      const normalized = String(value);
      let persisted = false;
      try {
        const storage = storageProvider();
        if (!storage) throw new Error("Storage unavailable");
        storage.setItem(key, normalized);
        persisted = true;
      } catch {
        // The in-memory copy below remains available if storage fails mid-session.
      }
      fallback.set(key, normalized);
      return persisted;
    },
    setPersistent(key, value) {
      const normalized = String(value);
      try {
        const storage = storageProvider();
        if (!storage) return false;
        storage.setItem(key, normalized);
        fallback.set(key, normalized);
        return true;
      } catch {
        return false;
      }
    },
  };
}
