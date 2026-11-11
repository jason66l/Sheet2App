/**
 * Keeps the chosen spreadsheet across the Google sign-in redirect.
 *
 * Signing in leaves the page and comes back, which would lose the File object.
 * We park it in IndexedDB (sessionStorage is too small for a 25 MB file) and
 * pick it up again once the user is signed in.
 */
const DB = 's2a';
const STORE = 'pending';
const KEY = 'upload';

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function run<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return open().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const req = fn(db.transaction(STORE, mode).objectStore(STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      }),
  );
}

export const savePendingUpload = (file: File) => run('readwrite', (s) => s.put(file, KEY)).then(() => undefined);

export async function takePendingUpload(): Promise<File | null> {
  const file = await run<File | undefined>('readonly', (s) => s.get(KEY));
  await run('readwrite', (s) => s.delete(KEY));
  return file ?? null;
}
