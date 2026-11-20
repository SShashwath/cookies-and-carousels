import { ArrowUpRight, Leaf, Wallet, MapPin, Star, Utensils } from 'lucide-react'
import { useState } from 'react'
import { apiOrigin } from '../services/api'
import type { Attribution, Restaurant } from '../types'

function AttributionList({ items }: { items: Attribution[] }) {
  return <>{items.map((item, index) => item.uri
    ? <a key={index} href={item.uri} target="_blank" rel="noreferrer">{item.name}</a>
    : <span key={index}>{item.name}</span>)}</>
}

export function RestaurantPhoto({ restaurant }: { restaurant: Restaurant }) {
  const [failedPhoto, setFailedPhoto] = useState<string | null>(null)
  const photo = restaurant.photo_url
  const available = photo && failedPhoto !== photo
  return (
    <div className="restaurant-photo">
      {available
        ? <img src={photo.startsWith('/api/') ? apiOrigin + photo : photo} alt="" draggable={false} onError={() => setFailedPhoto(photo)} />
        : <div className="photo-fallback"><Utensils size={36} /><span>Photo unavailable</span></div>}
      {available && restaurant.photo_attributions.length > 0 && (
        <div className="photo-credit"><AttributionList items={restaurant.photo_attributions} /></div>
      )}
      {restaurant.vegetarian_only && <span className="veg-badge"><Leaf size={14} /> Vegetarian</span>}
    </div>
  )
}

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

function priceText(restaurant: Restaurant) {
  const { min_price_per_person: min, max_price_per_person: max, price_level: level, source } = restaurant
  if (source === 'mock' && min !== null && max !== null) {
    const amount = min === max ? inr.format(2 * min) : inr.format(2 * min) + '–' + inr.format(2 * max)
    return amount + ' for two'
  }
  if (min !== null && max !== null) return inr.format(min) + '–' + inr.format(max)
  if (min !== null) return 'From ' + inr.format(min)
  if (max !== null) return 'Up to ' + inr.format(max)
  return level ?? 'Price unavailable'
}

export function RestaurantDetails({ restaurant }: { restaurant: Restaurant }) {
  if (!restaurant.available) return <p className="subtle">This venue’s details are currently unavailable.</p>
  return (
    <>
      <p className="food-cuisines">{restaurant.cuisines.length ? restaurant.cuisines.join(' · ') : 'Cuisine unavailable'}</p>
      <div className="facts">
        <span><Star size={16} className={restaurant.rating === null ? '' : 'rating-star'} />{restaurant.rating === null ? 'Rating unavailable' : restaurant.rating.toFixed(1)}</span>
        <span><MapPin size={16} />{restaurant.distance_km === null ? 'Distance unavailable' : restaurant.distance_km.toFixed(1) + ' km'}</span>
        <span><Wallet size={16} />{priceText(restaurant)}</span>
      </div>
      {restaurant.address && <p className="address">{restaurant.address}</p>}
      {restaurant.source === 'google' && <div className="provider-credit"><span translate="no">Google Maps</span><AttributionList items={restaurant.attributions} /></div>}
      {restaurant.source === 'mock' && <p className="provider-credit">Demo venue · illustrative photo</p>}
    </>
  )
}

export function MapsLink({ restaurant }: { restaurant: Restaurant }) {
  return restaurant.maps_url && <a className="btn secondary maps-link" href={restaurant.maps_url} target="_blank" rel="noreferrer">
    <MapPin size={16} /> {restaurant.source === 'mock' ? 'View sample location' : 'Open in Google Maps'} <ArrowUpRight size={16} />
  </a>
}
