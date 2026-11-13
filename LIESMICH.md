# Switch 2 Cover Scraper für Batocera

*Created by DeLorean23* · [English: README.md](README.md)

## Was ist das?

**Switch 2 Cover Scraper** holt Cover, Screenshots, Logos, Fanart und Spielinfos für dein System **„Switch 2“** in Batocera (`/userdata/roms/switch2`) und trägt sie in die Spieleliste ein. Du startest ihn über **Ports** und wählst mit dem Controller aus, was geladen werden soll.

**Warum?** Der eingebaute Scraper von Batocera kennt keine Switch 2. Er sucht nur in der Switch-1-Datenbank, deshalb findet er Switch-2-Spiele wie *Mario Kart World* oder *Donkey Kong Bananza* nicht. Dieser Scraper sucht direkt bei **TheGamesDB** auf der Plattform **Nintendo Switch 2**.

## Was er laden kann

Im Menü setzt du Haken:

| Punkt | In Batocera zu sehen als |
|---|---|
| Box cover (front) | Box / Hauptbild (wenn es keinen Screenshot gibt) |
| Box cover (back) | Box-Rückseite |
| Screenshot | Bild |
| Title screen | Titelbild |
| Logo | Logo (Marquee) |
| Fanart / background | Fanart / Hintergrund |
| Game info | Name, Beschreibung, Genre, Entwickler, Publisher, Erscheinungsdatum, Spieler |

**All** setzt oder entfernt alle Haken auf einmal. Deine Auswahl wird für den nächsten Start gespeichert.

**Modus:**
- **Only missing** (Standard): nur Spiele und Punkte, die noch fehlen. Ideal, wenn neue Spiele dazugekommen sind.
- **Re-scrape all**: lädt die angehakten Punkte für alle Spiele neu und überschreibt sie.

## Download

**Switch-2-Cover-Scraper.zip** auf der Seite **[Releases](https://github.com/DeLorean23/Switch-2-Cover-Scraper/releases/latest)** herunterladen.

## Voraussetzungen

- Batocera v43 (x86_64-PC)
- Das System **Switch 2** mit deinen Spielen in `/userdata/roms/switch2` (z. B. installiert mit dem [All-In Installer & Update](https://github.com/DeLorean23/All-In))
- Internetverbindung

Kein Konto und kein eigener API-Schlüssel nötig.

## Installation

1. Den Inhalt des ZIP-Archivs nach `/userdata` entpacken. Dadurch landen der Scraper und sein Cover in `/userdata/roms/ports/`.
2. In Batocera die Spieleliste aktualisieren und **Switch 2 Cover Scraper** unter **Ports** starten.

## Steuerung

| Controller | Tastatur | Aktion |
|---|---|---|
| Steuerkreuz / linker Stick hoch und runter | Pfeiltasten | Bewegen |
| A | Enter / Leertaste | Haken setzen / entfernen, starten |
| B | Esc | Beenden |

Nach dem Scrapen wird die Spieleliste in EmulationStation automatisch neu geladen.

## Spielnamen

Der Scraper sucht nach dem Namen des Spielordners oder der Datei, z. B. `Mario Kart World.s2` oder `Donkey Kong Bananza [0100D2B00BDE0000][v0].nsp`. Klammern, Title-IDs und Versionsnummern werden ignoriert. Wurde ein Spiel in Batocera umbenannt, wird zuerst dieser Name gesucht.

Wird ein Spiel **nicht gefunden**, den Ordner bzw. die Datei auf den genauen englischen Spieltitel umbenennen und den Scraper nochmal starten. Nicht gefundene Spiele werden im Modus „Only missing“ 7 Tage lang übersprungen, damit sie nicht die monatlichen Abfragen verbrauchen.

Steht ein Spiel bei TheGamesDB nicht unter Switch 2, sucht der Scraper zusätzlich in der Switch-1-Datenbank (viele Switch-2-Spiele sind Switch-1-Spiele oder *Switch 2 Editions*).

## Dateien

| Pfad | Inhalt |
|---|---|
| `/userdata/roms/switch2/gamelist.xml` | Spieleliste (vor jeder Änderung wird `gamelist.xml.bak` angelegt) |
| `/userdata/roms/switch2/images/` | Heruntergeladene Bilder |
| `/userdata/system/configs/switch2-cover-scraper.json` | Deine Auswahl |
| `/userdata/system/switch2-cover-scraper/` | Zwischenspeicher (Genres, Entwickler, nicht gefundene Spiele) |
| `/userdata/system/logs/switch2-cover-scraper.log` | Log |

## TheGamesDB-Limit

Der Scraper nutzt einen öffentlichen API-Schlüssel von TheGamesDB mit einem monatlichen Limit an Abfragen. Pro Spiel braucht er etwa eine Abfrage; am Ende wird angezeigt, wie viele noch übrig sind. Ist das Limit aufgebraucht, wird es im nächsten Monat zurückgesetzt. Du kannst auch einen eigenen Schlüssel nutzen: unter https://api.thegamesdb.net/key.php beantragen und in `/userdata/system/configs/switch2-cover-scraper.json` als `"apikey": "dein Schlüssel"` eintragen.

## Credits

- Spieldaten und Bilder: [TheGamesDB](https://thegamesdb.net) (Community-Datenbank)
- Created by DeLorean23

## Lizenz

MIT
