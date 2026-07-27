/*
 * Acces IndexedDB bas niveau a la file d'attente des actions hors ligne
 * ("outbox"). Fichier partage tel quel entre :
 *  - les pages (inclus via <script>, `self` == `window`) ;
 *  - le Service Worker (inclus via `importScripts()`, `self` == le contexte
 *    global du worker) ;
 * d'ou l'usage de `self.IdbOutbox` plutot que d'un module ES (ni les pages
 * ni le Service Worker "classique" de ce projet n'utilisent de bundler).
 *
 * Un seul object store `outbox` (cle `localId`, auto-incrementee) : chaque
 * ligne represente une action deja tentee en direct (fetch) qui a echoue par
 * manque de reseau, et qui attend d'etre rejouee automatiquement des que le
 * navigateur declenche l'evenement 'sync' (voir service-worker.js).
 */
(function (global) {
  const DB_NAME = 'empotage-offline-outbox';
  const DB_VERSION = 1;
  const STORE = 'outbox';

  function openDb() {
    return new Promise(function (resolve, reject) {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function () {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: 'localId', autoIncrement: true });
          store.createIndex('by_status', 'status');
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function add(record) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).add(record);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function getAll() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { reject(req.error); };
      });
    });
  }

  function getByStatus(status) {
    return getAll().then(function (rows) {
      return rows.filter(function (r) { return r.status === status; });
    });
  }

  function getNeedsAttention() {
    return getAll().then(function (rows) {
      return rows.filter(function (r) { return r.status === 'conflict' || r.status === 'failed'; });
    });
  }

  function update(localId, changes) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction(STORE, 'readwrite');
        const store = tx.objectStore(STORE);
        const getReq = store.get(localId);
        getReq.onsuccess = function () {
          const record = getReq.result;
          if (record) {
            Object.assign(record, changes);
            store.put(record);
          }
        };
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function remove(localId) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(localId);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  global.IdbOutbox = { add, getAll, getByStatus, getNeedsAttention, update, remove };
})(self);
