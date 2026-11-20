import axios from 'axios'
import type { Choice, Deck, GuestSession, Preferences, Restaurant, Results, Room } from '../types'

export const apiOrigin = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const api = axios.create({ baseURL: apiOrigin, timeout: 25_000, paramsSerializer: { indexes: null } })

export const roomPath = (code: string) => '/api/rooms/' + encodeURIComponent(code)

function auth(token?: string) {
  return token ? { headers: { Authorization: 'Bearer ' + token } } : undefined
}

export async function readRoom(code: string, token?: string) {
  return (await api.get<Room>(roomPath(code), auth(token))).data
}

export async function createRoom(preferences: Preferences, name: string) {
  return (await api.post<GuestSession>('/api/rooms', { ...preferences, display_name: name })).data
}

export async function joinRoom(code: string, name: string) {
  return (await api.post<GuestSession>(roomPath(code) + '/join', { display_name: name })).data
}

export async function roomAction(code: string, token: string, action: string, roundNumber: number, vote?: {
  restaurant_id: string
  vote: Choice
}) {
  return (await api.post<Room>(roomPath(code) + '/' + action, { round_number: roundNumber, ...vote }, auth(token))).data
}

export async function getDeck(code: string, token: string) {
  return (await api.get<Deck>(roomPath(code) + '/restaurants', auth(token))).data
}

export async function getResults(code: string, token: string) {
  return (await api.get<Results>(roomPath(code) + '/results', auth(token))).data
}

function searchParams({ location_name: _location, ...preferences }: Preferences) {
  return preferences
}

export async function getCuisines() {
  return (await api.get<string[]>('/api/restaurants/cuisines')).data
}

export async function nearby(search: Preferences) {
  return (await api.get<Restaurant[]>('/api/restaurants/nearby', { params: searchParams(search) })).data
}

export async function getSelection(search: Preferences, ids: string[]) {
  if (!ids.length) return []
  return (await api.get<Restaurant[]>('/api/restaurants/selection', {
    params: searchParams(search),
    headers: { 'X-Restaurant-Ids': ids.join(',') },
  })).data
}

export function getRoomSocket(code: string) {
  const url = new URL('/ws/rooms/' + encodeURIComponent(code), apiOrigin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(url)
}

export function statusOf(error: unknown) {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

export function messageOf(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (!error.response) return 'FoodMatch couldn’t connect. Check your connection and try again.'
  }
  return 'Something went wrong. Please try again.'
}
