import { resetAppearanceDefaults } from './theme'
import { resetDisplayDefaults } from './display'
import { resetLayoutPrefs } from './layoutPrefs'
import { resetAllShortcuts } from './shortcuts'

export function resetAllPreferences(): void {
  resetDisplayDefaults()
  resetAppearanceDefaults()
  resetLayoutPrefs()
  resetAllShortcuts()
}
