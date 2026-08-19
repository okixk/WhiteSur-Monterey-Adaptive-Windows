# Versionshinweise 2026.08.19-17

## Firefox 154-Kompatibilität

Firefox 154 verwendet die Tab-Zustände weiterhin als boolesche Attribute wie
`[selected]` und `[visuallyselected]`. Ältere Theme-Regeln mit
`[selected=true]`, `[selected="true"]` oder `[visuallyselected="true"]` können
dadurch die Inaktiv-Regel auf den aktiven Tab anwenden.

Diese Version:

- verwendet boolesche Tab-State-Selektoren;
- bindet den aktiven Hintergrund zusätzlich an den Zustand des
  `.tabbrowser-tab` statt nur an `.tab-background`;
- unterstützt `selected`, `visuallyselected`, `visually-selected` und
  `multiselected`;
- behält die bisherigen Firefox-154-unabhängigen Layout-, Dragging- und
  Autoscroll-Anpassungen unverändert;
- fügt einen eigenen Playwright-Regressionstest für den aktiven Tab hinzu.

Vor der Neuinstallation sichert das Reparaturskript den aktiven `chrome`-Ordner
und `user.js` unter `.local-patch-backups/`.
