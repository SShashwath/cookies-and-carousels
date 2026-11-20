import { Heart, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'
import { Loading, Location, Page, Problem } from '../components/Layout'
import ResultCard from '../components/ResultCard'
import SwipeCard from '../components/SwipeCard'
import { getSelection, messageOf } from '../services/api'
import { readSolo, storeSolo } from '../services/storage'
import { useSoloDeck } from '../hooks/useSoloDeck'
import type { Choice } from '../types'

export default function Solo({ results = false }: { results?: boolean }) {
  const navigate = useNavigate()
  const [session, setSession] = useState(readSolo)
  const { deck: restaurants, setDeck } = useSoloDeck()
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!session || restaurants) return
    let current = true
    getSelection(session.search, session.ids).then(items => {
      if (current) setDeck(items)
    }).catch(failure => {
      if (current) setError(messageOf(failure))
    })
    return () => { current = false }
  }, [attempt, restaurants, session, setDeck])

  if (!session) return <Navigate to="/solo" replace />
  const next = restaurants?.find(restaurant => !session.choices[restaurant.id])
  const liked = restaurants?.filter(restaurant => session.choices[restaurant.id] === 'like')
  const done = Object.keys(session.choices).length

  async function vote(choice: Choice) {
    if (!session || !next) return false
    const updated = { ...session, choices: { ...session.choices, [next.id]: choice } }
    try {
      storeSolo(updated)
      setSession(updated)
      if (done + 1 === session.ids.length) navigate('/solo/results')
      return true
    } catch {
      setError('This browser couldn’t save your vote. Check your storage settings and try again.')
      return false
    }
  }

  if (!results && restaurants && !next) return <Navigate to="/solo/results" replace />

  return (
    <Page eyebrow={results ? 'SOLO RESULTS' : 'SOLO SWIPING'} title={results ? 'Your favourites.' : 'What looks good?'} description={<Location name={session.search.location_name} />}>
      {error && <Problem message={error} retry={!restaurants ? () => { setError(''); setAttempt(a => a + 1) } : undefined} />}
      {!restaurants && !error && <Loading label="Loading restaurants" />}
      {!results && next && (
        <>
          <SwipeCard restaurant={next} done={done} total={session.ids.length} onVote={vote} />
          <div className="center"><Link className="btn secondary" to="/solo/results"><Heart size={16} /> View likes</Link></div>
        </>
      )}
      {results && liked && (
        <>
          {liked.length
            ? <div className="result-list">{liked.map(restaurant => <ResultCard key={restaurant.id} restaurant={restaurant} />)}</div>
            : <div className="panel empty"><Heart size={27} /><h2>No favourites yet</h2><p>Restaurants you like will show up here.</p></div>}
          <div className="center action-row">
            {next && <Link className="btn primary" to="/solo/swipe">Keep swiping</Link>}
            <Link className="btn secondary" to="/solo"><RotateCcw size={17} /> New search</Link>
          </div>
        </>
      )}
    </Page>
  )
}
