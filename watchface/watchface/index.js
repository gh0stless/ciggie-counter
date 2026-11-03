// Ciggie-Counter-Ziffernblatt: Uhrzeit, Datum, Akku, Schritte, Puls, Stress, Schlaf und die Pause bis zur nächsten.
// Den Stand liefern die Band-App (systemweiter Zwischenspeicher) und das Handy (Wetter-Kanal),
// siehe readShared() und watch-app/README.md; hier wird er nur gelesen und jede Minute neu gerechnet.

// Palette der Projekt-Flagge
const ESPRESSO = 0x2d0800
const KAFFEE = 0x590f02
const FILTER = 0xf9a948
const PAPIER = 0xffffff
const ASCHE = 0xa1a1a1

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

// Band-App: Doppeltipp auf den Ciggie-Kasten zählt sofort
const APP_ID = 1077701
const TAP_MS = 450

let taps = 0
let tapTimer = null

let clock
let battery
let steps
let heart
let stress
let sleep
let weather
let timeText
let dateText
let infoText
let healthText
let sleepText
let pauseText
let nextText
let todayText

function pad(n) {
  return (n < 10 ? '0' : '') + n
}

// Das JavaScript des Bandes rechnet in chinesischer Zeit (UTC+8); die Ortszeit kennt nur
// der Uhr-Sensor. Uhrzeit eines Zeitpunkts = jetzt laut Sensor plus Abstand.
function hhmm(seconds) {
  const nowLocal = clock.hour * 3600 + clock.minute * 60 + clock.second
  const t = (((nowLocal + seconds - Math.floor(Date.now() / 1000)) % 86400) + 86400) % 86400
  return pad(Math.floor(t / 3600)) + ':' + pad(Math.floor(t / 60) % 60)
}

// 'Tag|heute|letzte|nächste|Zeitpunkt' → Objekt (ältere Band-App ohne Zeitpunkt: 0)
function parseState(raw) {
  const parts = String(raw || '').split('|').map(Number)
  if (parts.length < 4 || parts.some(isNaN)) return null
  return { day: parts[0], today: parts[1], last: parts[2], next: parts[3], at: parts[4] || 0 }
}

// Zwei Quellen: die Band-App (systemweiter Zwischenspeicher) und das Handy über den
// Wetter-Kanal von Gadgetbridge (Ortsname 'CC|…', kommt auch bei geschlossener Band-App).
// Es gilt die neuere.
function readShared() {
  let app = null
  let phone = null
  try {
    app = parseState(hmFS.SysProGetChars('ciggie'))
  } catch (e) {}
  try {
    const city = String(weather.getForecastWeather().cityName || '')
    if (city.indexOf('CC|') === 0) phone = parseState(city.slice(3))
  } catch (e) {}
  if (!app) return phone
  if (!phone) return app
  return phone.at > app.at ? phone : app
}

function updateCiggie() {
  const shared = readShared()
  if (!shared) {
    // Band neu gestartet oder Band-App noch nie geöffnet
    pauseText.setProperty(hmUI.prop.TEXT, '–')
    nextText.setProperty(hmUI.prop.TEXT, 'Ciggie-App öffnen')
    todayText.setProperty(hmUI.prop.TEXT, '')
    return
  }
  const day = clock.year * 10000 + clock.month * 100 + clock.day
  const today = shared.day === day ? shared.today : 0
  todayText.setProperty(hmUI.prop.TEXT, 'heute ' + today)

  const now = Math.floor(Date.now() / 1000)
  if (shared.next > now) {
    const minutes = Math.ceil((shared.next - now) / 60)
    pauseText.setProperty(hmUI.prop.TEXT,
      minutes < 60 ? minutes + ' min' : Math.floor(minutes / 60) + ':' + pad(minutes % 60) + ' h')
    nextText.setProperty(hmUI.prop.TEXT, 'ab ' + hhmm(shared.next))
  } else {
    pauseText.setProperty(hmUI.prop.TEXT, 'frei')
    nextText.setProperty(hmUI.prop.TEXT, shared.last ? 'letzte ' + hhmm(shared.last) : '')
  }
}

// Puls der letzten Messung
function heartValue() {
  try {
    return heart && heart.last > 0 ? String(heart.last) : '–'
  } catch (e) {
    return '–'
  }
}

// Stress 1–100 (letzte Messung des Bandes)
function stressValue() {
  try {
    return stress && stress.current > 0 ? String(stress.current) : '–'
  } catch (e) {
    return '–'
  }
}

