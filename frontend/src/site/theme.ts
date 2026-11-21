import { useCallback, useEffect, useState } from 'react'

export type Theme = 'dark' | 'light'
const KEY = 'amcrax-theme'

function read(): Theme {
  try {
    const v = window.localStorage.getItem(KEY)
    if (v === 'light' || v === 'dark') return v
  } catch { /* storage can be blocked */ }
  return 'dark'
}

/** Theme shared by the site and the platform; dark by default, remembered per browser (best effort). */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(read)
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  const toggle = useCallback(() => {
    setTheme((t) => {
      const n = t === 'dark' ? 'light' : 'dark'
      try { window.localStorage.setItem(KEY, n) } catch { /* ignore */ }
      return n
    })
  }, [])
  return [theme, toggle]
}
