import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import SwipeCard from './components/SwipeCard'
import ResultCard from './components/ResultCard'
import { createRoom, joinRoom, readRoom } from './services/api'
import { readToken } from './services/storage'
import type { Restaurant, Room } from './types'

vi.mock('./services/api', async importOriginal => ({
  ...await importOriginal<typeof import('./services/api')>(),
  createRoom: vi.fn(),
  getCuisines: vi.fn(async () => ['South Indian', 'Italian']),
  joinRoom: vi.fn(),
  readRoom: vi.fn(),
  getRoomSocket: vi.fn(() => ({ close: vi.fn() })),
}))

const room: Room = {
  room_code: 'AB12CD', status: 'lobby', location_name: 'Bengaluru', preferences: null, round_number: 1,
  expires_at: '2027-01-01T00:00:00Z', restaurant_count: 10,
  participants: [{ id: 'one', display_name: 'Anika', completed_swiping: false, is_host: true, vote_count: 0 }],
  me: null,
}

const restaurant: Restaurant = {
  id: 'one', source: 'mock', name: 'Banana Leaf Kitchen', address: 'Sample venue', cuisines: ['South Indian'],
  rating: 4.7, price_level: null, min_price_per_person: 350, max_price_per_person: 350, distance_km: 1.2,
  photo_url: null, photo_attributions: [], attributions: [],
  maps_url: 'https://www.google.com/maps/search/?api=1&query=12.9,77.5', available: true, vegetarian_only: true,
}

function app(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('FoodMatch flows', () => {
  it('sends configured room preferences and retains the guest token', async () => {
    const hosting = { ...room, me: room.participants[0] }
    vi.mocked(createRoom).mockResolvedValueOnce({ token: 'host-token', room: hosting })
    vi.mocked(readRoom).mockResolvedValue(hosting)
    const user = userEvent.setup()
    app('/create')
    await user.type(screen.getByLabelText('Your name'), 'Anika')
    await user.selectOptions(screen.getByLabelText('Search location'), 'Pune')
    await user.click(screen.getByRole('button', { name: 'South Indian' }))
    await user.click(screen.getByRole('checkbox', { name: /vegetarian restaurants/i }))
    await user.click(screen.getByRole('button', { name: 'Create Room' }))
    expect(createRoom).toHaveBeenCalledWith(expect.objectContaining({
      location_name: 'Pune', latitude: 18.5204, cuisine_preferences: ['South Indian'], vegetarian_only: true,
    }), 'Anika')
    expect(await screen.findByRole('heading', { name: 'Invite your group.' })).toBeVisible()
    expect(readToken('AB12CD')).toBe('host-token')
    expect(screen.getByRole('link', { name: 'WhatsApp' })).toHaveAttribute('href', expect.stringContaining('https://wa.me/?text='))
  })

  it('shows a loading skeleton and lets a guest join from an invite', async () => {
    let resolveRoom!: (value: Room) => void
    vi.mocked(readRoom).mockReturnValueOnce(new Promise(resolve => { resolveRoom = resolve }))
    const guest = { id: 'two', display_name: 'Veda', is_host: false, completed_swiping: false, vote_count: 0 }
    const joined = { ...room, participants: [...room.participants, guest], me: guest }
    vi.mocked(readRoom).mockResolvedValue(joined)
    vi.mocked(joinRoom).mockResolvedValueOnce({ token: 'guest-token', room: joined })
    const user = userEvent.setup()
    app('/room/AB12CD')
    expect(screen.getByRole('status', { name: 'Loading room' })).toBeInTheDocument()
    resolveRoom(room)
    expect(await screen.findByRole('heading', { name: 'You’re invited.' })).toBeVisible()
    await user.type(screen.getByLabelText('Display name'), 'Veda')
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    await waitFor(() => expect(joinRoom).toHaveBeenCalledWith('AB12CD', 'Veda'))
    expect(await screen.findByText('Waiting for the host to start the round.')).toBeVisible()
    expect(readToken('AB12CD')).toBe('guest-token')
  })

  it('submits swipe button and keyboard actions and prevents extra submissions while saving', async () => {
    let resolveVote!: (value: boolean) => void
    const onVote = vi.fn()
      .mockReturnValueOnce(new Promise(resolve => { resolveVote = resolve }))
      .mockResolvedValue(true)
    const user = userEvent.setup()
    render(<SwipeCard restaurant={restaurant} done={1} total={3} onVote={onVote} />)
    expect(screen.getByRole('progressbar', { name: 'Swipe progress' })).toHaveAttribute('value', '1')
    await user.click(screen.getByRole('button', { name: 'Like' }))
    expect(onVote).toHaveBeenCalledWith('like')
    const pass = screen.getByRole('button', { name: 'Pass' })
    expect(pass).toBeDisabled()
    await user.click(pass)
    expect(onVote).toHaveBeenCalledTimes(1)
    resolveVote(true)
    await waitFor(() => expect(pass).toBeEnabled())
    pass.focus()
    await user.keyboard('{ArrowLeft}')
    expect(onVote).toHaveBeenLastCalledWith('dislike')
  })

  it('renders group agreement, the cast-ballot percentage, and a Maps link', () => {
    render(<ResultCard restaurant={restaurant} match={{
      rank: 1, restaurant, approval_percent: 100, participant_like_percent: 50, like_count: 2,
      dislike_count: 0, participant_count: 4, unanimous: false,
    }} />)
    expect(screen.getByRole('heading', { name: restaurant.name })).toBeVisible()
    expect(screen.getByText(/Partial match/)).toBeVisible()
    expect(screen.getByText('2 of 4 liked this', { exact: false })).toHaveTextContent('(50%)')
    expect(screen.getByText('100% approval among 2 votes cast')).toBeVisible()
    expect(screen.getByRole('link', { name: 'View sample location' })).toHaveAttribute('href', restaurant.maps_url)
  })
})
