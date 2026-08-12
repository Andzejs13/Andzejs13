# Fotoattēlu un video kārtotājs

Šajā repozitorijā ir neliels rīks, kas atrod fotoattēlus un video norādītajā
mapē un sakārto tos pēc faila tipa un uzņemšanas/modificēšanas mēneša:

```text
sakartots/
├── atteli/2026-08/
└── video/2026-08/
```

## Lietošana

Vispirms apskati plānotās izmaiņas (faili vēl netiek pārvietoti):

```bash
python3 organize_media.py /ceļš/uz/failiem
```

Kad plāns ir pārbaudīts, pārvieto failus:

```bash
python3 organize_media.py /ceļš/uz/failiem --apply
```

Rezultāta mapi var norādīt ar `--output`. Ja vienāda nosaukuma fails jau
pastāv, rīks tam droši pievieno numuru, piemēram, `bilde_1.jpg`. Citi failu
tipi netiek mainīti.

Atbalstīti biežākie attēlu formāti (`jpg`, `png`, `gif`, `webp`, `heic`,
`tiff`, `bmp`, `svg`, `avif`, `raw`) un video formāti (`mp4`, `mov`, `avi`,
`mkv`, `webm`, `m4v`, `mpeg`, `mpg`, `3gp`).

## Pārbaudes

```bash
python3 -m unittest discover -s tests -v
```
