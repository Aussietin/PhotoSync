// Central navigation model — shared by desktop nav, the "More" menu,
// and the mobile sheet so labels/icons stay in sync everywhere.

export const primaryNav = [
  { to: '/', label: 'Library', icon: '🖼️' },
  { to: '/cleanup', label: 'Cleanup', icon: '✨', accent: true },
  { to: '/triage', label: 'Triage', icon: '🃏' },
  { to: '/albums', label: 'Albums', icon: '🗂️' },
  { to: '/search', label: 'Search', icon: '🔍' },
]

export const navGroups = [
  {
    title: 'Tidy up',
    items: [
      { to: '/screenshots', label: 'Screenshots', icon: '📱', desc: 'Find & clear screen grabs' },
      { to: '/duplicates', label: 'Duplicates', icon: '🔁', desc: 'Near-identical shots' },
      { to: '/bursts', label: 'Bursts', icon: '📸', desc: 'Keep the best of each burst' },
      { to: '/large', label: 'Large files', icon: '🎬', desc: 'Biggest videos & photos' },
    ],
  },
  {
    title: 'Browse',
    items: [
      { to: '/timeline', label: 'Timeline', icon: '📅', desc: 'By date taken' },
      { to: '/map', label: 'Map', icon: '🗺️', desc: 'Photos with GPS' },
      { to: '/stats', label: 'Stats', icon: '📊', desc: 'Library insights' },
    ],
  },
  {
    title: 'Library',
    items: [
      { to: '/import', label: 'Import', icon: '📥', desc: 'Add a local folder' },
      { to: '/upload', label: 'Upload', icon: '⬆️', desc: 'Send photos here' },
      { to: '/export', label: 'Export', icon: '📦', desc: 'Download a ZIP' },
      { to: '/trash', label: 'Trash', icon: '🗑️', desc: 'Restore or empty' },
    ],
  },
]

// Flat list of everything for the mobile sheet
export const allDestinations = [...primaryNav, ...navGroups.flatMap((g) => g.items)]
