# Versionshinweise 2026.08.03-16

Diese Version fasst die nach dem ersten Repository-Release getesteten UI-Korrekturen sauber im eigentlichen Theme zusammen.

## Änderungen

- Der Mittelklick-Autoscroll-Indikator verwendet jetzt einen eigenen macOS-inspirierten Puck.
- Für Light Mode und Dark Mode sowie für freie, vertikale und horizontale Scroll-Richtung gibt es eigene Grafiken.
- Der Autoscroller wird von den allgemeinen Popup-Regeln ausgenommen, damit Firefox das Symbol nicht mehr entfernt.
- Leere Bereiche der Tab-Leiste können das Fenster ziehen.
- Tabs, Schliessen-, Neuer-Tab-, Alle-Tabs-, Navigations- und Windows-Fensterknöpfe bleiben normale Klickziele.
- Während Firefox einen Tab verschiebt oder aus dem Fenster löst, wird die Tab-Leiste vorübergehend zu `no-drag`.
- Die zusätzliche 15-Pixel-Geometrie von Firefox' `movingtab`-Zustand wird im kompakten Ein-Zeilen-Layout neutralisiert.
- Der Abstand zwischen Adressfeld und erstem Tab wurde auf dem Desktop von 510 px auf 498 px reduziert.

## Manuell getestet

- Autoscroll in hellem und dunklem Theme
- Fensterziehen über freie Toolbar- und Tab-Leisten-Flächen
- Tabs innerhalb der Leiste verschieben
- Tabs aus dem Fenster lösen und wieder einsetzen
- Neuer-Tab-, Tab-Schliessen- und Windows-Fensterknöpfe
- endgültiges Desktop-Spacing bei `--whitesur-left-zone: 498px`

## Hinweise

Firefox-Chrome-CSS ist keine stabile öffentliche Firefox-API. Die Selektoren können sich mit künftigen Firefox-Versionen ändern.
