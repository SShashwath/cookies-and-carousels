export type Choice = 'like' | 'dislike'

export interface Search {
  latitude: number
  longitude: number
  radius_km: number
  min_budget: number
  max_budget: number
  cuisine_preferences: string[]
  vegetarian_only: boolean
}

export interface Preferences extends Search {
  location_name: string
}

export interface Participant {
  id: string
  display_name: string
  is_host: boolean
  completed_swiping: boolean
  vote_count: number
}

export interface Room {
  room_code: string
  status: 'lobby' | 'swiping' | 'finished'
  location_name: string
  preferences: Search | null
  round_number: number
  expires_at: string
  restaurant_count: number
  participants: Participant[]
  me: Participant | null
}

export interface Attribution {
  name: string
  uri: string | null
}

export interface Restaurant {
  id: string
  source: 'mock' | 'google'
  name: string
  address: string | null
  cuisines: string[]
  rating: number | null
  price_level: string | null
  min_price_per_person: number | null
  max_price_per_person: number | null
  distance_km: number | null
  photo_url: string | null
  photo_attributions: Attribution[]
  attributions: Attribution[]
  maps_url: string | null
  vegetarian_only: boolean
  available: boolean
}

export interface Deck {
  round_number: number
  restaurants: Restaurant[]
  voted_ids: string[]
}

export interface Match {
  rank: number
  restaurant: Restaurant
  approval_percent: number
  participant_like_percent: number
  like_count: number
  dislike_count: number
  participant_count: number
  unanimous: boolean
}

export interface Results {
  round_number: number
  matches: Match[]
}

export interface GuestSession {
  token: string
  room: Room
}

export interface SoloSession {
  search: Preferences
  ids: string[]
  choices: Record<string, Choice>
}
