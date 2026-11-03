// Zustand der Band-App, dauerhaft in einer Datei (übersteht Neustart des Bandes).
// pending: Einträge, die das Handy noch nicht bestätigt hat – erst nach Quittung gelöscht.

const FILE = 'ciggie.json'

let clock = null

export function now() {
  return Math.floor(Date.now() / 1000)
}

// Das JavaScript des Bandes rechnet in chinesischer Zeit (UTC+8), nicht in der eingestellten.
// Die richtige Ortszeit kennt nur der Uhr-Sensor; daraus die Verschiebung in Sekunden.
function offset() {
  if (!clock) clock = hmSensor.createSensor(hmSensor.id.TIME)
  const local = Date.UTC(clock.year, clock.month - 1, clock.day, clock.hour, clock.minute, clock.second) / 1000
  return Math.round((local - now()) / 60) * 60
}

// Ortszeit als Date, nur mit den getUTC…-Methoden lesen
export function localDate(seconds) {
  return new Date((seconds + offset()) * 1000)
}

function dayOf(seconds) {
  const d = localDate(seconds)
  return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate()
}

export function load() {
  // next: nächste erlaubt (Unix-Sekunden, 0 = keine Pause), gap: zuletzt bekannte Pausenlänge
  // mpending: noch nicht quittierte Messungen, session: laufende Vorher-nachher-Messung
  const empty = { pending: [], mpending: [], session: null, today: 0, day: dayOf(now()), last: 0, next: 0, gap: 0 }
  const [stat, err] = hmFS.stat(FILE)
  if (err !== 0 || !stat.size) return empty

  const buf = new ArrayBuffer(stat.size)
  const fd = hmFS.open(FILE, hmFS.O_RDONLY)
  hmFS.read(fd, buf, 0, stat.size)
  hmFS.close(fd)

  let text = ''
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < bytes.length; i++) text += String.fromCharCode(bytes[i])
  try {
    const state = JSON.parse(text)
    return rollDay(Object.assign(empty, state))
  } catch (e) {
    return empty
  }
}

export function save(state) {
  const text = JSON.stringify(state)
  const bytes = new Uint8Array(text.length)
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i) & 0x7f
  const fd = hmFS.open(FILE, hmFS.O_WRONLY | hmFS.O_CREAT | hmFS.O_TRUNC)
  hmFS.write(fd, bytes.buffer, 0, bytes.length)
  hmFS.close(fd)
}

// Neuer Tag: Tageszähler zurücksetzen
export function rollDay(state) {
  const today = dayOf(now())
  if (state.day !== today) {
    state.day = today
    state.today = 0
  }
  return state
}

// Eindeutige Eintrags-ID wie im Abgleich v2: zufällige UUID (Version 4)
export function newId() {
  const hex = '0123456789abcdef'
  let id = ''
  for (let i = 0; i < 36; i++) {
    if (i === 8 || i === 13 || i === 18 || i === 23) id += '-'
    else if (i === 14) id += '4'
    else if (i === 19) id += hex[8 + Math.floor(Math.random() * 4)]
    else id += hex[Math.floor(Math.random() * 16)]
  }
  return id
}
