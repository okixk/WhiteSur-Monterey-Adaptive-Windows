# WhiteSur Monterey Adaptive für Windows

Ein Monterey-inspiriertes Firefox-Theme für Windows 11 in **Full** und **Lite**.

| | Full | Lite |
| --- | --- | --- |
| Adaptive Farben, Kapseln, Windows-Fensterknöpfe | Ja | Ja |
| Bearbeiten durch Darüberfahren | Nein | Nein |
| Ausgewählten Tab anklicken zum Bearbeiten | Ja | Strg+L / Alt+D / F6 |
| Mittelklick im Adressfeld schliesst den Tab | Ja | Normales Firefox-Verhalten |
| Mehrere normale Tabs | Bis 160px beim Surfen | Feste 240px-Plätze |
| Automatische GitHub-Theme-Updates | Ja | Keine |
| AutoConfig | Erforderlich, geschützt installiert/wiederverwendet | Wird nie installiert |

## Installation

Firefox schliessen, das vollständige gewünschte ZIP entpacken und dessen
`Install.cmd` starten. Im Quellverzeichnis installiert `Install.cmd` Full und
`Install-Lite.cmd` Lite. Explizit: `-Edition Full` oder `-Edition Lite` beim
PowerShell-Installer. `Install.cmd -DisableAutoUpdate` startet Full ohne
automatische Updates.

Full benötigt Firefox 158+ und einen freien AutoConfig-Platz. Ein passender,
fertig installierter WhiteSur-Loader wird schreibgeschützt wiederverwendet.
Bestehende cfg-/Pref-Loader-Dateien werden niemals überschrieben. Fremdes
AutoConfig, geänderte cfg-Dateien oder erkannte Unternehmensrichtlinien führen
zu einer Ablehnung mit Empfehlung für Lite. Nur die erstmalige Erstellung
eines neuen Loaders in einem geschützten Ordner kann Administratorrechte benötigen.

Lite installiert ausschliesslich Profil-CSS, ohne privilegiertes Skript,
AutoConfig oder Updater. Gesperrte Einstellungen bleiben wirksam. Der Installer
sichert einen vorherigen `chrome`-Ordner, erhält `customChrome.css` bei Updates
und verwaltet nur seinen eigenen `user.js`-Block.

## Bedienung

Full: Hintergrund-Tab auswählen, dann ausgewählten Tab anklicken, um das echte
Adressfeld zu bearbeiten. Ein schneller Doppelklick ist nicht nötig. Mittlere
Maustaste im Editor drücken und loslassen schliesst den ausgewählten Tab;
Loslassen ausserhalb bricht ab. Strg+L, Alt+D und F6 funktionieren direkt.
Escape, Navigation oder ein Klick auf die Seite stellt den Titel wieder her.
Hover hebt nur hervor. Animationen respektieren reduzierte Bewegung.

Lite: Normale Tab-Klicks bleiben nativ, insbesondere Mittelklick zum Schliessen
eines Browsing-Tabs. Hover öffnet kein Eingabefeld. Strg+L, Alt+D, F6 und neue
Tabs verwenden das native Adressfeld. Bei CSS-Ankerunterstützung liegt es am
ausgewählten horizontalen Tab; in schmalen Fenstern, ohne Anker oder bei einer
angehefteten Auswahl wird eine separate Adresszeile verwendet. Vertikale Tabs
behalten ihre Sidebar. CSS kann die Maustasten im fokussierten Eingabefeld
nicht umbelegen.

