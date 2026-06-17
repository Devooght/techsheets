---
name: devooght-techsheet-v2
description: Technische fiches (datasheets) maken in de Devooght-huisstijl (v2, blauw) en online zetten op de webshop via cloudopslag (jsDelivr), tweetalig NL/FR. Trigger bij "technische fiche", "datasheet", "TDS", "productfiche maken", "fiche in devooght stijl", "fiche online zetten".
---

# Devooght Technische Fiche v2 (huisstijl + cloud)

Maakt gepolijste, tweetalige (NL/FR) technische fiches in de **Devooght-huisstijl** en zet ze
online op de webshop **zonder data-kost in Odoo** (cloud-link via jsDelivr).

## Stijl (vast)
- Officieel logo (`assets/logo.png` / reverse `assets/logo_reverse.png`).
- Huisstijlkleuren: donkerblauw #274472, blauw #2a508d, lichtblauw #1e8fce, lichtgrijs #e3ebf2.
- Lettertype Montserrat (gebundeld). Mark (bedrijfslettertype): TTF's in `assets/fonts/` zetten + `FONT_FAMILY='Mark'`.
- 1 pagina per taal. Header met "Technische fiche/Fiche technique"-chip + optioneel "Ref. <code>".
- Hero (titel + foto), Beschrijving, 4 highlight-kaarten, spec-tabel (1 of meer kolommen),
  Toepassingen met blauwe checks, footer met contact (**hooglede@devoplast.com**), revisiedatum,
  **QR → https://www.devoplast.com/r/Sk4**, en de verplichte voorbehoud-regel
  ("Onder voorbehoud van fouten ... met behulp van AI opgesteld").

## Genereren
```bash
pip install weasyprint "qrcode[pil]"
python3 fiche_builder.py product.json --lang nl --out TDS_<Naam>_NL.pdf
python3 fiche_builder.py product.json --lang fr --out TDS_<Naam>_FR.pdf
```
JSON-velden: `code`, `image`, `revision`, `qr_url`, en per taal `nl`/`fr`:
`label, title, subtitle, intro, highlights[[k,v]], specs{header,rows}, applications[]`.
Specs-tabel mag meerdere kolommen (bv. codes 25 m / 50 m). Zie `voorbeeld_*.json` en de
batch-voorbeelden `voorbeeld_batch_putten.py` / `voorbeeld_batch_petry.py` (parsen specs uit de
productnaam, halen de echte productfoto via `/web/image/product.template/<id>/image_1920`).

## REGELS (belangrijk)
- **Bestandsnaam ALTIJD** `TDS_<naam>_NL.pdf` / `TDS_<naam>_FR.pdf`.
- **Aparte NL- en FR-fiche** (geen tweetalige in één PDF). Telkens beide talen maken.
- **Enkel Devooght-artikelcodes** (default_code). Geen leveranciersnaam, geen accessoires/artikelen
  buiten ons gamma. (Uitzondering: als het merk zelf het product IS, bv. "Petry"-ladders.)
- Mailadres in de footer = **hooglede@devoplast.com**.
- QR → **https://www.devoplast.com/r/Sk4**.
- Voorbehoud-AI-regel staat verplicht onderaan.

## Online zetten — ALTIJD via cloudopslag (geen Odoo-kopie)
1. Push de PDF's naar de publieke repo **Devooght/techsheets** (map per reeks, bv. `pe-putten/`, `petry/`).
2. Publieke URL = `https://cdn.jsdelivr.net/gh/Devooght/techsheets@main/<map>/<bestand>.pdf` (jsDelivr CDN).
3. Maak per product een `product.document` aan **type=url** (geen binaire data). Efficiënt in bulk via
   de Odoo MCP `create("product.document", [ {...}, ... ])`:
   ```
   {name, type:"url", url:<jsdelivr>, res_model:"product.template", res_id:<id>,
    mimetype:"application/pdf", shown_on_product_page:true,
    x_document_type:"technical", x_document_lang:"nl"|"fr", public:true}
   ```
   (Eén `product_doc_link` per product kan ook, maar bulk-`create` is veel zuiniger.)
4. **Bestaande andere fiches online?** Zet die op `shown_on_product_page=false` (NIET verwijderen).
5. Bron-kopie van de PDF's in `Verkoop/Productfiches/<reeks>/`.

## Verifiëren
Publieke download: `https://www.devoplast.com/web/content/<attachment_id>` of de jsDelivr-URL.
De `/shop`-pagina zelf is vanuit het buitenland Cloudflare-challenged (sandbox kan ze niet lezen);
controleer via de `web/content`/CDN-URL of via een BE-browser.

## Reeds uitgerold (17/06/2026)
- Flexibele kabelbuis (ex-Caboflex), 18 producten — binaire upload (vóór cloud-regel).
- PE putten (26) en Petry ladders (54) — via cloud-link (jsDelivr). Repo `Devooght/techsheets`.
