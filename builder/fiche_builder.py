#!/usr/bin/env python3
"""
Devooght fiche-generator (huisstijl, tweetalig).

JSON  ->  gepolijste technische fiche (PDF), 1 pagina per taal.
Vaste huisstijl: logo + Devooght-blauwen + lettertype Montserrat
(drop Mark-*.ttf in assets/fonts/ en zet FONT_FAMILY='Mark' om naar het
officiele bedrijfslettertype te wisselen).

Gebruik:
    python3 fiche_builder.py product.json --out TF_Product.pdf

JSON-structuur (taalblokken nl/fr; voeg/laat weg naar wens):
{
  "code": "CABO",                       # optioneel: referentie/artikelcode
  "image": "assets/foto.png",           # productfoto (optioneel)
  "revision": "2026-06-17",             # optioneel, default vandaag
  "nl": {
    "label": "Technische fiche",
    "title": "Caboflex - PE kabelbeschermingsbuis",
    "subtitle": "Wachtdarm - dubbelwandig PE - EN 50086-2-4",
    "intro": "Korte beschrijving ...",
    "highlights": [["Norm","EN 50086-2-4"], ["Slagvastheid","15-40 J"]],
    "specs": {"header": ["Kenmerk","Waarde"], "rows": [["Ø 40","..."]]},
    "applications": ["Toepassing 1", "Toepassing 2"]
  },
  "fr": { ... }
}
"""
from __future__ import annotations
import argparse, base64, datetime, html, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FONT_FAMILY = "Montserrat"   # zet op "Mark" als de Mark-*.ttf in assets/fonts staan

# ---- Devooght huisstijl ----------------------------------------------------
C_BLUE_DARK  = "#274472"
C_BLUE       = "#2a508d"
C_BLUE_LIGHT = "#1e8fce"
C_GREY       = "#e3ebf2"
C_INK        = "#1b2733"
C_MUTED      = "#6b7888"

MONTHS = None  # niet nodig


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _img_data_uri(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    mt = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "image/png")
    return f"data:{mt};base64,{_b64(path)}"


def _font_face() -> str:
    """Bouw @font-face. Mark (5 statische gewichten) of Montserrat (variabel)."""
    fdir = ASSETS / "fonts"
    if FONT_FAMILY == "Mark":
        weights = {"Mark-Light":300, "Mark-Regular":400, "Mark-Medium":500, "Mark-Bold":700, "Mark-Black":800}
        faces = []
        for fname, wght in weights.items():
            f = fdir / f"{fname}.ttf"
            if f.exists():
                faces.append(f"@font-face{{font-family:'Mark';src:url('{_img_font(f)}');font-weight:{wght};font-style:normal;}}")
        return "\n".join(faces)
    # Montserrat variabel
    f = fdir / "Montserrat.ttf"
    return f"@font-face{{font-family:'Montserrat';src:url('file://{f.resolve()}');font-weight:100 900;font-style:normal;}}"


def _img_font(path: Path) -> str:
    return f"data:font/ttf;base64,{_b64(path)}"


def _qr_data_uri(url: str) -> str:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="#274472", back_color="white").convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _highlights(items) -> str:
    if not items:
        return ""
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="hl"><div class="hl-l">{esc(label)}</div>'
            f'<div class="hl-v">{esc(value)}</div></div>'
        )
    return f'<div class="highlights">{"".join(cards)}</div>'