Beide Editionen verwenden Firefox-Theme-Farben, unter anderem von
[Adaptive Tab Bar Color](https://addons.mozilla.org/firefox/addon/adaptive-tab-bar-colour/).

## Automatische Updates in Full

Full prüft veröffentlichte GitHub-Releases nach dem Start und höchstens täglich.
Vorabversionen werden während der Beta-Phase berücksichtigt. Unter **Tools →
WhiteSur Updates** lässt sich manuell prüfen, der Status ansehen und die
Automatik ausschalten. Ein ausgeschalteter Zustand bleibt bei normalen
Installer-Updates erhalten.

Ein neueres Full-ZIP wird heruntergeladen, mittels GitHub-SHA-256 und Datei-Manifest
geprüft und bereitgelegt. Beim normalen Beenden wird das verwaltete Theme vor
Freigabe der Profilsperre ersetzt; der nächste Start verwendet das neue Theme.
Der laufende Browser wird nicht mitten in der Sitzung umgestellt. Änderungen
an `customChrome.css`, auch nach dem Download, bleiben erhalten. Andere verwaltete
Theme-Dateien können ersetzt werden; Firefox, cfg-Dateien, Richtlinien,
Erweiterungen, Einstellungen und Zertifikate werden nicht geändert.

Das Update umfasst auch Fulls privilegierten Browser-UI-Code und vertraut dem
Release-Herausgeber des festen GitHub-Repositories. Prüfsummen sind keine
unabhängigen Autorensignaturen. Heruntergeladene Installer werden nie ausgeführt.
Loader-Protokolländerungen erfordern eine manuelle Installation.

Nach einem Absturz bleibt ein Update bis zum nächsten normalen Beenden
bereitgelegt. Vorherige Theme-Versionen werden als Backup behalten. Falls ein
Stromausfall zwischen Verzeichniswechseln `chrome` fehlen lässt, stellt der
Installer beim erneuten Ausführen sein eigenes Backup wieder her. Einzelheiten
und Testergebnisse: [AUTO-UPDATES.md](docs/AUTO-UPDATES.md).

## Update und Deinstallation

Firefox schliessen und den gewünschten Installer erneut ausführen. Der Wechsel
zu Lite entfernt das Profilsystem für Skript/Updater und verwirft wartende
Full-Updates. Gemeinsam verwendete Installations-Loader bleiben unangetastet.
`Check-Installation.cmd` zeigt Profil, Version, Edition und erkannte Konfigurationen.
`Uninstall.cmd` entfernt Theme und verwaltete Preferences und stellt vorhandene
Chrome-Backups wieder her. Update-Caches und Rollback-Kopien bleiben zur manuellen
Wiederherstellung erhalten und können ohne Full nicht angewendet werden.

Tests laufen in isolierten Kopien und Profilen, einschliesslich echter
Firefox-Neustarts. Befehle: [TESTING.md](docs/TESTING.md). Browser-Chrome-CSS und
privilegierte UI-Schnittstellen sind keine stabilen öffentlichen Mozilla-APIs.
Dies ist ein inoffizielles Projekt ohne Verbindung zu Mozilla oder Apple.

## Basis und Inspiration

Das Projekt basiert stark auf beziehungsweise wurde inspiriert von:

- [WhiteSur Firefox Theme](https://github.com/vinceliuice/WhiteSur-firefox-theme) von Vince Liuice — wichtigste visuelle und CSS-Basis
- [Firefox GNOME Theme](https://github.com/rafaelmardojai/firefox-gnome-theme) von Rafael Mardojai und Mitwirkenden — Ideen für Firefox-Chrome und Layout
- [WhiteSurFirefoxThemeMacOS](https://github.com/AdamXweb/WhiteSurFirefoxThemeMacOS) von AdamXweb — Ideen für WhiteSur-Anpassungen unter Windows und macOS

Weitere Angaben stehen in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) und im Ordner [`licenses/`](licenses/).

## Lizenz

Die Windows-Anpassung, der Installer, die Tests, Dokumentation und Änderungen dieses Repositories stehen unter **GNU Affero General Public License v3.0 oder später** (`AGPL-3.0-or-later`). Siehe [`LICENSE`](LICENSE).

Übernommene Bestandteile behalten die Copyright- und Lizenzhinweise ihrer ursprünglichen Projekte. Die hauptsächliche WhiteSur-Basis steht unter MIT; der entsprechende Hinweis bleibt im Repository erhalten.
