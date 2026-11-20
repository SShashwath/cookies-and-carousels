import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { Restaurant } from '../types'

const DeckContext = createContext<{ deck: Restaurant[] | null; setDeck: (deck: Restaurant[]) => void } | null>(null)

export function SoloDeckProvider({ children }: { children: ReactNode }) {
  const [deck, setDeck] = useState<Restaurant[] | null>(null)
  return <DeckContext.Provider value={{ deck, setDeck }}>{children}</DeckContext.Provider>
}

export function useSoloDeck() {
  const context = useContext(DeckContext)
  if (!context) throw new Error('SoloDeckProvider is required.')
  return context
}
