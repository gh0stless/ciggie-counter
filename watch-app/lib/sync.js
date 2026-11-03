// Abgleich mit dem Handy (Protokoll: watch-app/README.md).
// Einträge bleiben in state.pending, bis das Handy sie quittiert.

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

export function flush(state) {
  for (const entry of state.pending) {
    sendDict({ [KEY_CMD]: 'entry', [KEY_ID]: entry.id, [KEY_TIME]: entry.t })
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