// Schlaf der letzten Nacht in Stunden:Minuten
function sleepValue() {
  if (!sleep) return '–'
  // kein sleep.updateInfo(): jede Minute aufgerufen, startete das Band 7 beim Tragen neu
  try {
    const minutes = sleep.getTotalTime()
    return minutes > 0 ? Math.floor(minutes / 60) + ':' + pad(minutes % 60) : '–'
  } catch (e) {
    return '–'
  }
}

function update() {
  timeText.setProperty(hmUI.prop.TEXT, pad(clock.hour) + ':' + pad(clock.minute))
  dateText.setProperty(hmUI.prop.TEXT, WEEKDAYS[(clock.week + 6) % 7] + ' ' + pad(clock.day) + '.' + pad(clock.month) + '.')
  infoText.setProperty(hmUI.prop.TEXT, battery.current + ' %   ' + steps.current + ' Schritte')
  healthText.setProperty(hmUI.prop.TEXT, 'Puls ' + heartValue() + '   Stress ' + stressValue())
  sleepText.setProperty(hmUI.prop.TEXT, 'Schlaf ' + sleepValue())
  updateCiggie()
}

function openApp(page, param) {
  try {
    hmApp.startApp({ appid: APP_ID, url: page, param })
  } catch (e) {}
}

// Tipps zählen; TAP_MS nach dem letzten entscheiden (zwei = eine zählen)
function onPanelTap() {
  taps += 1
  if (tapTimer) timer.stopTimer(tapTimer)
  tapTimer = timer.createTimer(TAP_MS, TAP_MS, () => {
    timer.stopTimer(tapTimer)
    tapTimer = null
    if (taps === 2) openApp('page/index', 'count')
    taps = 0
  })
}

function text(props, aod) {
  return hmUI.createWidget(hmUI.widget.TEXT, Object.assign({
    x: 0, w: 194, text: '',
    align_h: hmUI.align.CENTER_H, align_v: hmUI.align.CENTER_V,
    // im Always-on-Display nur das Wichtigste
    show_level: aod ? hmUI.show_level.ONLY_NORMAL | hmUI.show_level.ONAL_AOD : hmUI.show_level.ONLY_NORMAL,
  }, props))
}

WatchFace({
  build() {
    hmUI.createWidget(hmUI.widget.FILL_RECT, {
      x: 0, y: 0, w: 194, h: 368, color: ESPRESSO, show_level: hmUI.show_level.ONLY_NORMAL,
    })

    dateText = text({ y: 16, h: 28, text_size: 22, color: ASCHE })
    timeText = text({ y: 44, h: 76, text_size: 64, color: PAPIER }, true)
    infoText = text({ y: 122, h: 24, text_size: 20, color: ASCHE })
    healthText = text({ y: 146, h: 24, text_size: 20, color: ASCHE })
    sleepText = text({ y: 170, h: 24, text_size: 20, color: ASCHE })

    const panel = hmUI.createWidget(hmUI.widget.FILL_RECT, {
      x: 12, y: 196, w: 170, h: 150, radius: 24, color: KAFFEE, show_level: hmUI.show_level.ONLY_NORMAL,
    })
    pauseText = text({ y: 206, h: 60, text_size: 48, color: FILTER }, true)
    nextText = text({ y: 268, h: 32, text_size: 24, color: PAPIER }, true)
    todayText = text({ y: 302, h: 32, text_size: 22, color: ASCHE })
    // Tipps auf Kasten und Texte (eine unsichtbare Fläche darüber kann Zepp OS 1.0 nicht: alpha wird ignoriert)
    for (const widget of [panel, pauseText, nextText, todayText]) {
      widget.addEventListener(hmUI.event.CLICK_UP, onPanelTap)
    }

    clock = hmSensor.createSensor(hmSensor.id.TIME)
    battery = hmSensor.createSensor(hmSensor.id.BATTERY)
    steps = hmSensor.createSensor(hmSensor.id.STEP)
    try {
      heart = hmSensor.createSensor(hmSensor.id.HEART)
    } catch (e) {}
    try {
      stress = hmSensor.createSensor(hmSensor.id.STRESS)
    } catch (e) {}
    try {
      sleep = hmSensor.createSensor(hmSensor.id.SLEEP)
    } catch (e) {}
    try {
      weather = hmSensor.createSensor(hmSensor.id.WEATHER)
    } catch (e) {}
    // Sensoren nur hier und beim Aufwecken lesen: eigene Ereignis-Listener auf Puls/Stress
    // brachten das Band 7 (Firmware 1.11) zum Absturz
    clock.addEventListener(clock.event.MINUTEEND, update)
    hmUI.createWidget(hmUI.widget.WIDGET_DELEGATE, { resume_call: update })
    update()
  },
})
