import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { suggestTerms } from '../lib/searchSuggest'

export function SearchBox({
  terms,
  value,
  onChange,
  placeholder = '搜索…',
}: {
  terms: string[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [focused, setFocused] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const suggestions = focused ? suggestTerms(value, terms) : []

  useEffect(() => {
    setActiveIndex(suggestions.length > 0 ? 0 : -1)
  }, [value, suggestions.length, focused])

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setFocused(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const pick = (term: string) => {
    onChange(term)
    setFocused(false)
    inputRef.current?.focus()
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => (i + 1) % suggestions.length)
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => (i <= 0 ? suggestions.length - 1 : i - 1))
      return
    }
    if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault()
      pick(suggestions[activeIndex]!)
      return
    }
    if (e.key === 'Escape') {
      setFocused(false)
    }
  }

  return (
    <div className="search-box" ref={wrapRef}>
      <input
        ref={inputRef}
        className="fg-input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        spellCheck={false}
        role="combobox"
        aria-expanded={suggestions.length > 0}
        aria-activedescendant={
          activeIndex >= 0 ? `search-suggest-${activeIndex}` : undefined
        }
      />
      {suggestions.length > 0 && (
        <ul className="search-suggest" role="listbox">
          {suggestions.map((term, index) => (
            <li key={term}>
              <button
                id={`search-suggest-${index}`}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                className={index === activeIndex ? 'active' : undefined}
                onMouseDown={() => pick(term)}
                onMouseEnter={() => setActiveIndex(index)}
              >
                {highlightMatch(term, value.trim())}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function highlightMatch(text: string, query: string): ReactNode {
  if (!query) return text
  const lower = text.toLowerCase()
  const q = query.toLowerCase()
  const idx = lower.indexOf(q)
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="search-suggest-mark">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}
