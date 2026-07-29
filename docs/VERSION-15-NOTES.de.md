# WhiteSur Monterey Adaptive für Windows – Version 15

Version 15 baut direkt auf dem funktionierenden URLbar-Fix aus Version 14 auf. Der lange Balken bleibt entfernt. Diese Ausgabe behebt die letzten zwei Punkte aus dem Windows-Test:

1. Die Navigation verschiebt sich nicht mehr, wenn der Vorwärts-Button erscheint oder wieder deaktiviert wird.
2. Ein wiederhergestelltes Firefox-Fenster besitzt wieder echte ziehbare Leerbereiche, ohne Tabs oder Buttons zu blockieren.

## Installation

1. Firefox vollständig schließen. Auch im Task-Manager darf kein `firefox.exe` mehr laufen.
2. Das ZIP in einen normalen Ordner entpacken.
3. `Install.cmd` doppelklicken.
4. Firefox starten.

Version 15 kann direkt über Version 14 installiert werden. Eine vorhandene `customChrome.css` wird weiterhin übernommen.

## Änderung 1: stabiles Spacing links von der Adressleiste

Firefox blendet den deaktivierten Vorwärts-Button normalerweise vollständig aus. Sobald Vorwärtsnavigation verfügbar wird, erscheint dieser Button wieder und verschiebt die Adressleiste um ungefähr eine Buttonbreite nach rechts. Da die Tabs in dieser Windows-Anpassung in derselben Zeile liegen, konnte das rechte Ende der Adressleiste dadurch in den ersten Tab hineinragen.

Version 15 hält den 32-Pixel-Platz des Vorwärts-Buttons deshalb immer frei:

- deaktiviert: unsichtbar, aber weiterhin im Layout;
- aktiviert: sichtbar, exakt an derselben Position;
- URLbar und Tabs bewegen sich beim Zustandswechsel nicht mehr;
- die Desktop-Reservation wurde auf 510 Pixel erhöht.

Im lokalen 1310-Pixel-Test bleiben URLbar und Tab-Leiste in beiden Zuständen identisch positioniert. Der freie Abstand beträgt im Modell 40 Pixel.

Testbilder:

- `tests/navigation-forward-disabled.png`
- `tests/navigation-forward-enabled.png`
- `tests/navigation-spacing-report.json`

## Änderung 2: Fenster wieder ziehen

Die vorherige Regel markierte praktisch den gesamten `nav-bar-customization-target` als `no-drag`. Dadurch gab es trotz sichtbarer Leerflächen kaum einen gültigen Windows-Titelleistenbereich.

Version 15 verwendet nun dieses Modell:

- leere Toolbar-, Tabstrip- und Navigationscontainer: `-moz-window-dragging: drag`;
- echte Tabs, URLbar, Buttons, Scrollbuttons und Fensterknöpfe: `-moz-window-dragging: no-drag`;
- auch freie Bereiche innerhalb der Tab-Leiste können zum Ziehen dienen;
- Klicks, Tab-Auswahl und Tab-Reihenfolge bleiben normale Interaktionen.

Praktische Ziehflächen sind insbesondere der freie Bereich zwischen Adressleiste und erstem Tab sowie freie Tabstrip-Fläche neben den Tabs.

## Beibehaltene Korrekturen

- kein langer oder gestrichelter URLbar-Balken mehr;
- sauberes und schnelles Schließen von Tabs;
- einfacher Tab-Schließen-Button;
- Tabs verschwinden in zu schmalen Fenstern, statt sich zu überschneiden;
- echte Windows-Schaltflächen rechts;
- adaptive Monterey-Farben;
- keine globalen CSS-Regeln innerhalb normaler Webseiten.

## Tests

Das fertige Paket besteht 16 von 16 automatisierten Testgruppen. Zusätzlich wurden folgende Geometriezustände gerendert:

- Fensterbreiten von 600 bis 1668 Pixel;
- Vorwärts deaktiviert und aktiviert;
- kompakter Modus und einzeiliger Desktop-Modus;
- URLbar fokussiert, unfokussiert und mit geöffneten Vorschlägen;
- Tab-Schließen und Entfernen des Closing-Spacers.

Die URLbar-Geometrie aus Version 14 wird erneut geprüft: Im Test existieren weiterhin 0 farbige Randpixel rechts außerhalb der sichtbaren Adressleiste.

Das native Windows-Hit-Testing für `-moz-window-dragging` kann in der Linux-/Chromium-Testumgebung nicht vollständig ausgeführt werden. Die Selektoren und die Regionsaufteilung sind statisch geprüft; der endgültige native Drag-Test erfolgt in Firefox unter Windows.

## Kontrolle

`Check-Installation.cmd` zeigt das aktive Firefox-Profil und die installierte Version. In `VERSION.txt` muss stehen:

```text
2026.07.28-15
```
