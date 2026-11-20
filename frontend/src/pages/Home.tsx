import { ArrowRight, Heart, MapPin, Share2, Users, Utensils } from 'lucide-react'
import { Link } from 'react-router'

const steps = [
  { icon: Share2, title: 'Invite your people', detail: 'Create a room and send the link in your group chat.' },
  { icon: Heart, title: 'Swipe for what you love', detail: 'Everyone gets the same shortlist and votes on their own.' },
  { icon: MapPin, title: 'Meet at the match', detail: 'See what the group liked most and get directions.' },
]

export default function Home() {
  return (
    <>
      <section className="hero wrap">
        <div className="hero-copy">
          <p className="eyebrow"><span /> RESTAURANT DISCOVERY</p>
          <h1>Dinner plans,<br /><em>sorted.</em></h1>
          <p className="hero-description">Discover restaurants nearby, swipe on what looks good, and find a place everyone can get excited about.</p>
          <div className="hero-actions">
            <Link className="btn primary" to="/create"><Users size={19} /> Create Group <ArrowRight size={19} /></Link>
            <Link className="btn secondary" to="/solo"><Utensils size={17} /> Find Food</Link>
          </div>
          <p className="hero-note">No signup needed.</p>
        </div>
        <div className="hero-art">
          <img src="/food/indian.jpg" alt="An Indian meal with creamy curry, naan, and fresh herbs" fetchPriority="high" />
        </div>
      </section>
      <section className="how">
        <div className="wrap">
          <h2>How group matching works</h2>
          <div className="steps">
            {steps.map(({ icon: Icon, title, detail }) => (
              <article key={title}><span className="step-icon"><Icon size={22} /></span><div><h3>{title}</h3><p>{detail}</p></div></article>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
