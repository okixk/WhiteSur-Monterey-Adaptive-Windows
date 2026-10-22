# WhiteSur Monterey Adaptive für Windows

Ein **Monterey-inspiriertes, adaptives Firefox-UI-Theme für Windows 11**.

Der ausgewählte Tab wird zur nativen Firefox-Adress- und Suchleiste. Tab anklicken und eine Adresse oder Suche eingeben; die übrigen Tabs bleiben kompakt. Adaptive Farben, echte Windows-Fensterknöpfe, Profilerkennung, Backups und Deinstallation bleiben erhalten.

**v0.2.0-beta.2 installiert editierbare Tabs direkt im vorhandenen Firefox. Die gewohnten Verknüpfungen funktionieren weiterhin.** Details stehen in den [Release Notes](docs/releases/v0.2.0-beta.2.md) (Englisch).

![WhiteSur Monterey Adaptive in Firefox unter Windows](docs/screenshot.png)

> [!IMPORTANT]
> Dies ist ein inoffizielles Community-Projekt und steht in keiner offiziellen Verbindung zu Mozilla, Apple, Vince Liuice, Rafael Mardojai, AdamXweb oder den Entwicklern von Adaptive Tab Bar Color.

## Funktionen

- Monterey-inspirierte Firefox-Oberfläche unter Windows
- echte Windows-Knöpfe für Minimieren, Maximieren und Schliessen rechts
- ausgewählte Tabs als native Adressleiste inklusive Symbolen und Suchvorschlägen
- kompakte Hintergrund-Tabs, die bei Platzmangel schmaler werden
- stabile Tab-Wechsel und Schliessvorgänge ohne animierte Breitenänderungen
- klassische CSS-Toolbar als Fallback für ältere Firefox-Versionen, vertikale Tabs und vorhandene AutoConfig-Setups
- stabiles Spacing bei Vorwärts-, Sicherheits-, Stern- und Page-Action-Symbolen
- sauberes Schliessen von Tabs ohne unsichtbare Lücken
- freie Toolbar- und Tab-Leisten-Bereiche können das Fenster ziehen, ohne Tab-Reihenfolge oder Tab-Abtrennen zu stören
- macOS-inspirierte helle/dunkle Mittelklick-Autoscroll-Anzeige
- adaptive Farben über Firefox-Theme-Variablen
- automatische Erkennung des tatsächlich aktiven Firefox-Profils
- Backup und Wiederherstellung eines vorhandenen `chrome`-Ordners
- eine eigene `customChrome.css` bleibt bei Updates erhalten
- Loader im vorhandenen Firefox; Windows fragt bei geschützten Ordnern nach Administratorrechten

## Adaptive Farben

Für die adaptive Einfärbung ist das Theme auf **Adaptive Tab Bar Color** ausgelegt:

https://addons.mozilla.org/firefox/addon/adaptive-tab-bar-colour/

Die Erweiterung passt Firefox' Theme-Farben an die aktive Webseite an. Dieses Theme verwendet Firefox' normale Lightweight-Theme-Variablen und übernimmt dadurch die dynamischen Farben.

Ohne die Erweiterung funktioniert das Layout weiterhin, aber die Farben bleiben beim aktuell ausgewählten Firefox-Theme.

## Installation

1. Repository herunterladen oder klonen.
2. Firefox vollständig schliessen; im Task-Manager darf kein `firefox.exe` mehr laufen.
3. `Install.cmd` starten.
4. Bei Bedarf die Windows-Administratorabfrage bestätigen. Firefox öffnet sich automatisch; die gewohnten Verknüpfungen funktionieren weiterhin.

Ab Firefox 158 ergänzt der Installer die Loader-Dateien direkt in der vorhandenen Firefox-Installation. Profil, Erweiterungen, Lesezeichen und Verknüpfungen werden weiterverwendet. Nur das Schreiben des Loaders wird bei Bedarf mit Administratorrechten ausgeführt; die Profilinstallation bleibt beim ursprünglichen Benutzer.

Normale Eingaben verwenden die Firefox-Standardsuche. `g Suchbegriffe` sucht mit Google, `q Suchbegriffe` mit Qwant. `Strg+L`, `Alt+D` und `F6` fokussieren das Feld. `Esc` verwirft die Eingabe; das Feld bleibt sichtbar.

