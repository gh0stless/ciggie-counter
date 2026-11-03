// Mess-Seite: Puls und Blutsauerstoff (gemessen) und Stress (letzter Firmware-Wert) vor und nach einer Zigarette.
// Öffnen startet sofort die Messung: ohne laufende Sitzung "vorher" (danach wird gezählt),
// mit Sitzung "nachher". Sensoren per start() und Abfrage jede Sekunde, keine Listener
// (die brachten das Band 7 zum Absturz, siehe docs/zepp-os-band7-tricks.md).

import { connect, disconnect, isReady } from '../lib/link'
import { load, save, now } from '../lib/store'
import { APP_ID, addEntry, addMeasurement, flush, hello, handleData } from '../lib/sync'

const ESPRESSO = 0x2d0800
const KAFFEE = 0x590f02
const ROAST = 0x470d02
const FILTER = 0xf9a948
const PAPIER = 0xffffff
const ASCHE = 0xa1a1a1

// Eine Vorher-Messung ohne Nachher verfällt nach dieser Zeit
const SESSION_MAX_AGE = 3 * 3600

let state
let titleText
let statusText
let valuesText
let afterButton
let vibrate
let poll = null
let retryTimer = null
let sensors = {}
let measuring = false

function buzz() {
  try {
    vibrate.stop()
    vibrate.scene = 25
    vibrate.start()
  } catch (e) {}
}

function read(sensor, prop) {
  try {
    const v = sensor[prop]
    return typeof v === 'number' ? v : 0
  } catch (e) {
    return 0
  }
}

// Ablauf je Sensor: wann ist ein frischer Wert da, wie lange höchstens warten
const STEPS = [
  {
    // current bleibt ohne Listener 0; die fertige Messung landet in last
    key: 'hr', label: 'Puls', sensor: 'heart', max: 30,
    ready: (s, ctx) => ctx.elapsed >= 12 && (read(s, 'current') > 0 || read(s, 'last') !== ctx.l0),
    value: (s) => read(s, 'current') || read(s, 'last'),
    // ohne neue Messung: jüngster Wert des Bandes
    fallback: (s) => read(s, 'last'),
  },
  {
    key: 'spo2', label: 'Sauerstoff', sensor: 'spo2', max: 45,
    // fertig, wenn sich der Zeitstempel ändert (retcode taugt dafür nicht)
    ready: (s, ctx) => read(s, 'time') !== ctx.t0 && read(s, 'current') > 0,
    value: (s) => read(s, 'current'),
  },
  {
    // Stress errechnet die Firmware über längere Zeit; eine erzwungene Messung per start()
    // ließ das Band nach gut 2 Minuten neu starten. Daher nur den letzten Wert lesen.
    key: 'stress', label: 'Stress', sensor: 'stress', max: 0, passive: true,
    ready: () => true,
    value: (s) => read(s, 'current'),
  },
]

function stopSensors() {
  for (const k of ['heart', 'spo2']) {
    try { sensors[k].stop() } catch (e) {}
  }
}

function stopAll() {
  if (poll) {
    timer.stopTimer(poll)
    poll = null
  }
  stopSensors()
  try { hmSetting.setBrightScreenCancel() } catch (e) {}
  measuring = false
}

function show(title, status, values) {
  titleText.setProperty(hmUI.prop.TEXT, title)
  statusText.setProperty(hmUI.prop.TEXT, status)
  valuesText.setProperty(hmUI.prop.TEXT, values)
}

function showButton(visible) {
  afterButton.setProperty(hmUI.prop.VISIBLE, visible)
}

function fmt(m) {
  return [
    'Puls ' + (m.hr || '–'),
    'Sauerstoff ' + (m.spo2 ? m.spo2 + ' %' : '–'),
    'Stress ' + (m.stress || '–'),
  ].join('\n')
}

function arrow(a, b, unit) {
  return (a || '–') + ' → ' + (b || '–') + (unit && b ? unit : '')
}

