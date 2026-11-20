import type { SoloSession } from '../types'

const sessionKey = (code: string) => 'foodmatch:room:' + code
const soloKey = 'foodmatch:solo'

export function readToken(code: string) {
  return localStorage.getItem(sessionKey(code)) ?? undefined
}

export function storeToken(code: string, token: string) {
  localStorage.setItem(sessionKey(code), token)
}

export function clearToken(code: string) {
  localStorage.removeItem(sessionKey(code))
}

export function readSolo(): SoloSession | null {
  try {
    const value = JSON.parse(localStorage.getItem(soloKey) ?? 'null')
    return value?.search && Array.isArray(value.ids) && value.choices ? value : null
  } catch {
    return null
  }
}

export function storeSolo(session: SoloSession) {
  localStorage.setItem(soloKey, JSON.stringify(session))
}
