// Abgleich mit dem Handy, gemeinsam für Zähl- und Mess-Seite (Protokoll: watch-app/README.md).
// Einträge und Messungen bleiben in state.pending / state.mpending, bis das Handy sie quittiert.

import { sendDict } from './link'
import { save, now, newId, rollDay } from './store'

export const APP_ID = 1077701

// Schlüssel im PebbleKit-Dictionary
export const KEY_CMD = 0
export const KEY_ID = 1
export const KEY_TIME = 2
export const KEY_TODAY = 3
export const KEY_LAST = 4
export const KEY_NEXT = 5
export const KEY_PHASE = 6
export const KEY_HR = 7
export const KEY_SPO2 = 8
export const KEY_STRESS = 9

// Für das Ziffernblatt: systemweiter Zwischenspeicher (bis zum Neustart des Bands)
export function share(state) {
  hmFS.SysProSetChars('ciggie', [state.day, state.today, state.last, state.next].join('|'))
}

// Eine Zigarette zählen; Ergebnis: ihre Eintrags-ID
export function addEntry(state) {
  const t = now()
  rollDay(state)
  const id = newId()
  state.pending.push({ id, t })
  state.today += 1
  state.last = t
  // bis das Handy quittiert: Pause so lang wie die letzte bekannte
  if (state.gap > 0) state.next = t + state.gap
  save(state)
  share(state)
  return id
}

// Messung vormerken; m: { id, phase: 'before' | 'after', t, hr, spo2, stress } (0 = kein Wert)
export function addMeasurement(state, m) {
  state.mpending.push(m)
  save(state)
}

export function flush(state) {
  for (const entry of state.pending) {
    sendDict({ [KEY_CMD]: 'entry', [KEY_ID]: entry.id, [KEY_TIME]: entry.t })
  }
  for (const m of state.mpending) {
    sendDict({
      [KEY_CMD]: 'measure', [KEY_ID]: m.id, [KEY_PHASE]: m.phase, [KEY_TIME]: m.t,
      [KEY_HR]: m.hr, [KEY_SPO2]: m.spo2, [KEY_STRESS]: m.stress,
    })
  }
}

export function hello() {
  sendDict({ [KEY_CMD]: 'hello' })
}

export function handleData(state, values) {
  const cmd = values[KEY_CMD]
  if (cmd === 'ack') {
    const id = values[KEY_ID]
    state.pending = state.pending.filter((e) => e.id !== id)
  }
  if (cmd === 'mack') {
    const id = values[KEY_ID]
    const phase = values[KEY_PHASE]
    state.mpending = state.mpending.filter((m) => !(m.id === id && m.phase === phase))
  }
  if (cmd === 'ack' || cmd === 'state') {
    // Das Handy kennt alle Quellen (Butt Bin, App, Nextcloud) – seine Zahl gilt,
    // plus was hier noch unterwegs ist
    if (typeof values[KEY_TODAY] === 'number') {
      rollDay(state)
      state.today = values[KEY_TODAY] + state.pending.length
    }
    if (typeof values[KEY_LAST] === 'number' && values[KEY_LAST] > state.last) {
      state.last = values[KEY_LAST]
    }
    if (typeof values[KEY_NEXT] === 'number') {
      state.next = values[KEY_NEXT]
      state.gap = state.next > state.last ? state.next - state.last : 0
    }
  }
  save(state)
  share(state)
}
