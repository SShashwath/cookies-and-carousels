import { Link, Route, Routes } from 'react-router'
import { Layout, Page } from './components/Layout'
import { SoloDeckProvider } from './hooks/useSoloDeck'
import Group from './pages/Group'
import Home from './pages/Home'
import Policies from './pages/Policies'
import Setup from './pages/Setup'
import Solo from './pages/Solo'

export default function App() {
  return (
    <SoloDeckProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="solo" element={<Setup />} />
          <Route path="solo/swipe" element={<Solo key="swipe" />} />
          <Route path="solo/results" element={<Solo key="results" results />} />
          <Route path="create" element={<Setup key="group" group />} />
          <Route path="room/:code" element={<Group />} />
          <Route path="privacy" element={<Policies privacy />} />
          <Route path="terms" element={<Policies />} />
          <Route path="*" element={<Page title="Page unavailable."><Link className="btn primary" to="/">Back to FoodMatch</Link></Page>} />
        </Route>
      </Routes>
    </SoloDeckProvider>
  )
}
