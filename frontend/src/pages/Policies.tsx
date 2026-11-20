import { Page } from '../components/Layout'

export default function Policies({ privacy = false }: { privacy?: boolean }) {
  return (
    <Page title={privacy ? 'Privacy.' : 'Terms.'}>
      <div className="panel policy">
        {privacy ? <>
          <p>FoodMatch uses the location you select to find nearby restaurants. When you create a group, it stores the room’s preferences, display names, and votes so the group can resume and see its results.</p>
          <p>Your browser keeps a guest token for each room you join and saves solo choices on that device. Clear the site’s storage to remove them from your browser. Room access ends when the room expires.</p>
          <p>Live discovery sends search coordinates to Google Maps Platform. Google describes its handling of that data in the <a href="https://policies.google.com/privacy">Google Privacy Policy</a>.</p>
        </> : <>
          <p>FoodMatch helps you compare restaurants and agree on where to eat. Details and prices can change. Sample venues are fictional and use illustrative photography.</p>
          <p>Live restaurant information is subject to the <a href="https://www.google.com/intl/en_US/help/terms_maps/">Google Maps and Earth Additional Terms of Service</a>.</p>
        </>}
      </div>
    </Page>
  )
}