Nur die klassische adaptive Toolbar installieren:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-WhiteSur-Monterey-Adaptive.ps1 -ClassicToolbar
```

Details und eigene Installationspfade: [Editable tabs](docs/EDITABLE-TABS.md) (Englisch).

Mit `Check-Installation.cmd` kannst du das erkannte Profil und die installierte Version prüfen.

## Update

Firefox schliessen und `Install.cmd` aus der neuen Version starten. Eine vorhandene `customChrome.css` wird übernommen. Der Loader wird im vorhandenen Firefox aktualisiert. Falls ein Firefox-Update den Loader entfernt, den Installer erneut ausführen.

## Deinstallation

Firefox schliessen und `Uninstall.cmd` starten. Der Installer entfernt seine verwalteten Preferences und stellt nach Möglichkeit das vorherige `chrome`-Backup wieder her. Der gemeinsam genutzte Loader bleibt für andere installierte Profile erhalten und ignoriert Profile ohne Theme-Markierung. Firefox bleibt installiert. Eine alte separate Kopie aus beta.1 kann nach dem Wechsel zum gewohnten Firefox manuell entfernt werden.

## Kompatibilität

Version `2026.10.22-22` (`v0.2.0-beta.2`) benötigt für editierbare Tabs Firefox 158+ mit horizontalen Tabs. Bei älteren Versionen, fehlendem Firefox, AutoConfig-Konflikten oder Fehlern beim Einrichten der Laufzeit bricht die Standardinstallation vor Änderungen am Profil ab. Das klassische CSS-Layout wird ausdrücklich mit `Install.cmd -ClassicToolbar` gewählt. Vertikale Tabs aktivieren das Skript nicht. `Install.cmd` öffnet den eingerichteten Firefox nach erfolgreicher Installation automatisch und leitet zusätzliche Parameter weiter.

Adaptive Tab Bar Color bleibt kompatibel: beide Layouts verwenden Firefox-Theme-Variablen. Die nativen Tests prüfen helle und dunkle Farbwechsel; das Verhalten einzelner Erweiterungen hängt auch von deren Einstellungen ab.

## Entwicklung

Das Projekt wurde **stark mit ChatGPT vibe-codiert** und danach iterativ in echtem Firefox unter Windows getestet und korrigiert. Besonders intensiv getestet wurden URLbar-Geometrie, Tab-Schliessen, schmale Fenster, dynamisch erscheinende Toolbar-Symbole, Spacing und Fenster-Dragging.

Die aktuellen Tests und Befehle stehen unter [`docs/TESTING.md`](docs/TESTING.md). Dazu gehören echte Firefox-Tests für die Tab-Geometrie und Windows-PowerShell-Tests für Installation, Update, Fallback und Deinstallation.

## Basis und Inspiration

Das Projekt basiert stark auf beziehungsweise wurde inspiriert von:

- [WhiteSur Firefox Theme](https://github.com/vinceliuice/WhiteSur-firefox-theme) von Vince Liuice — wichtigste visuelle und CSS-Basis
- [Firefox GNOME Theme](https://github.com/rafaelmardojai/firefox-gnome-theme) von Rafael Mardojai und Mitwirkenden — Ideen für Firefox-Chrome und Layout
- [WhiteSurFirefoxThemeMacOS](https://github.com/AdamXweb/WhiteSurFirefoxThemeMacOS) von AdamXweb — Ideen für WhiteSur-Anpassungen unter Windows und macOS

Weitere Angaben stehen in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) und im Ordner [`licenses/`](licenses/).

## Lizenz

Die Windows-Anpassung, der Installer, die Tests, Dokumentation und Änderungen dieses Repositories stehen unter **GNU Affero General Public License v3.0 oder später** (`AGPL-3.0-or-later`). Siehe [`LICENSE`](LICENSE).

Übernommene Bestandteile behalten die Copyright- und Lizenzhinweise ihrer ursprünglichen Projekte. Die hauptsächliche WhiteSur-Basis steht unter MIT; der entsprechende Hinweis bleibt im Repository erhalten.
