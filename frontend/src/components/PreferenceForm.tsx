import { ArrowRight, Crosshair, Leaf, MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { getCuisines } from '../services/api'
import type { Preferences } from '../types'
import { Problem } from './Layout'

const CITIES = {
  Bengaluru: [12.9716, 77.5946],
  Mumbai: [19.076, 72.8777],
  Delhi: [28.6139, 77.209],
  Hyderabad: [17.385, 78.4867],
  Chennai: [13.0827, 80.2707],
  Pune: [18.5204, 73.8567],
  Kolkata: [22.5726, 88.3639],
  Ahmedabad: [23.0225, 72.5714],
} as const

const defaultCuisines = ['Indian', 'Chinese', 'Italian', 'Asian', 'Cafe', 'Pizza']

export default function PreferenceForm({ group = false, busy, onSubmit }: {
  group?: boolean; busy: boolean; onSubmit: (preferences: Preferences, name: string) => void
}) {
  const [location, setLocation] = useState('Bengaluru')
  const [coordinates, setCoordinates] = useState({ lat: '', lng: '' })
  const [geolocating, setGeolocating] = useState(false)
  const [error, setError] = useState('')
  const [radius, setRadius] = useState(5)
  const [minBudget, setMinBudget] = useState(0)
  const [maxBudget, setMaxBudget] = useState(1000)
  const [selected, setSelected] = useState<string[]>([])
  const [cuisines, setCuisines] = useState(defaultCuisines)
  useEffect(() => {
    let current = true
    getCuisines().then(options => {
      if (current) setCuisines(options)
    }).catch(() => { /* The common cuisines remain available if the list can't load. */ })
    return () => { current = false }
  }, [])
  const [vegetarian, setVegetarian] = useState(false)
  const [name, setName] = useState('')

  function locate() {
    if (!navigator.geolocation) {
      setError('Location access is unavailable here. Choose a city or enter coordinates.')
      return
    }
    setGeolocating(true)
    setError('')
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      setCoordinates({ lat: String(coords.latitude), lng: String(coords.longitude) })
      setLocation('Current location')
      setGeolocating(false)
    }, () => {
      setError('We couldn’t access your location. Choose a city or enter coordinates.')
      setGeolocating(false)
    }, { timeout: 9000, maximumAge: 30000 })
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (minBudget > maxBudget) {
      setError('The minimum budget must be lower than or equal to the maximum.')
      return
    }
    const point = CITIES[location as keyof typeof CITIES]
    const [latitude, longitude] = point ?? [Number(coordinates.lat), Number(coordinates.lng)]
    if (!point && (!coordinates.lat || !coordinates.lng || !Number.isFinite(latitude) || !Number.isFinite(longitude)
      || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)) {
      setError('Enter valid latitude and longitude values.')
      return
    }
    if (group && !name.trim()) {
      setError('Enter a display name to create your group.')
      return
    }
    setError('')
    onSubmit({
      location_name: location, latitude, longitude, radius_km: radius,
      min_budget: minBudget, max_budget: maxBudget, cuisine_preferences: selected, vegetarian_only: vegetarian,
    }, name.trim())
  }

  return (
    <form className="panel preference-form" onSubmit={submit}>
      <fieldset disabled={busy}>
        {group && <label className="field">Your name<input value={name} onChange={e => setName(e.target.value)} required maxLength={40} placeholder="e.g. Anika" autoComplete="nickname" /></label>}
        <div className="field">
          <label htmlFor="location">Search location</label>
          <div className="location-field">
            <div className="select-with-icon"><MapPin size={17} /><select id="location" value={location} onChange={e => { setLocation(e.target.value); setError('') }}>
              {Object.keys(CITIES).map(city => <option key={city}>{city}</option>)}
              {location === 'Current location' && <option>Current location</option>}
              <option>Custom coordinates</option>
            </select></div>
            <button type="button" className="btn secondary locate" onClick={locate} disabled={geolocating}><Crosshair size={17} /> {geolocating ? 'Locating…' : 'Use my location'}</button>
          </div>
          {location === 'Custom coordinates' && <div className="field-grid coordinate-fields">
            <label className="field">Latitude<input type="number" min={-90} max={90} step="any" required value={coordinates.lat} onChange={e => setCoordinates({ ...coordinates, lat: e.target.value })} /></label>
            <label className="field">Longitude<input type="number" min={-180} max={180} step="any" required value={coordinates.lng} onChange={e => setCoordinates({ ...coordinates, lng: e.target.value })} /></label>
          </div>}
        </div>
        <div className="field-grid">
          <label className="field">Min per person (₹)<input type="number" min={0} max={10000} required value={minBudget} onChange={e => setMinBudget(Number(e.target.value))} /></label>
          <label className="field">Max per person (₹)<input type="number" min={100} max={20000} required value={maxBudget} onChange={e => setMaxBudget(Number(e.target.value))} /></label>
        </div>
        <label className="field">Search radius<select value={radius} onChange={e => setRadius(Number(e.target.value))}>
          {[0.5, 1, 2, 3, 5, 10, 20, 30].map(km => <option key={km} value={km}>{km} km</option>)}
        </select></label>
        <div className="field">
          <span>Cuisine <small className="muted-details">Optional</small></span>
          <div className="chips" role="group" aria-label="Cuisine preferences">
            {cuisines.map(cuisine => <button
              key={cuisine} type="button" className="chip" aria-pressed={selected.includes(cuisine)}
              onClick={() => setSelected(current => current.includes(cuisine) ? current.filter(item => item !== cuisine) : [...current, cuisine])}
            >{cuisine}</button>)}
          </div>
        </div>
        <label className="diet">
          <Leaf size={20} aria-hidden="true" />
          <span><strong>Vegetarian restaurants only</strong><small>Only include venues listed as vegetarian or vegan.</small></span>
          <input type="checkbox" checked={vegetarian} onChange={e => setVegetarian(e.target.checked)} />
        </label>
      </fieldset>
      {error && <Problem message={error} />}
      <button className="btn primary wide" disabled={busy || geolocating}>{busy ? (group ? 'Creating room…' : 'Finding restaurants…') : (group ? 'Create Room' : 'Find Food')} <ArrowRight size={19} /></button>
    </form>
  )
}
