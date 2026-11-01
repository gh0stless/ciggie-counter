// Zustand der Band-App, dauerhaft in einer Datei (übersteht Neustart des Bandes).
// pending: Einträge, die das Handy noch nicht bestätigt hat – erst nach Quittung gelöscht.

const FILE = 'ciggie.json'

function dayOf(seconds) {
  const d = new Date(seconds * 1000)
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate()
}

export function now() {
  return Math.floor(Date.now() / 1000)
}

export function load() {
  const empty = { pending: [], today: 0, day: dayOf(now()), last: 0 }
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
