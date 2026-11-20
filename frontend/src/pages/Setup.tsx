import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Page, Problem } from '../components/Layout'
import PreferenceForm from '../components/PreferenceForm'
import { createRoom, messageOf, nearby } from '../services/api'
import { readSolo, storeSolo, storeToken } from '../services/storage'
import { useSoloDeck } from '../hooks/useSoloDeck'
import type { Preferences } from '../types'

export default function Setup({ group = false }: { group?: boolean }) {
  const navigate = useNavigate()
  const { setDeck } = useSoloDeck()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const previous = group ? null : readSolo()

  async function submit(preferences: Preferences, name: string) {
    setBusy(true)
    setError('')
    try {
      if (group) {
        const { token, room } = await createRoom(preferences, name)
        storeToken(room.room_code, token)
        navigate('/room/' + room.room_code)
      } else {
        const restaurants = await nearby(preferences)
        if (!restaurants.length) {
          setError('No restaurants match these filters. Try a wider radius or more cuisines.')
          return
        }
        storeSolo({ search: preferences, ids: restaurants.map(r => r.id), choices: {} })
        setDeck(restaurants)
        navigate('/solo/swipe')
      }
    } catch (failure) {
      setError(messageOf(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Page eyebrow={group ? 'GROUP DINING' : 'SOLO DISCOVERY'} title={group ? 'Set the table.' : 'Find your next bite.'} description={group ? 'Pick a location and preferences for the whole group.' : 'Choose an area and what you’re in the mood for.'}>
      {error && <Problem message={error} />}
      {previous && <div className="action-row resume-actions">
        {previous.ids.some(id => !previous.choices[id]) && <Link className="btn secondary" to="/solo/swipe">Resume swiping</Link>}
        <Link className="btn secondary" to="/solo/results">View likes</Link>
      </div>}
      <PreferenceForm key={String(group)} group={group} busy={busy} onSubmit={submit} />
    </Page>
  )
}