def _specs(specs) -> str:
    if not specs or not specs.get("rows"):
        return ""
    hdr = specs.get("header", ["Kenmerk", "Waarde"])
    thead = "".join(f'<th>{esc(h)}</th>' for h in hdr)
    body = []
    for r in specs["rows"]:
        cells = "".join(
            (f'<td class="k">{esc(c)}</td>' if i == 0 else f'<td>{esc(c)}</td>')
            for i, c in enumerate(r)
        )
        body.append(f"<tr>{cells}</tr>")
    return (
        f'<table class="specs"><thead><tr>{thead}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


def _applications(items, heading) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{esc(x)}</li>" for x in items)
    return f'<div class="apps"><div class="sec-h">{esc(heading)}</div><ul>{lis}</ul></div>'


APP_HEADINGS = {"nl": "Toepassingen", "fr": "Applications", "en": "Applications"}
DESC_HEADINGS = {"nl": "Beschrijving", "fr": "Description", "en": "Description"}
SPEC_HEADINGS = {"nl": "Technische gegevens", "fr": "Données techniques", "en": "Technical data"}
REV_LABEL = {"nl": "Laatste revisie", "fr": "Dernière révision", "en": "Last revision"}
DISCLAIMER = {
    "nl": "Onder voorbehoud van fouten. Deze technische fiche werd met behulp van artificiële intelligentie (AI) opgesteld.",
    "fr": "Sous réserve d'erreurs. Cette fiche technique a été établie à l'aide de l'intelligence artificielle (IA).",
    "en": "Subject to errors. This technical data sheet was produced with the help of artificial intelligence (AI).",
}
MOREINFO = {"nl": "Meer info", "fr": "Plus d'infos", "en": "More info"}


def _page(lang: str, blk: dict, *, code: str, img_uri: str, rev: str, logo_uri: str, logo_rev_uri: str, qr_uri: str = "") -> str:
    label = blk.get("label") or {"nl": "Technische fiche", "fr": "Fiche technique", "en": "Technical data sheet"}[lang]
    title = blk.get("title", "")
    subtitle = blk.get("subtitle", "")
    intro = blk.get("intro", "")
    desc_block = ""
    if intro:
        desc_block = (
            f'<div class="desc"><div class="sec-h">{DESC_HEADINGS.get(lang,"Beschrijving")}</div>'
            f'<p>{esc(intro)}</p></div>'
        )
    photo = f'<div class="photo"><img src="{img_uri}"></div>' if img_uri else ""
    code_chip = f'<div class="ref">Ref. {esc(code)}</div>' if code else ""
    spec_head = SPEC_HEADINGS.get(lang, "Technische gegevens")
    specs_block = _specs(blk.get("specs"))
    if specs_block:
        specs_block = f'<div class="sec-h">{spec_head}</div>' + specs_block

    disclaimer = esc(DISCLAIMER.get(lang, ""))
    rev_label = REV_LABEL.get(lang, "Revisie")
    rev_v = esc(rev)
    qr_block = (
        f'<div class="ft-qr"><img src="{qr_uri}"><span>{esc(MOREINFO.get(lang,"Meer info"))}</span></div>'
        if qr_uri else ""
    )
    return f'''
<section class="page">
  <div class="accent"></div>
  <header class="hd">
    <img class="logo" src="{logo_uri}">
    <div class="hd-r">
      <div class="chip">{esc(label)}</div>
      {code_chip}
    </div>
  </header>

  <div class="hero">
    <div class="hero-t">
      <h1>{esc(title)}</h1>
      <div class="sub">{esc(subtitle)}</div>
    </div>
    {photo}
  </div>

  {desc_block}
  {_highlights(blk.get("highlights"))}

  <div class="body">
    <div class="col-main">{specs_block}</div>
    <div class="col-side">{_applications(blk.get("applications"), APP_HEADINGS.get(lang,"Toepassingen"))}</div>
  </div>

  <footer class="ft">
    <div class="disc">{disclaimer}</div>
    <div class="ft-row">
      <img class="ft-logo" src="{logo_rev_uri}">
      <div class="ft-c">
        Devooght bv &nbsp;·&nbsp; Delaeystraat 48, 8830 Hooglede &nbsp;·&nbsp; 051 70 55 20<br>
        hooglede@devoplast.com &nbsp;·&nbsp; www.devoplast.com &nbsp;·&nbsp; BE 0474 574 478
        <div class="ft-rev">{rev_label}: <b>{rev_v}</b></div>
      </div>
      {qr_block}
    </div>
  </footer>
</section>'''


def build_html(data: dict) -> str:
    code = data.get("code", "")
    rev_raw = data.get("revision")
    if rev_raw:
        try:
            rev = datetime.date.fromisoformat(rev_raw).strftime("%d/%m/%Y")
        except ValueError:
            rev = rev_raw
    else:
        rev = datetime.date.today().strftime("%d/%m/%Y")
    img_uri = _img_data_uri(Path(data["image"])) if data.get("image") else ""
    if data.get("image") and not Path(data["image"]).is_absolute():
        p = (HERE / data["image"])
        img_uri = _img_data_uri(p) if p.exists() else _img_data_uri(Path(data["image"]))
    logo_uri = _img_data_uri(ASSETS / "logo.png")
    logo_rev_uri = _img_data_uri(ASSETS / "logo_reverse.png")

    qr_uri = _qr_data_uri(data["qr_url"]) if data.get("qr_url") else ""
    only = data.get("_only_lang")
    langs = [l for l in ("nl", "fr", "en") if l in data and (not only or l == only)]
    pages = "".join(
        _page(l, data[l], code=code, img_uri=img_uri, rev=rev,
              logo_uri=logo_uri, logo_rev_uri=logo_rev_uri, qr_uri=qr_uri)
        for l in langs
    )
    css = CSS.format(
        FF=FONT_FAMILY, BD=C_BLUE_DARK, B=C_BLUE, BL=C_BLUE_LIGHT,
        GREY=C_GREY, INK=C_INK, MUTED=C_MUTED, FONTFACE=_font_face(),
    )
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{pages}</body></html>"


CSS = """
{FONTFACE}
@page {{ size: A4; margin: 0; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'{FF}', Arial, sans-serif; color:{INK}; }}
.page {{ width:210mm; height:297mm; position:relative; padding:0 0 30mm 0;
         page-break-after:always; overflow:hidden; }}
.page:last-child {{ page-break-after:auto; }}
.accent {{ height:5mm; background:linear-gradient(90deg,{BD} 0%,{B} 45%,{BL} 100%); }}

.hd {{ display:flex; align-items:center; justify-content:space-between;
       padding:8mm 15mm 5mm 15mm; }}
.logo {{ height:13mm; }}
.hd-r {{ text-align:right; }}
.chip {{ display:inline-block; background:{BL}; color:#fff; font-weight:700;
         font-size:8.2pt; letter-spacing:2.5px; text-transform:uppercase;
         padding:5px 13px; border-radius:30px; }}
.ref {{ margin-top:5px; font-size:8pt; color:{MUTED}; font-weight:600; letter-spacing:.5px; }}

.hero {{ margin:2mm 15mm 0 15mm; background:{GREY}; border-radius:10px;
         padding:7mm 8mm; display:flex; align-items:center; gap:7mm;
         min-height:40mm; }}
.hero-t {{ flex:1; }}
.hero h1 {{ font-size:23pt; font-weight:800; color:{BD}; line-height:1.04; letter-spacing:-.3px; }}
.hero .sub {{ margin-top:3.5mm; font-size:10.5pt; font-weight:600; color:{B}; line-height:1.3; }}
.photo {{ width:54mm; height:40mm; background:#fff; border-radius:8px; padding:2.5mm;
          box-shadow:0 2px 10px rgba(39,68,114,.12); flex:none; }}
.photo img {{ width:100%; height:100%; object-fit:cover; border-radius:5px; }}

.sec-h {{ font-size:10.5pt; font-weight:800; color:{BD}; text-transform:uppercase;
          letter-spacing:1px; margin:0 0 3mm 0; padding-left:10px;
          border-left:4px solid {BL}; line-height:1; }}
.desc {{ margin:7mm 15mm 0 15mm; }}
.desc p {{ font-size:9.6pt; line-height:1.55; color:#33414f; }}

.highlights {{ display:flex; gap:5mm; margin:6mm 15mm 0 15mm; }}
.hl {{ flex:1; background:#fff; border:1px solid {GREY}; border-top:3px solid {BL};
       border-radius:7px; padding:4mm 4mm; }}
.hl-l {{ font-size:7.6pt; font-weight:700; color:{MUTED}; text-transform:uppercase; letter-spacing:.8px; }}
.hl-v {{ font-size:10pt; font-weight:700; color:{BD}; margin-top:2mm; line-height:1.25; }}

.body {{ display:flex; gap:8mm; margin:7mm 15mm 0 15mm; }}
.col-main {{ flex:1.45; }}
.col-side {{ flex:1; }}

table.specs {{ width:100%; border-collapse:collapse; font-size:8.9pt;
               border-radius:7px; overflow:hidden; }}
table.specs thead th {{ background:{BD}; color:#fff; text-align:left; font-weight:700;
                        padding:6px 10px; font-size:8.4pt; letter-spacing:.4px; }}
table.specs tbody td {{ padding:5.5px 10px; border-bottom:1px solid {GREY}; }}
table.specs tbody td.k {{ font-weight:700; color:{B}; white-space:nowrap; }}
table.specs td, table.specs th {{ white-space:nowrap; }}
table.specs td:nth-child(n+4) {{ font-weight:600; color:{BD}; }}
table.specs tbody tr:nth-child(even) {{ background:#f4f8fc; }}

.apps ul {{ list-style:none; }}
.apps li {{ position:relative; padding-left:20px; margin-bottom:3mm;
            font-size:9.2pt; line-height:1.35; color:#33414f; }}
.apps li:before {{ content:""; position:absolute; left:0; top:3px; width:11px; height:11px;
                   border-radius:50%; background:{BL};
                   box-shadow:inset 0 0 0 2px #fff, 0 0 0 1px {BL}; }}

.ft {{ position:absolute; left:0; right:0; bottom:0; background:{BD}; color:#cdd9ea; }}
.disc {{ font-size:6.7pt; font-style:italic; color:#8ea3c4; text-align:center;
         padding:2.6mm 15mm 0 15mm; line-height:1.3; }}
.ft-row {{ display:flex; align-items:center; gap:7mm; padding:3mm 15mm 4mm 15mm; }}
.ft-logo {{ height:8.5mm; flex:none; filter:brightness(0) invert(1); opacity:.95; }}
.ft-c {{ flex:1; font-size:7.6pt; line-height:1.5; letter-spacing:.2px; }}
.ft-rev {{ margin-top:1mm; font-size:7.2pt; color:#9fb4d2; }}
.ft-rev b {{ color:#fff; }}
.ft-qr {{ flex:none; text-align:center; }}
.ft-qr img {{ width:15mm; height:15mm; background:#fff; padding:1mm; border-radius:4px; display:block; }}
.ft-qr span {{ display:block; margin-top:1mm; font-size:6.6pt; color:#cdd9ea; letter-spacing:.4px; }}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--html", action="store_true", help="schrijf ook .html")
    ap.add_argument("--lang", default=None, help="render enkel deze taal (nl/fr/en)")
    args = ap.parse_args()
    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    if args.lang:
        data["_only_lang"] = args.lang
    out = Path(args.out) if args.out else Path(args.json).with_suffix(".pdf")
    html_str = build_html(data)
    if args.html:
        out.with_suffix(".html").write_text(html_str, encoding="utf-8")
    from weasyprint import HTML
    HTML(string=html_str, base_url=str(HERE)).write_pdf(str(out))
    print("PDF:", out)


if __name__ == "__main__":
    main()
