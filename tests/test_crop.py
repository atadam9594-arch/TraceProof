import tempfile
import unittest
from pathlib import Path
from traceproof.lineage import compare,scan
try:
    from PIL import Image,ImageDraw
except ImportError:
    Image=None

@unittest.skipIf(Image is None,'Pillow optional dependency absent')
class CropTests(unittest.TestCase):
    def test_cropped_variant(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'source.png';b=Path(d)/'crop.png'
            im=Image.new('RGB',(300,300),'white');draw=ImageDraw.Draw(im)
            for i in range(25):
                draw.rectangle((i*11,i*7,i*11+12,i*7+40),fill=(i*7%255,i*11%255,i*17%255))
            im.save(a)
            im.crop((45,45,255,255)).save(b)
            result=compare(a,b)
            self.assertIn(result['relation'],('image_crop_candidate','image_similarity_candidate'))
            self.assertNotIn('image_crop_hashes',result['left'])
            self.assertTrue(any(x['relation'] in ('image_crop_candidate','image_similarity_candidate') for x in scan(d)['edges']))
    def test_nonimage(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.txt';b=Path(d)/'b.txt'
            a.write_text('alpha');b.write_text('beta')
            self.assertIsNone(compare(a,b)['crop_hamming_distance'])