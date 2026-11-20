import { Heart } from 'lucide-react'
import type { Match, Restaurant } from '../types'
import { MapsLink, RestaurantDetails, RestaurantPhoto } from './Restaurant'

export default function ResultCard({ restaurant, match }: { restaurant: Restaurant; match?: Match }) {
  const votes = match ? match.like_count + match.dislike_count : 0
  const percentage = match ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 }).format(match.participant_like_percent) : ''
  return (
    <article className="result-card panel">
      <RestaurantPhoto restaurant={restaurant} />
      <div className="result-copy">
        {match && <p className="match-label"><Heart size={15} /> {match.unanimous ? 'Unanimous match' : 'Partial match'} <span>·</span> Rank {match.rank}</p>}
        <h2>{restaurant.name}</h2>
        <RestaurantDetails restaurant={restaurant} />
        {match && <div className="agreement">
          <strong>{match.like_count} of {match.participant_count} liked this <span>({percentage}%)</span></strong>
          {votes < match.participant_count && <small>{match.approval_percent}% approval among {votes} {votes === 1 ? 'vote' : 'votes'} cast</small>}
        </div>}
        <MapsLink restaurant={restaurant} />
      </div>
    </article>
  )
}
