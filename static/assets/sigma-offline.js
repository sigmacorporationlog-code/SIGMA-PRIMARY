/* SIGMA Primaire — pont offline navigateur v2.15 */
(function () {
  const DB = 'sigma-offline-v1';
  const VERSION = 3;
  let dbPromise;
  function db() {
    if (!dbPromise) dbPromise = new Promise((resolve, reject) => {
      const r = indexedDB.open(DB, VERSION);
      r.onupgradeneeded = () => {
        const d = r.result;
        if (!d.objectStoreNames.contains('cache')) d.createObjectStore('cache');
        if (!d.objectStoreNames.contains('entities')) {
          const e = d.createObjectStore('entities', {keyPath:'key'});
          e.createIndex('entity_type', 'entity_type');
          e.createIndex('assessment_id', 'assessment_id');
        }
        if (!d.objectStoreNames.contains('queue')) {
          const s = d.createObjectStore('queue', {keyPath:'id', autoIncrement:true});
          s.createIndex('created_at', 'created_at');
        }
        if (!d.objectStoreNames.contains('conflicts')) {
          const c = d.createObjectStore('conflicts', {keyPath:'id', autoIncrement:true});
          c.createIndex('created_at', 'created_at');
        }
      };
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    return dbPromise;
  }
  async function tx(store, mode, fn) {
    const d = await db();
    return new Promise((resolve, reject) => {
      const t = d.transaction(store, mode), s = t.objectStore(store);
      let result;
      try { result = fn(s); } catch (e) { reject(e); return; }
      t.oncomplete = () => resolve(result);
      t.onerror = () => reject(t.error);
    });
  }
  async function put(store, key, value) { return tx(store,'readwrite',s=>s.put(value,key)); }
  async function get(store, key) { return tx(store,'readonly',s=>new Promise((res,rej)=>{const r=s.get(key);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})); }
  async function addQueue(value) { return tx('queue','readwrite',s=>s.add(value)); }
  async function allQueue() { return tx('queue','readonly',s=>new Promise((res,rej)=>{const r=s.getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})); }
  async function delQueue(id) { return tx('queue','readwrite',s=>s.delete(id)); }
  async function addConflict(value) { return tx('conflicts','readwrite',s=>s.add(value)); }
  async function allConflicts() { return tx('conflicts','readonly',s=>new Promise((res,rej)=>{const r=s.getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})); }

  const Offline = {
    available: () => !!window.indexedDB,
    async cacheGet(key) { return get('cache', key); },
    async cachePut(key, value) { return put('cache', key, value); },
    async queueMutation(item) {
      return addQueue({...item, created_at: new Date().toISOString()});
    },
    async pendingCount() { return (await allQueue()).length; },
    async flush(api) {
      if (!navigator.onLine) return {flushed:0, remaining:await this.pendingCount()};
      let flushed = 0;
      let syncDeviceReady = false;
      const ensureSyncDevice = async (deviceId) => {
        if (syncDeviceReady) return;
        let appVersion='unknown'; try { const vr=await fetch('/api/version',{credentials:'same-origin'}); if(vr.ok){ const vd=await vr.json(); appVersion=String(vd.version||'unknown'); } } catch(_) {}
        await api('/api/sync/devices/register', {method:'POST', body:JSON.stringify({device_id:deviceId, name:deviceId, device_type:'browser', app_version:appVersion}), _offlineReplay:true});
        syncDeviceReady = true;
      };
      for (const item of await allQueue()) {
        try {
          if (item.kind === 'sync_operation') {
            await ensureSyncDevice(item.operation.device_id);
            const pushed = await api('/api/sync/push', {method:'POST', body:JSON.stringify([item.operation]), _offlineReplay:true});
            const accepted = (pushed.items || []).find(x => x.operation_id === item.operation.operation_id);
            if (!accepted || !['pending','applied'].includes(accepted.status)) {
              const e = new Error((accepted && accepted.error) || 'Synchronisation refusée');
              e._offlinePermanent = true; throw e;
            }
            if (accepted.status === 'pending') {
              const applied = await api('/api/sync/apply-batch', {method:'POST', body:JSON.stringify([item.operation.operation_id]), _offlineReplay:true});
              const result = (applied.items || [])[0];
              if (!result || result.status !== 'applied') {
                const e = new Error((result && result.error) || 'Application de la synchronisation impossible');
                if (result && result.http_status === 409) {
                  e._offlineConflict = true;
                  await addConflict({...item, error:e.message, created_at:new Date().toISOString()});
                }
                throw e;
              }
            }
            await delQueue(item.id); flushed++;
          } else {
            await api(item.path, {method:item.method, body:item.body, _offlineReplay:true});
            await delQueue(item.id); flushed++;
          }
        } catch (e) {
          if (e && e._offlinePermanent) await delQueue(item.id);
          else if (e && e._offlineConflict) await delQueue(item.id);
          else break;
        }
      }
      return {flushed, remaining:await this.pendingCount()};
    },
    async entityPut(entity_type, entity, key) {
      const value = {...entity, entity_type, key: String(key ?? entity.id ?? entity.client_id)};
      return put('entities', value.key, value);
    },
    async entityGet(entity_type, key) {
      const value = await get('entities', String(key));
      return value && value.entity_type === entity_type ? value : undefined;
    },
    async entityAll(entity_type) {
      return tx('entities','readonly',s=>new Promise((res,rej)=>{
        const idx=s.index('entity_type'), r=idx.getAll(IDBKeyRange.only(entity_type));
        r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error);
      }));
    },
    async gradeRowsPut(assessmentId, rows) {
      const existing = await this.gradeRowsGet(assessmentId).catch(()=>[]);
      const byStudent = new Map(existing.map(r => [Number(r.student_id), r]));
      for (const row of rows || []) {
        const sid = Number(row.student_id);
        const merged = {...(byStudent.get(sid) || {}), ...row, student_id:sid, assessment_id:Number(assessmentId)};
        await this.entityPut('grade_row', merged, `${assessmentId}:${sid}`);
      }
    },
    async gradeRowsGet(assessmentId) {
      const rows = await this.entityAll('grade_row');
      return rows.filter(r => Number(r.assessment_id) === Number(assessmentId)).map(({key,entity_type,...r})=>r);
    },
    async assessmentPut(assessment) { return this.entityPut('assessment', assessment); },
    async assessmentAll(classId, periodId) {
      const rows=await this.entityAll('assessment');
      return rows.filter(a => Number(a.class_id)===Number(classId) && Number(a.academic_period_id)===Number(periodId));
    },
    async studentRowsPut(rows) { for (const row of rows || []) await this.entityPut('student', row); },
    async studentRowsGet(classId) {
      const rows=await this.entityAll('student');
      return rows.filter(s => !classId || Number(s.class_id)===Number(classId) || Number(s.current_class_id)===Number(classId));
    },
    async queueGradeBatch(assessmentId, rows, maxScore) {
      const clean=[];
      const deviceId = localStorage.getItem('sigma_device_id') || (() => {
        const id = `browser-${crypto.randomUUID ? crypto.randomUUID() : Date.now() + '-' + Math.random().toString(16).slice(2)}`;
        localStorage.setItem('sigma_device_id', id); return id;
      })();
      for (const row of rows || []) {
        const score=row.score === null || row.score === '' || row.score === undefined ? null : Number(row.score);
        const limit=Number(row.max_score ?? maxScore);
        if (score !== null && (!Number.isFinite(score) || score < 0 || score > Number(maxScore) || score > limit)) throw new Error(`Note invalide pour l'élève ${row.student_id}: la note doit être comprise entre 0 et ${limit}.`);
        if (row.is_absent && score !== null) throw new Error(`L'élève ${row.student_id} est marqué absent et ne peut pas avoir de score.`);
        if (row.state === 'locked' || row.state === 'published') throw new Error('Ce résultat est verrouillé ou publié et ne peut plus être modifié hors ligne.');
        const resultId = row.result_id != null ? String(row.result_id) : `local-result-${assessmentId}-${row.student_id}`;
        const operationType = row.result_id != null ? 'update' : 'create';
        const payload = operationType === 'create'
          ? {activity_id:Number(assessmentId), student_entity_id:Number(row.student_id), score, max_score:limit, is_absent:!!row.is_absent, observation:row.observation||'', strengths:row.strengths||'', needs_support:row.needs_support||''}
          : {activity_id:Number(assessmentId), score, max_score:limit, is_absent:!!row.is_absent, observation:row.observation||'', strengths:row.strengths||'', needs_support:row.needs_support||''};
        clean.push({...row, student_id:Number(row.student_id), result_id:row.result_id ?? null, score, is_absent:!!row.is_absent, sync_version:Number(row.sync_version || 0), max_score:limit});
        await this.entityPut('evaluation_result', {...clean[clean.length-1], activity_id:Number(assessmentId)}, resultId);
        for (const item of await allQueue()) {
          if (item.kind === 'sync_operation' && item.entity_type === 'evaluation_result' && item.assessment_id === Number(assessmentId) && item.student_id === Number(row.student_id)) await delQueue(item.id);
        }
        await this.queueMutation({
          kind:'sync_operation', entity_type:'evaluation_result', assessment_id:Number(assessmentId), student_id:Number(row.student_id),
          operation:{operation_id:`${deviceId}-eval-${assessmentId}-${row.student_id}-${Date.now()}-${Math.random().toString(16).slice(2)}`, device_id:deviceId, entity_type:'evaluation_result', entity_id:resultId, operation_type:operationType, base_version:Number(row.sync_version || 0), payload}
        });
      }
      await this.gradeRowsPut(assessmentId, clean);
      return {queued:true, count:clean.length};
    },
    async resolveConflict(api, conflict, resolution) {
      if (!conflict || !conflict.operation || !conflict.operation.operation_id) throw new Error('Conflit local invalide');
      const op=conflict.operation;
      const result=await api(`/api/sync/conflicts/${encodeURIComponent(op.operation_id)}/resolve`, {method:'POST', body:JSON.stringify({resolution}), _offlineReplay:true});
      if (resolution === 'discard') {
        const conflicts=await allConflicts();
        for (const c of conflicts) if (c.operation && c.operation.operation_id === op.operation_id) { await tx('conflicts','readwrite',s=>s.delete(c.id)); }
        return result;
      }
      if (resolution === 'rebase') {
        op.base_version=Number(result.base_version || 0);
        await this.queueMutation({...conflict, kind:'sync_operation'});
        const conflicts=await allConflicts();
        for (const c of conflicts) if (c.operation && c.operation.operation_id === op.operation_id) { await tx('conflicts','readwrite',s=>s.delete(c.id)); }
        return this.flush(api);
      }
      throw new Error('Résolution inconnue');
    },
    async conflicts() { return allConflicts(); },
    async status() { return {online:navigator.onLine, pending:await this.pendingCount(), conflicts:(await allConflicts()).length}; }
  };
  window.SigmaOffline = Offline;
})();
