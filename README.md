# Switch 2 Cover Scraper for Batocera

*Created by DeLorean23* · [Deutsche Anleitung: LIESMICH.md](LIESMICH.md)

## What is this?

**Switch 2 Cover Scraper** fetches box art, screenshots, logos, fanart and game info for your **"Switch 2"** system in Batocera (`/userdata/roms/switch2`) and writes them into the game list. You start it from **Ports** and choose with the controller what should be scraped.

**Why?** The scraper built into Batocera does not know Switch 2. It only searches the Switch 1 database, so Switch 2 games like *Mario Kart World* or *Donkey Kong Bananza* are not found. This scraper searches **TheGamesDB** directly on its **Nintendo Switch 2** platform.

## What it can fetch

In the menu you tick what you want:

| Item | Shown in Batocera as |
|---|---|
| Box cover (front) | Box / main image (if there is no screenshot) |
| Box cover (back) | Box backside |
| Screenshot | Image |
| Title screen | Title shot |
| Logo | Logo (marquee) |
| Fanart / background | Fan art |
| Game info | Name, description, genre, developer, publisher, release date, players |

**All** ticks or unticks everything at once. Your choice is saved for the next start.

**Mode:**
- **Only missing** (default): only games and items that do not have anything yet. Perfect after adding new games.
- **Re-scrape all**: fetches the ticked items again for every game and overwrites them.

## Download

Get **Switch-2-Cover-Scraper.zip** from the **[Releases](https://github.com/DeLorean23/Switch-2-Cover-Scraper/releases/latest)** page.

## Requirements

- Batocera v43 (x86_64 PC)
- The system **Switch 2** with your games in `/userdata/roms/switch2` (for example installed with the [All-In Installer & Update](https://github.com/DeLorean23/All-In))
- Internet connection

No account and no own API key needed.

## Installation

1. Extract the contents of the ZIP archive to `/userdata`. This places the scraper and its cover image in `/userdata/roms/ports/`.
2. In Batocera, refresh the game list and launch **Switch 2 Cover Scraper** from **Ports**.

## Controls

| Controller | Keyboard | Action |
|---|---|---|
| D-pad / left stick up and down | Arrow keys | Move |
| A | Enter / Space | Tick / untick, start |
| B | Esc | Exit |

After scraping, the game list in EmulationStation is reloaded automatically.

## Game names

The scraper searches by the name of the game folder or file, for example `Mario Kart World.s2` or `Donkey Kong Bananza [0100D2B00BDE0000][v0].nsp`. Things in brackets, title IDs and version numbers are ignored. If a game was renamed in Batocera, that name is searched first.

If a game is **not found**, rename the folder or file to the exact English game title and run the scraper again. Games that were not found are skipped for 7 days in the mode "Only missing", so they don't use up the monthly requests.

If a game is not listed under Switch 2 on TheGamesDB, the scraper also looks in the Switch 1 database (many Switch 2 games are Switch 1 games or *Switch 2 Editions*).

## Files

| Path | Content |
|---|---|
| `/userdata/roms/switch2/gamelist.xml` | Game list (a backup `gamelist.xml.bak` is made before every change) |
| `/userdata/roms/switch2/images/` | Downloaded images |
| `/userdata/system/configs/switch2-cover-scraper.json` | Your selection |
| `/userdata/system/switch2-cover-scraper/` | Cache (genres, developers, games not found) |
| `/userdata/system/logs/switch2-cover-scraper.log` | Log |

## TheGamesDB limit

The scraper uses a public TheGamesDB API key with a monthly limit of requests. One game needs about one request; the number of requests left is shown at the end. If the limit is used up, it is reset the next month. You can use your own key: request one at https://api.thegamesdb.net/key.php and add it to `/userdata/system/configs/switch2-cover-scraper.json` as `"apikey": "your key"`.

## Credits

- Game data and images: [TheGamesDB](https://thegamesdb.net) (community database)
- Created by DeLorean23

## License

MIT
