import { Heart, X } from 'lucide-react'
import { AnimatePresence, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react'
import type { PanInfo } from 'motion/react'
import { forwardRef, useRef, useState } from 'react'
import type { Choice, Restaurant } from '../types'
import { RestaurantDetails, RestaurantPhoto } from './Restaurant'

interface Props {
  restaurant: Restaurant
  done: number
  total: number
  onVote: (choice: Choice) => Promise<boolean>
  locked?: boolean
}

const DraggableCard = forwardRef<HTMLElement, {
  restaurant: Restaurant; locked: boolean; onDragEnd: (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => void
}>(function DraggableCard({ restaurant, locked, onDragEnd }, ref) {
  const x = useMotionValue(0)
  const rotation = useTransform(x, [-210, 210], [-12, 12])
  const likeOpacity = useTransform(x, [15, 95], [0, 1])
  const passOpacity = useTransform(x, [-95, -15], [1, 0])
  const reduce = useReducedMotion()

  return (
    <motion.article
      ref={ref} className="restaurant-card panel"
      drag={!locked && 'x'} dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.55} dragMomentum={false} onDragEnd={onDragEnd}
      style={{ x, rotate: reduce ? 0 : rotation, touchAction: 'pan-y' }}
      initial={{ opacity: 0, scale: reduce ? 1 : 0.98 }} animate={{ opacity: 1, scale: 1 }}
      variants={{ gone: (choice: Choice) => ({ opacity: 0, x: reduce ? 0 : (choice === 'like' ? 260 : -260) }) }}
      exit="gone" transition={{ duration: reduce ? 0 : 0.22 }}
    >
      <RestaurantPhoto restaurant={restaurant} />
      <motion.span className="swipe-stamp stamp-like" aria-hidden="true" style={{ opacity: restaurant.available ? likeOpacity : 0 }}>LIKE</motion.span>
      <motion.span className="swipe-stamp stamp-pass" aria-hidden="true" style={{ opacity: passOpacity }}>PASS</motion.span>
      <div className="restaurant-copy"><h2>{restaurant.name}</h2><RestaurantDetails restaurant={restaurant} /></div>
    </motion.article>
  )
})

export default function SwipeCard({ restaurant, done, total, onVote, locked }: Props) {
  const [pending, setPending] = useState(false)
  const [direction, setDirection] = useState<Choice>('like')
  const submitting = useRef(false)

  async function choose(choice: Choice) {
    if (submitting.current || locked) return
    submitting.current = true
    setPending(true)
    setDirection(choice)
    try {
      await onVote(choice)
    } finally {
      submitting.current = false
      setPending(false)
    }
  }

  function endDrag(_event: MouseEvent | TouchEvent | PointerEvent, { offset, velocity }: PanInfo) {
    const projectedX = offset.x + velocity.x * 0.14
    if (Math.abs(projectedX) >= 85) void choose(projectedX > 0 && restaurant.available ? 'like' : 'dislike')
  }

  return (
    <div className="swipe">
      <div className="progress-title"><strong>Restaurant {done + 1} of {total}</strong><span>{done} swiped</span></div>
      <progress className="progress" aria-label="Swipe progress" max={total} value={done} />
      <div className="deck" onKeyDown={event => {
        if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
          event.preventDefault()
          if (event.key === 'ArrowLeft' || restaurant.available) void choose(event.key === 'ArrowRight' ? 'like' : 'dislike')
        }
      }}>
        <AnimatePresence initial={false} mode="popLayout" custom={direction}>
          <DraggableCard key={restaurant.id} restaurant={restaurant} locked={Boolean(locked || pending)} onDragEnd={endDrag} />
        </AnimatePresence>
        <div className="swipe-actions" aria-label="Vote on this restaurant">
          <button type="button" className="swipe-btn pass" disabled={pending || locked} onClick={() => void choose('dislike')}><span><X size={26} /></span> Pass</button>
          <button type="button" className="swipe-btn like" disabled={pending || locked || !restaurant.available} onClick={() => void choose('like')}><span><Heart size={25} /></span> Like</button>
        </div>
      </div>
    </div>
  )
}
