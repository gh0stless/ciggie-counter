"""Baut com_ciggiecounter: Bilder verkleinern (media/img) und das Joomla-Paket packen.

    python website/build.py   ->  website/Output/com_ciggiecounter.zip

ZIP mit Vorwärts-Schrägstrichen (Joomlas Installer auf Linux), siehe Desktop-Cat-BuildPackage.ps1.
"""
import os
import zipfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COM = os.path.join(HERE, 'com_ciggiecounter')
IMG = os.path.join(COM, 'media', 'img')

# Ziel-Name: (Quelle, größte Kante)
IMAGES = {
    'buttbin-hero.jpg': ('design/fotoshooting/01_held.jpg', 900),
    'buttbin-colours.jpg': ('design/fotoshooting/15_vergleich_oben.jpg', 1400),
}
for lang in ('de', 'en'):
    for n in (1, 2, 3, 4, 5):
        IMAGES[f'app-{lang}-{n}.jpg'] = (f'design/screenshots/{lang}_{n}.png', 900)
# nextcloud_de_4 zeigt eine interne Adresse: nicht verwenden
IMAGES['nextcloud-1.jpg'] = ('design/screenshots/nextcloud_de_1.png', 900)


def trim_white(im, margin=0.06):
    """Renders have wide white margins: crop to the object plus a small border."""
    from PIL import ImageChops
    # ignore a thin frame: some renders have grey specks in the corners
    e = int(min(im.size) * 0.02)
    im = im.crop((e, e, im.width - e, im.height - e))
    box = ImageChops.difference(im, Image.new('RGB', im.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 110 else 0).getbbox()
    if not box:
        return im
    m = int(max(box[2] - box[0], box[3] - box[1]) * margin)
    return im.crop((max(box[0] - m, 0), max(box[1] - m, 0), min(box[2] + m, im.width), min(box[3] + m, im.height)))


def images():
    os.makedirs(IMG, exist_ok=True)
    for name, (src, edge) in IMAGES.items():
        im = Image.open(os.path.join(ROOT, src)).convert('RGB')
        if name.startswith('buttbin'):
            im = trim_white(im)
        im.thumbnail((edge, edge), Image.LANCZOS)
        im.save(os.path.join(IMG, name), 'JPEG', quality=82, optimize=True, progressive=True)


def package():
    out = os.path.join(HERE, 'Output')
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'com_ciggiecounter.zip')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(COM):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, COM).replace(os.sep, '/'))
    print(path, os.path.getsize(path), 'Bytes')


if __name__ == '__main__':
    images()
    package()
