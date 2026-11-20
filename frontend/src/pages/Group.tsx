import { ArrowRight, Check, Clipboard, Heart, MessageCircle, Play, RotateCcw, Users, WifiOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { Loading, Location, Page, Problem } from '../components/Layout'
import ResultCard from '../components/ResultCard'
import SwipeCard from '../components/SwipeCard'
import useRoom from '../hooks/useRoom'
import { getDeck, getResults, joinRoom, messageOf, roomAction } from '../services/api'
import type { Choice, Deck, Match, Room } from '../types'

type Action = 'start' | 'finish' | 'complete' | 'rounds' | 'leave'
type RunAction = (action: Action) => Promise<boolean>

function JoinView({ room, onJoined }: { room: Room; onJoined: ReturnType<typeof useRoom>['acceptSession'] }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const host = room.participants.find(p => p.is_host)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) {
      setError('Enter your display name to join.')
      return
    }
    setError('')
    setBusy(true)
    try {
      onJoined(await joinRoom(room.room_code, name.trim()))
    } catch (failure) {
      setError(messageOf(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Page eyebrow={'ROOM ' + room.room_code} title="You’re invited." description={<Location name={room.location_name} />}>
      <div className="panel join-panel">
        <div className="join-details"><span className="step-icon"><Users size={22} /></span><div><h2>{host ? host.display_name + '’s group' : 'Group dining'}</h2><p>{room.participants.length} {room.participants.length === 1 ? 'person' : 'people'} in the room</p></div></div>
        {room.status === 'lobby' ? (
          <form onSubmit={submit} className="join-form">
            <label className="field">Display name<input autoComplete="nickname" maxLength={40} placeholder="Your name" required value={name} onChange={e => setName(e.target.value)} /></label>
            {error && <Problem message={error} />}
            <button className="btn primary wide" disabled={busy}>{busy ? 'Joining…' : 'Join Room'} <ArrowRight size={18} /></button>
          </form>
        ) : <Problem message="This round has already started. Reopen this invite when the next lobby opens." />}
      </div>
    </Page>
  )
}

function Roster({ room, onlineIds, trackPresence, showProgress }: {
  room: Room; onlineIds: string[]; trackPresence: boolean; showProgress?: boolean
}) {
  return (
    <div className="panel roster">
      <div className="section-heading"><h2>{showProgress ? 'Group progress' : 'Who’s here'}</h2><span>{room.participants.length} joined</span></div>
      <ul>
        {room.participants.map(participant => {
          const online = onlineIds.includes(participant.id)
          return (
            <li key={participant.id}>
              <span className="avatar">{Array.from(participant.display_name)[0].toUpperCase()}</span>
              <span className="roster-name">{participant.display_name}{room.me?.id === participant.id && <small> (you)</small>}</span>
              {participant.is_host && <span className="host-tag">Host</span>}
              {showProgress
                ? <span className="roster-status">
                  {trackPresence && !online && !participant.completed_swiping && <small>Away ·</small>}
                  {participant.completed_swiping ? <><Check size={15} /> Done</> : participant.vote_count + '/' + room.restaurant_count}
                </span>
                : trackPresence && <span className={'roster-status ' + (online ? 'online' : '')}><span className="status-dot" />{online ? 'Online' : 'Away'}</span>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Lobby({ room, onlineIds, live, run, busy }: {
  room: Room; onlineIds: string[]; live: boolean; run: RunAction; busy: boolean
}) {
  const [copyState, setCopyState] = useState('')
  const invite = new URL('/room/' + room.room_code, window.location.origin).href
  const whatsapp = 'https://wa.me/?text=' + encodeURIComponent('Help us decide where to eat! Join my FoodMatch room: ' + invite)

  async function copy() {
    try {
      await navigator.clipboard.writeText(invite)
      setCopyState('Invite link copied.')
    } catch {
      setCopyState('Select the invite link below to copy it.')
    }
  }

  return (
    <>
      <section className="panel invite-panel">
        <div><p className="eyebrow">ROOM CODE</p><strong className="room-code">{room.room_code}</strong></div>
        <div className="action-row">
          <button className="btn secondary" onClick={() => void copy()}><Clipboard size={17} /> Copy invite link</button>
          <a className="btn whatsapp" href={whatsapp} target="_blank" rel="noreferrer"><MessageCircle size={17} /> WhatsApp</a>
        </div>
        {copyState && <p className="subtle copy-note" role="status">{copyState}</p>}
        {copyState.startsWith('Select') && <input className="invite-input" aria-label="Invite link" readOnly value={invite} onFocus={event => event.target.select()} />}
      </section>
      <Roster room={room} onlineIds={onlineIds} trackPresence={live} />
      {room.me?.is_host
        ? <button className="btn primary wide" disabled={busy} onClick={() => void run('start')}><Play size={18} /> {busy ? 'Starting…' : 'Start swiping'}</button>
        : <p className="center subtle" role="status">Waiting for the host to start the round.</p>}
    </>
  )
}

function GroupSwipe({ room, token, onRoom, refresh, run }: {
  room: Room; token: string; onRoom: (room: Room) => void; refresh: () => Promise<void>; run: RunAction
}) {
  const [data, setData] = useState<Deck | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [saving, setSaving] = useState(false)
  const completionAttempt = useRef(false)
  const code = room.room_code
  const round = room.round_number
  const completed = room.me?.completed_swiping
  const selfCount = room.me?.vote_count
  const count = data?.voted_ids.length

  useEffect(() => {
    if (completed || data && data.voted_ids.length === selfCount) return
    let current = true
    getDeck(code, token).then(deck => {
      if (current && deck.round_number === round) setData(deck)
      else if (current) void refresh()
    }).catch(failure => {
      if (current) setError(messageOf(failure))
    })
    return () => { current = false }
  }, [code, token, round, attempt, completed, count, selfCount, refresh])

  useEffect(() => {
    if (completed || !data || count !== data.restaurants.length || completionAttempt.current) return
    completionAttempt.current = true
    setSaving(true)
    void run('complete').finally(() => setSaving(false))
  }, [completed, count, data, attempt, run])

  const next = data?.restaurants.find(restaurant => !data.voted_ids.includes(restaurant.id))

  async function vote(choice: Choice) {
    if (!next) return false
    setError('')
    try {
      const snapshot = await roomAction(code, token, 'votes', round, { restaurant_id: next.id, vote: choice })
      setData(previous => previous && { ...previous, voted_ids: Array.from(new Set([...previous.voted_ids, next.id])) })
      onRoom(snapshot)
      return true
    } catch (failure) {
      setError(messageOf(failure))
      void refresh()
      return false
    }
  }

  if (completed) return <div className="panel empty"><Check size={30} /><h2>Your votes are in</h2><p>Results appear after everyone finishes or the host closes voting.</p></div>

  return (
    <>
      {error && <Problem message={error} retry={!data ? () => { setError(''); setAttempt(a => a + 1) } : undefined} />}
      {!data && !error && <Loading label="Loading the group’s restaurants" />}
      {next && <SwipeCard restaurant={next} done={data?.voted_ids.length ?? 0} total={room.restaurant_count} onVote={vote} />}
      {data && !next && <div className="panel empty">
        <Check size={28} />
        <h2>{saving ? 'Saving your progress…' : 'You’ve swiped on every restaurant'}</h2>
        {!saving && <button className="btn secondary" onClick={() => { completionAttempt.current = false; setAttempt(a => a + 1) }}>Submit completion</button>}
      </div>}
    </>
  )
}

function GroupResults({ room, token, run, busy }: { room: Room; token: string; run: RunAction; busy: boolean }) {
  const [matches, setMatches] = useState<Match[] | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const code = room.room_code
  const round = room.round_number

  useEffect(() => {
    let current = true
    getResults(code, token).then(results => {
      if (current && results.round_number === round) setMatches(results.matches)
    }).catch(failure => {
      if (current) setError(messageOf(failure))
    })
    return () => { current = false }
  }, [code, token, round, attempt])

  return (
    <>
      {error && <Problem message={error} retry={() => { setError(''); setAttempt(a => a + 1) }} />}
      {!matches && !error && <Loading label="Loading group matches" />}
      {matches && (
        matches.length ? (
          <div className="result-list">{matches.map(match => <ResultCard key={match.restaurant.id} restaurant={match.restaurant} match={match} />)}</div>
        ) : <div className="panel empty"><Heart size={28} /><h2>No matches this round</h2><p>Try a new round to see another shortlist.</p></div>
      )}
      <div className="action-row center">
        {room.me?.is_host
          ? <button className="btn primary" onClick={() => void run('rounds')} disabled={busy}><RotateCcw size={17} /> {busy ? 'Preparing round…' : 'Start another round'}</button>
          : <p className="subtle">The host can start another round.</p>}
      </div>
    </>
  )
}

function GroupRoom({ code }: { code: string }) {
  const { room, token, error, refresh, connection, onlineIds, acceptSession, acceptRoom, leaveRoom } = useRoom(code)
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmation, setConfirmation] = useState<'finish' | 'leave' | null>(null)
  const running = useRef(false)

  async function run(action: Action) {
    if (!room || !token || running.current) return false
    running.current = true
    setBusy(true)
    setActionError('')
    try {
      const snapshot = await roomAction(code, token, action, room.round_number)
      if (action === 'leave') leaveRoom(snapshot)
      else acceptRoom(snapshot)
      setConfirmation(null)
      return true
    } catch (failure) {
      setActionError(messageOf(failure))
      void refresh()
      return false
    } finally {
      running.current = false
      setBusy(false)
    }
  }

  if (!room) return <Page title={error ? 'Room unavailable.' : 'Opening your room.'}>
    {error ? <><Problem message={error} retry={() => void refresh()} /><Link className="btn secondary" to="/create">Create Group</Link></> : <Loading label="Loading room" />}
  </Page>
  if (!room.me || !token) return <JoinView room={room} onJoined={acceptSession} />

  const titles = { lobby: 'Invite your group.', swiping: 'What looks good?', finished: 'Group matches.' }
  return (
    <Page eyebrow={'ROOM ' + code + ' · ROUND ' + room.round_number} title={titles[room.status]} description={<Location name={room.location_name} />}>
      {connection === 'offline' && <div className="connection-note" role="status"><WifiOff size={16} /> Reconnecting to live updates…</div>}
      {(error || actionError) && <Problem message={actionError || error} />}
      {room.status === 'lobby' && <Lobby room={room} onlineIds={onlineIds} live={connection === 'live'} run={run} busy={busy} />}
      {room.status === 'swiping' && <>
        <GroupSwipe key={room.round_number} room={room} token={token} onRoom={acceptRoom} refresh={refresh} run={run} />
        <Roster room={room} onlineIds={onlineIds} trackPresence={connection === 'live'} showProgress />
      </>}
      {room.status === 'finished' && <GroupResults key={room.round_number} room={room} token={token} run={run} busy={busy} />}
      {room.status !== 'finished' && (room.status === 'swiping' || !room.me.is_host) && (
        confirmation
          ? <div className="panel confirm">
            <p>{confirmation === 'finish' ? 'Show results using the votes received so far?' : 'Leave this room? Your votes won’t count toward this round.'}</p>
            <div className="action-row">
              <button className="btn secondary" disabled={busy} onClick={() => setConfirmation(null)}>Keep room open</button>
              <button className="btn primary" disabled={busy} onClick={() => void run(confirmation)}>{confirmation === 'finish' ? 'Finish round' : 'Leave room'}</button>
            </div>
          </div>
          : <div className="center"><button className="text-link" disabled={busy} onClick={() => setConfirmation(room.me?.is_host ? 'finish' : 'leave')}>{room.me.is_host ? 'Finish round early' : 'Leave room'}</button></div>
      )}
    </Page>
  )
}

export default function Group() {
  const code = (useParams().code ?? '').toUpperCase()
  return <GroupRoom key={code} code={code} />
}
