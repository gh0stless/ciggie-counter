// Verbindung Band <-> Handy (Gadgetbridge mit PebbleKit-Fassade).
//
// Rahmen: 16 Byte Kopf, Little Endian – flag u8 (1 = App), version u8 (1), type u16,
// port1 u16 (Band), port2 u16 (Handy), appId u32, extra u32 – danach die Nutzdaten.
// Ablauf: Band schickt SHAKE mit port2 = 0, das Handy antwortet mit seinem Port; danach
// gelten nur noch DATA-Nachrichten mit genau diesem Port.
// Nutzdaten: PebbleKit-Dictionary als JSON, z. B. [{"key":0,"type":"string","length":5,"value":"entry"}].

const FLAG_APP = 1
const VERSION = 1
const TYPE_SHAKE = 1
const TYPE_CLOSE = 2
const TYPE_DATA = 4
const DEVICE_PORT = 20
const HEADER = 16

let appId = 0
let sidePort = 0
let ready = false
let handlers = { onReady: null, onData: null }

// JSON ist bei uns reines ASCII (IDs, Zahlen, feste Wörter)
function toBytes(str) {
  const out = new Uint8Array(str.length)
  for (let i = 0; i < str.length; i++) out[i] = str.charCodeAt(i) & 0x7f
  return out
}

function fromBytes(bytes) {
  let s = ''
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i])
  return s
}

function send(type, payload) {
  const buf = new ArrayBuffer(HEADER + payload.length)
  const dv = new DataView(buf)
  dv.setUint8(0, FLAG_APP)
  dv.setUint8(1, VERSION)
  dv.setUint16(2, type, true)
  dv.setUint16(4, DEVICE_PORT, true)
  dv.setUint16(6, sidePort, true)
  dv.setUint32(8, appId, true)
  dv.setUint32(12, 0, true)
  new Uint8Array(buf, HEADER).set(payload)
  hmBle.send(buf, buf.byteLength)
}

function receive(data) {
  if (!data || data.byteLength < HEADER) return
  const dv = new DataView(data)
  if (dv.getUint8(0) !== FLAG_APP) return
  const type = dv.getUint16(2, true)
  const port2 = dv.getUint16(6, true)

  if (type === TYPE_SHAKE) {
    sidePort = port2
    ready = true
    handlers.onReady && handlers.onReady()
    return
  }
  if (type === TYPE_DATA && ready && port2 === sidePort) {
    let dict
    try {
      dict = JSON.parse(fromBytes(new Uint8Array(data, HEADER)))
    } catch (e) {
      return
    }
    const values = {}
    for (const item of dict) values[item.key] = item.value
    handlers.onData && handlers.onData(values)
  }
}

export function connect(id, onReady, onData) {
  appId = id
  handlers = { onReady, onData }
  hmBle.createConnect((index, data, size) => receive(data))
  // SHAKE-Nutzdaten wie beim offiziellen SDK: das untere Byte der App-ID
  send(TYPE_SHAKE, new Uint8Array([appId & 0xff]))
}

export function disconnect() {
  if (ready) send(TYPE_CLOSE, new Uint8Array([appId & 0xff]))
  ready = false
  sidePort = 0
  hmBle.disConnect()
}

export function isReady() {
  return ready
}

// values: { key: Zahl | Text } – Zahlen gehen als "int", Text als "string"
export function sendDict(values) {
  if (!ready) return false
  const dict = []
  for (const key in values) {
    const value = values[key]
    if (typeof value === 'number') {
      dict.push({ key: Number(key), type: 'int', length: 4, value })
    } else {
      const text = String(value)
      dict.push({ key: Number(key), type: 'string', length: text.length + 1, value: text })
    }
  }
  send(TYPE_DATA, toBytes(JSON.stringify(dict)))
  return true
}
