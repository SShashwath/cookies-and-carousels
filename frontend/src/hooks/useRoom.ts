import { useCallback, useEffect, useRef, useState } from 'react'
import { getRoomSocket, messageOf, readRoom, statusOf } from '../services/api'
import { clearToken, readToken, storeToken } from '../services/storage'
import type { GuestSession, Room } from '../types'

export default function useRoom(code: string) {
  const [token, setToken] = useState(() => readToken(code))
  const [room, setRoom] = useState<Room | null>(null)
  const [error, setError] = useState('')
  const [connection, setConnection] = useState<'connecting' | 'live' | 'offline'>('connecting')
  const [onlineIds, setOnlineIds] = useState<string[]>([])
  const requestId = useRef(0)

  const refresh = useCallback(async () => {
    const request = ++requestId.current
    try {
      const snapshot = await readRoom(code, token)
      if (request !== requestId.current) return
      setRoom(snapshot)
      setError('')
    } catch (failure) {
      if (request !== requestId.current) return
      if (token && statusOf(failure) === 401) {
        clearToken(code)
        setToken(undefined)
      }
      if ([401, 404, 410, 422].includes(statusOf(failure) ?? 0)) setRoom(null)
      setError(messageOf(failure))
    }
  }, [code, token])

  useEffect(() => {
    void refresh()
    return () => { requestId.current++ }
  }, [refresh])

  const hasRoom = room !== null

  useEffect(() => {
    if (!token || !hasRoom) return
    const timer = window.setInterval(() => void refresh(), connection === 'live' ? 30000 : 3500)
    const onFocus = () => { void refresh() }
    window.addEventListener('focus', onFocus)
    return () => { window.clearInterval(timer); window.removeEventListener('focus', onFocus) }
  }, [token, hasRoom, connection, refresh])

  const authorized = Boolean(room?.me)

  useEffect(() => {
    if (!token || !authorized) return
    let disposed = false
    let socket: WebSocket | undefined
    let reconnect: number | undefined
    let queuedRefresh: number | undefined
    let failures = 0

    function scheduleRefresh() {
      window.clearTimeout(queuedRefresh)
      queuedRefresh = window.setTimeout(() => void refresh(), 100)
    }

    function connect() {
      if (disposed) return
      socket = getRoomSocket(code)
      socket.onopen = () => {
        socket?.send(JSON.stringify({ token }))
        scheduleRefresh()
      }
      socket.onmessage = ({ data }) => {
        try {
          const message = JSON.parse(data)
          failures = 0
          setConnection('live')
          if (Array.isArray(message.online_ids)) setOnlineIds(message.online_ids)
          if (message.event !== 'presence_updated') scheduleRefresh()
        } catch {
          scheduleRefresh()
        }
      }
      socket.onerror = () => socket?.close()
      socket.onclose = () => {
        if (disposed) return
        setConnection('offline')
        setOnlineIds([])
        scheduleRefresh()
        reconnect = window.setTimeout(connect, Math.min(1000 * 2 ** failures++, 12000))
      }
    }

    connect()
    return () => {
      disposed = true
      window.clearTimeout(reconnect)
      window.clearTimeout(queuedRefresh)
      socket?.close()
    }
  }, [authorized, code, refresh, token])

  function acceptSession(session: GuestSession) {
    requestId.current++
    storeToken(code, session.token)
    setToken(session.token)
    setRoom(session.room)
    setError('')
    setConnection('connecting')
  }

  function acceptRoom(snapshot: Room) {
    requestId.current++
    setRoom(snapshot)
    void refresh()
  }

  function leaveRoom(snapshot: Room) {
    requestId.current++
    clearToken(code)
    setToken(undefined)
    setRoom(snapshot)
  }

  return { room, token, error, refresh, connection, onlineIds, acceptSession, acceptRoom, leaveRoom }
}
