import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from traceproof.lineage import compare, scan, image_hash, image_distance


class ImageLineageTests(unittest.TestCase):
    def test_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.png'; b=Path(d)/'b.jpg'
            im=Image.new('RGB',(128,128),'white')
            dr=ImageDraw.Draw(im)
            dr.rectangle((5,5,60,110),fill='black')
            dr.ellipse((70,30,115,80),fill='gray')
            im.save(a); im.save(b,quality=95)
            result=compare(a,b)
            self.assertEqual(result['relation'],'image_similarity_candidate')
            self.assertLessEqual(result['image_hamming_distance'],6)
            self.assertEqual(scan(d)['edges'][0]['relation'],'image_similarity_candidate')

    def test_exact_images(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.png'; b=Path(d)/'b.png'
            Image.new('RGB',(20,20),'red').save(a)
            b.write_bytes(a.read_bytes())
            self.assertEqual(compare(a,b)['relation'],'byte_identical')

    def test_distance(self):
        self.assertEqual(image_distance('0000000000000000','ffffffffffffffff'),64)

    def test_invalid_image(self):
        self.assertIsNone(image_hash(b'not an image'))


if __name__=='__main__': unittest.main()