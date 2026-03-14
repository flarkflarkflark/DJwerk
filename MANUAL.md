# De Ultieme DJwerk Handleiding 🎧

Welkom bij **DJwerk**, de universele crate engine van flarkAUDIO die de kloof overbrugt tussen vloeibare cloud-muziek en solide fysieke DJ-bibliotheken.

## Wat is DJwerk?
DJwerk is een autonome tool ontworpen voor DJ's die hun bibliotheek willen synchroniseren tussen verschillende platforms. Het downloadt tracks met de hoogst mogelijke kwaliteit (FLAC of MP3 320kbps), embedt metadata en cover art, en werkt direct je Pioneer Rekordbox en Engine DJ bibliotheken bij.

## Hoe gebruik je de Universal Sync?
1. Kopieer de URL van een Spotify playlist, album of track.
2. Plak de URL in de balk bovenaan in het DJwerk paneel.
3. Klik op **Sync Crate**.
4. DJwerk analyseert de bron, zoekt de beste kwaliteit match en downloadt de tracks naar de `downloads/` map.
5. Metadata zoals BPM, Key en Cover Art worden automatisch ingebakken.

## Pioneer Rekordbox Integratie
DJwerk genereert automatisch een `rekordbox.xml` bestand in de hoofdmap.
1. Open Pioneer Rekordbox.
2. Ga naar **Preferences** -> **Advanced** -> **Database**.
3. Bij **rekordbox xml**, selecteer het `rekordbox.xml` bestand in je DJwerk map.
4. In de Rekordbox zijbalk verschijnt nu een sectie "rekordbox xml". Hier vind je al je gesynchroniseerde tracks klaar om te importeren in je collectie.

## Algoriddim djay Sync
Voor mobiele DJ's ondersteunt DJwerk sync naar Algoriddim djay.
1. Synchroniseer je DJwerk `downloads/` map met een cloud-service zoals iCloud, Dropbox of Google Drive.
2. Open djay op je iPad of iPhone.
3. Ga naar de **Files** bron en navigeer naar je gesynchroniseerde map.
4. De tracks zijn direct laadbaar met alle metadata die door DJwerk is toegevoegd.

## Engine DJ (Denon/Numark) Integratie
DJwerk schrijft tracks direct weg naar een Engine-compatibele database (`m.db`).
1. Sluit je Engine DJ device (zoals een Prime Go of USB-stick) aan op je computer.
2. Kopieer het bestand `m.db` uit de DJwerk map naar de map `Engine Library/` op je device.
3. De tracks staan nu direct in de bibliotheek van je hardware, inclusief cues en metadata.

## STEMwerk Integratie (Upcoming)
Met de **Auto-Stem Sync** schakelaar kun je tracks direct door de flarkAUDIO STEMwerk engine halen. Hiermee worden tracks gesplitst in Vocals, Drums, Bass en Other, zodat je altijd over de stems beschikt voor je live mashups. *Opmerking: Deze feature is momenteel in de proto-link fase.*

## Crate Health Reports Lezen
Regelmatig onderhoud is essentieel voor een professionele DJ-crate. Klik op **Scan Crate Health** in de zijbalk om je downloads te controleren.
- **Duplicates:** Tracks die dubbel aanwezig zijn (of sterk op elkaar lijken) worden gemarkeerd zodat je ruimte kunt besparen.
- **Low Bitrate:** Tracks onder de 320kbps worden gedetecteerd. Voor club-gebruik raden we aan deze te vervangen door hogere kwaliteit.
- **Missing Art:** Tracks zonder hoesafbeelding worden getoond, zodat je bibliotheek er op elk scherm strak uitziet.

Alle rapporten worden opgeslagen in `REPORTS.md` voor latere referentie.

---
*Liquid to Solid | flarkAUDIO 2024*
