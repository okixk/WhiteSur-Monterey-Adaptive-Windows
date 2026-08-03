# WhiteSur Monterey Adaptive für Windows

Ein **Monterey-inspiriertes, adaptives Firefox-UI-Theme für Windows 11**.

Es kombiniert eine kompakte Safari-artige Ein-Zeilen-Toolbar mit den echten Windows-Fensterknöpfen rechts, sauberem Tab-Verhalten, responsivem Layout und einem sicheren PowerShell-Installer.

![WhiteSur Monterey Adaptive in Firefox unter Windows](docs/screenshot.png)

> [!IMPORTANT]
> Dies ist ein inoffizielles Community-Projekt und steht in keiner offiziellen Verbindung zu Mozilla, Apple, Vince Liuice, Rafael Mardojai, AdamXweb oder den Entwicklern von Adaptive Tab Bar Color.

## Funktionen

- Monterey-inspirierte Firefox-Oberfläche unter Windows
- echte Windows-Knöpfe für Minimieren, Maximieren und Schliessen rechts
- Adressleiste und Tabs in einer Zeile
- Tabs verschwinden bei zu schmalen Fenstern, bevor sich Elemente überschneiden
- stabiles Spacing bei Vorwärts-, Sicherheits-, Stern- und Page-Action-Symbolen
- sauberes Schliessen von Tabs ohne unsichtbare Lücken
- freie Toolbar- und Tab-Leisten-Bereiche können das Fenster ziehen, ohne Tab-Reihenfolge oder Tab-Abtrennen zu stören
- macOS-inspirierte helle/dunkle Mittelklick-Autoscroll-Anzeige
- adaptive Farben über Firefox-Theme-Variablen
- automatische Erkennung des tatsächlich aktiven Firefox-Profils
- Backup und Wiederherstellung eines vorhandenen `chrome`-Ordners
- eine eigene `customChrome.css` bleibt bei Updates erhalten
- keine Administratorrechte nötig

## Adaptive Farben

Für die adaptive Einfärbung ist das Theme auf **Adaptive Tab Bar Color** ausgelegt:

https://addons.mozilla.org/firefox/addon/adaptive-tab-bar-colour/

Die Erweiterung passt Firefox' Theme-Farben an die aktive Webseite an. Dieses Theme verwendet Firefox' normale Lightweight-Theme-Variablen und übernimmt dadurch die dynamischen Farben.

Ohne die Erweiterung funktioniert das Layout weiterhin, aber die Farben bleiben beim aktuell ausgewählten Firefox-Theme.

## Installation

1. Repository herunterladen oder klonen.
2. Firefox vollständig schliessen; im Task-Manager darf kein `firefox.exe` mehr laufen.
3. `Install.cmd` starten.
4. Firefox wieder öffnen.

Mit `Check-Installation.cmd` kannst du das erkannte Profil und die installierte Version prüfen.

## Update

Firefox schliessen und `Install.cmd` aus der neuen Version starten. Eine vorhandene `customChrome.css` wird übernommen.

## Deinstallation

Firefox schliessen und `Uninstall.cmd` starten. Der Installer entfernt seinen verwalteten Preference-Block und stellt nach Möglichkeit das vorherige `chrome`-Backup wieder her.

## Entwicklung

Das Projekt wurde **stark mit ChatGPT vibe-codiert** und danach iterativ in echtem Firefox unter Windows getestet und korrigiert. Besonders intensiv getestet wurden URLbar-Geometrie, Tab-Schliessen, schmale Fenster, dynamisch erscheinende Toolbar-Symbole, Spacing und Fenster-Dragging.

Die detaillierten Notizen zur aktuellen Version findest du unter [`docs/VERSION-16-NOTES.de.md`](docs/VERSION-16-NOTES.de.md).

## Basis und Inspiration

Das Projekt basiert stark auf beziehungsweise wurde inspiriert von:

- [WhiteSur Firefox Theme](https://github.com/vinceliuice/WhiteSur-firefox-theme) von Vince Liuice — wichtigste visuelle und CSS-Basis
- [Firefox GNOME Theme](https://github.com/rafaelmardojai/firefox-gnome-theme) von Rafael Mardojai und Mitwirkenden — Ideen für Firefox-Chrome und Layout
- [WhiteSurFirefoxThemeMacOS](https://github.com/AdamXweb/WhiteSurFirefoxThemeMacOS) von AdamXweb — Ideen für WhiteSur-Anpassungen unter Windows und macOS

Weitere Angaben stehen in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) und im Ordner [`licenses/`](licenses/).

## Lizenz

Die Windows-Anpassung, der Installer, die Tests, Dokumentation und Änderungen dieses Repositories stehen unter **GNU Affero General Public License v3.0 oder später** (`AGPL-3.0-or-later`). Siehe [`LICENSE`](LICENSE).

Übernommene Bestandteile behalten die Copyright- und Lizenzhinweise ihrer ursprünglichen Projekte. Die hauptsächliche WhiteSur-Basis steht unter MIT; der entsprechende Hinweis bleibt im Repository erhalten.