// Alle Sensoren nacheinander, dann done(Messwerte)
function measureAll(title, done) {
  measuring = true
  showButton(false)
  try { hmSetting.setBrightScreen(240) } catch (e) {}
  buzz()
  const result = { t: now(), hr: 0, spo2: 0, stress: 0 }
  let index = -1
  let ctx = null

  function next() {
    stopSensors()
    index += 1
    if (index >= STEPS.length) {
      stopAll()
      buzz()
      done(result)
      return
    }
    const step = STEPS[index]
    const sensor = sensors[step.sensor]
    ctx = { elapsed: 0, t0: read(sensor, 'time'), l0: read(sensor, 'last') }
    if (step.passive) {
      result[step.key] = step.value(sensor)
      next()
      return
    }
    try { sensor.start() } catch (e) {}
  }

  next()
  poll = timer.createTimer(1000, 1000, () => {
    const step = STEPS[index]
    const sensor = sensors[step.sensor]
    ctx.elapsed += 1
    show(title, step.label + ' … ' + ctx.elapsed + ' s', fmt(result))
    if (step.ready(sensor, ctx)) {
      result[step.key] = step.value(sensor)
      next()
    } else if (ctx.elapsed >= step.max) {
      if (step.fallback) result[step.key] = step.fallback(sensor)
      next()
    }
  })
}

function measureBefore() {
  measureAll('Vorher', (m) => {
    const id = addEntry(state)
    state.session = { id, t: m.t, before: m }
    addMeasurement(state, { id, phase: 'before', t: m.t, hr: m.hr, spo2: m.spo2, stress: m.stress })
    if (isReady()) flush(state)
    show('Jetzt rauchen', 'gezählt', fmt(m))
    showButton(true)
  })
}

function measureAfter() {
  const session = state.session
  measureAll('Nachher', (m) => {
    addMeasurement(state, { id: session.id, phase: 'after', t: m.t, hr: m.hr, spo2: m.spo2, stress: m.stress })
    state.session = null
    save(state)
    if (isReady()) flush(state)
    const b = session.before
    show('Vorher → nachher', '', [
      'Puls ' + arrow(b.hr, m.hr),
      'SpO2 ' + arrow(b.spo2, m.spo2, ' %'),
      'Stress ' + arrow(b.stress, m.stress),
    ].join('\n'))
  })
}

function start() {
  const session = state.session
  if (session && now() - session.t < SESSION_MAX_AGE) measureAfter()
  else {
    state.session = null
    measureBefore()
  }
}

Page({
  build() {
    state = load()

    hmUI.createWidget(hmUI.widget.FILL_RECT, { x: 0, y: 0, w: 194, h: 368, color: ESPRESSO })
    titleText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 0, y: 14, w: 194, h: 40, text: '', text_size: 30, color: FILTER,
      align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V,
    })
    statusText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 0, y: 58, w: 194, h: 32, text: '', text_size: 22, color: ASCHE,
      align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V,
    })
    valuesText = hmUI.createWidget(hmUI.widget.TEXT, {
      x: 8, y: 100, w: 178, h: 140, text: '', text_size: 24, color: PAPIER,
      align_h: hmUI.align.CENTER_H, text_style: hmUI.text_style.WRAP,
    })
    afterButton = hmUI.createWidget(hmUI.widget.BUTTON, {
      x: 17, y: 256, w: 160, h: 90, radius: 28,
      normal_color: KAFFEE, press_color: ROAST,
      text: 'Nachher\nmessen', text_size: 26, color: PAPIER,
      click_func: () => { if (!measuring) measureAfter() },
    })
    showButton(false)

    vibrate = hmSensor.createSensor(hmSensor.id.VIBRATE)
    sensors = {
      heart: hmSensor.createSensor(hmSensor.id.HEART),
      spo2: hmSensor.createSensor(hmSensor.id.SPO2),
      stress: hmSensor.createSensor(hmSensor.id.STRESS),
    }

    connect(APP_ID, () => { hello(); flush(state) }, (values) => handleData(state, values))
    retryTimer = timer.createTimer(15000, 15000, () => {
      if (isReady() && (state.pending.length || state.mpending.length)) flush(state)
    })

    start()
  },

  onDestroy() {
    stopAll()
    if (retryTimer) timer.stopTimer(retryTimer)
    disconnect()
  },
})
