import { connect, disconnect, isReady } from '../lib/link'
import { load, localDate } from '../lib/store'
import { APP_ID, addEntry, flush, hello, handleData, share } from '../lib/sync'

// Palette der Projekt-Flagge
const ESPRESSO = 0x2d0800
const KAFFEE = 0x590f02
const ROAST = 0x470d02
const FILTER = 0xf9a948
const PAPIER = 0xffffff
const ASCHE = 0xa1a1a1

let state
let countText
let lastText
let statusText
let vibrate
let retryTimer
// Schnellzählen vom Ziffernblatt (Doppeltipp): zählen, quittieren lassen, zurück
let quick = false
let backTimer = null

function goBack(delay) {
  if (backTimer) timer.stopTimer(backTimer)
  backTimer = timer.createTimer(delay, delay, () => {
    timer.stopTimer(backTimer)
    backTimer = null
    hmApp.goBack()
  })
}

function hhmm(seconds) {
  if (!seconds) return '--:--'
  const d = localDate(seconds)
  const h = d.getUTCHours()
  const m = d.getUTCMinutes()
  return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m
}

function render() {
  countText.setProperty(hmUI.prop.TEXT, String(state.today))
  lastText.setProperty(hmUI.prop.TEXT, hhmm(state.last))
  const link = isReady() ? '●' : '○'
  const pending = state.pending.length ? '  ↑' + state.pending.length : ''
  statusText.setProperty(hmUI.prop.TEXT, link + pending)
  share(state)
}

function stamp() {
  addEntry(state)
  try {
    vibrate.stop()
    vibrate.scene = 25
    vibrate.start()
  } catch (e) {}
  if (isReady()) flush(state)
  render()
}

function onReady() {
  hello()
  flush(state)
  render()
}

function onData(values) {
  handleData(state, values)
  render()
  if (quick && !state.pending.length) goBack(1500)
}

Page({
  onInit(param) {
    quick = param === 'count'
  },

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
    if (quick) {
      stamp()
      // ohne Quittung trotzdem zurück; der Eintrag bleibt vorgemerkt
      goBack(8000)
    }

    // Unbestätigte Einträge regelmäßig erneut senden
    retryTimer = timer.createTimer(15000, 15000, () => {
      if (isReady() && state.pending.length) flush(state)
      render()
    })
  },

  onDestroy() {
    if (retryTimer) timer.stopTimer(retryTimer)
    if (backTimer) timer.stopTimer(backTimer)
    disconnect()
  }
})
