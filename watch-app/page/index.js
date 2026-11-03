import { connect, disconnect, isReady, sendDict } from '../lib/link'
import { load, save, now, newId, rollDay } from '../lib/store'

// Palette der Projekt-Flagge
const ESPRESSO = 0x2d0800
const KAFFEE = 0x590f02
const ROAST = 0x470d02
const FILTER = 0xf9a948
const PAPIER = 0xffffff
const ASCHE = 0xa1a1a1

const APP_ID = 1077701

// Schlüssel im PebbleKit-Dictionary (siehe watch-app/README.md)
const KEY_CMD = 0
const KEY_ID = 1
const KEY_TIME = 2
const KEY_TODAY = 3
const KEY_LAST = 4
const KEY_NEXT = 5

let state
let countText
let lastText
let statusText
let vibrate
let retryTimer

function hhmm(seconds) {
  if (!seconds) return '--:--'
  const d = new Date(seconds * 1000)
  const h = d.getHours()
  const m = d.getMinutes()
  return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m
}

function render() {
  countText.setProperty(hmUI.prop.TEXT, String(state.today))
  lastText.setProperty(hmUI.prop.TEXT, hhmm(state.last))
  const link = isReady() ? '●' : '○'
  const pending = state.pending.length ? '  ↑' + state.pending.length : ''
  statusText.setProperty(hmUI.prop.TEXT, link + pending)
  // Für das Ziffernblatt: systemweiter Zwischenspeicher (bis zum Neustart des Bands)
  hmFS.SysProSetChars('ciggie', [state.day, state.today, state.last, state.next].join('|'))
}

function flush() {
  for (const entry of state.pending) {
    sendDict({ [KEY_CMD]: 'entry', [KEY_ID]: entry.id, [KEY_TIME]: entry.t })
  }
}

function stamp() {
  const t = now()
  rollDay(state)
  state.pending.push({ id: newId(), t })
  state.today += 1
  state.last = t
  // bis das Handy quittiert: Pause so lang wie die letzte bekannte
  if (state.gap > 0) state.next = t + state.gap
  save(state)
  try {
    vibrate.stop()
    vibrate.scene = 25
    vibrate.start()
  } catch (e) {}
  if (isReady()) flush()
  render()
}

function onReady() {
  sendDict({ [KEY_CMD]: 'hello' })
  flush()
  render()
}

function onData(values) {
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
    save(state)
  }
  render()
}

Page({
  build() {
    state = load()

    hmUI.createWidget(hmUI.widget.FILL_RECT, { x: 0, y: 0, w: 194, h: 368, color: ESPRESSO })

    statusText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 0, y: 14, w: 194, h: 28,
      text: '', text_size: 20, color: ASCHE,
      align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V
    })

    countText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 0, y: 48, w: 194, h: 96,
      text: '0', text_size: 80, color: FILTER,
      align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V
    })

    lastText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 0, y: 144, w: 194, h: 32,
      text: '', text_size: 24, color: ASCHE,
      align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V
    })

    hmUI.createWidget(hmUI.widget.BUTTON, {
      x: 17, y: 196, w: 160, h: 140, radius: 32,
      normal_color: KAFFEE, press_color: ROAST,
      text: '+1', text_size: 56, color: PAPIER,
      click_func: stamp
    })

    vibrate = hmSensor.createSensor(hmSensor.id.VIBRATE)

    render()
    connect(APP_ID, onReady, onData)

    // Unbestätigte Einträge regelmäßig erneut senden
    retryTimer = timer.createTimer(15000, 15000, () => {
      if (isReady() && state.pending.length) flush()
      render()
    })
  },

  onDestroy() {
    if (retryTimer) timer.stopTimer(retryTimer)
    disconnect()
  }
})
