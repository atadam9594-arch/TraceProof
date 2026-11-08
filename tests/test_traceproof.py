import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from traceproof.core import (new_case, append_event, replay, validate_case, evaluate, canonical,
                              describe_file, sniff_type, InvalidCase, sha)
from traceproof.bundle import make_bundle, verify_bundle, create_keypair


class EventTests(unittest.TestCase):
    def setUp(self):
        self.c = new_case('Example source investigation')
        self.art = {'id':'a1','name':'sample.png','sha256':'a'*64,'size':12,'media_type':'image/png'}
        self.claim = {'id':'c1','statement':'The file is authentic','kind':'authorship'}

    def test_case_empty_valid(self):
        self.assertTrue(validate_case(self.c))
        self.assertEqual(len(self.c['events']),1)
    def test_case_schema(self):
        self.assertEqual(self.c['format'],'traceproof.case.v3')
    def test_replay(self):
        self.c=append_event(self.c,'artifact_added',self.art)
        self.assertEqual(replay(self.c['events']),self.c['state'])
    def test_first_chain_genesis(self):
        self.assertEqual(self.c['events'][0]['previous'],'0'*64)
    def test_bad_event_hash(self):
        self.c['events'][0]['hash']='0'*64
        with self.assertRaises(InvalidCase):validate_case(self.c)
    def test_bad_previous(self):
        self.c=append_event(self.c,'artifact_added',self.art)
        self.c['events'][1]['previous']='0'*64
        with self.assertRaises(InvalidCase):validate_case(self.c)
    def test_modified_content(self):
        self.c['events'][0]['payload']['subject']='tampered'
        with self.assertRaises(InvalidCase):validate_case(self.c)
    def test_modified_snapshot(self):
        self.c['state']['subject']='tampered'
        with self.assertRaises(InvalidCase):validate_case(self.c)
    def test_removed_event(self):
        self.c=append_event(self.c,'artifact_added',self.art)
        self.c['events'].pop()
        with self.assertRaises(InvalidCase):validate_case(self.c)
    def test_unknown_action(self):
        with self.assertRaises(InvalidCase):append_event(self.c,'sudo',{})
    def test_duplicate_artifact(self):
        self.c=append_event(self.c,'artifact_added',self.art)
        with self.assertRaises(InvalidCase):append_event(self.c,'artifact_added',self.art)
    def test_invalid_hash(self):
        a=dict(self.art,sha256='fakehash')
        with self.assertRaises(InvalidCase):append_event(self.c,'artifact_added',a)
    def test_invalid_size_bool(self):
        a=dict(self.art,size=True)
        with self.assertRaises(InvalidCase):append_event(self.c,'artifact_added',a)
    def test_invalid_id(self):
        a=dict(self.art,id='../bad')
        with self.assertRaises(InvalidCase):append_event(self.c,'artifact_added',a)
    def test_invalid_claim_kind(self):
        with self.assertRaises(InvalidCase):append_event(self.c,'claim_added',dict(self.claim,kind='unknown'))
    def test_unknown_claim(self):
        with self.assertRaises(InvalidCase):append_event(self.c,'observation_added',{'id':'o1','claim_id':'no','artifact_id':None,'source':'me','state':'supports','trust':'contextual','details':{}})
    def test_invalid_cryptographic_self_assertion(self):
        self.c=append_event(self.c,'claim_added',self.claim)
        with self.assertRaises(InvalidCase):append_event(self.c,'observation_added',{'id':'o1','claim_id':'c1','artifact_id':None,'source':'me','state':'supports','trust':'cryptographic','details':{}})
    def test_report_attached_by_digest(self):
        rep={'id':'r1','name':'legacy.json','summary':'External and unverified','sha256':'b'*64}
        self.c=append_event(self.c,'report_attached',rep)
        self.assertEqual(self.c['state']['reports'][0],rep)
    def test_eval_no_claim(self):
        self.assertEqual(evaluate(self.c)['overall'],'unresolved')
    def test_eval_unresolved(self):
        self.c=append_event(self.c,'claim_added',self.claim)
        r=evaluate(self.c)['claim_results'][0]
        self.assertEqual(r['status'],'unresolved')
        self.assertIn('verifiable signed',str(r['missing']))
    def test_eval_support_not_verified(self):
        self.c=append_event(self.c,'claim_added',self.claim)
        self.c=append_event(self.c,'observation_added',{'id':'o1','claim_id':'c1','artifact_id':None,'source':'me','state':'supports','trust':'contextual','details':{}})
        self.assertEqual(evaluate(self.c)['claim_results'][0]['status'],'supported_contextually')
    def test_eval_conflicting(self):
        self.c=append_event(self.c,'claim_added',self.claim)
        for id_,s in [('o1','supports'),('o2','contradicts')]:
            self.c=append_event(self.c,'observation_added',{'id':id_,'claim_id':'c1','artifact_id':None,'source':'analyst','state':s,'trust':'contextual','details':{}})
        r=evaluate(self.c)['claim_results'][0]
        self.assertEqual(r['status'],'contested')
        self.assertEqual(evaluate(self.c)['overall'],'unresolved')
        self.assertIn('Resolve conflicting',str(r['missing']))
    def test_unicode(self):
        c=new_case('مرحبا İstanbul 日本語')
        self.assertTrue(validate_case(c))
    def test_empty_subject(self):
        with self.assertRaises(InvalidCase):new_case('')
    def test_unexpected_payload(self):
        with self.assertRaises(InvalidCase):append_event(self.c,'artifact_added',dict(self.art,admin=True))
    def test_case_past_events_not_mutated(self):
        prior=canonical(self.c)
        append_event(self.c,'artifact_added',self.art)
        self.assertEqual(canonical(self.c),prior)


class FileTests(unittest.TestCase):
    def test_magic_png(self):self.assertEqual(sniff_type(b'\x89PNG\r\n\x1a\n' + b'0'*20),'image/png')
    def test_magic_jpeg(self):self.assertEqual(sniff_type(b'\xff\xd8\xff' + b'0'*20),'image/jpeg')
    def test_magic_pdf(self):self.assertEqual(sniff_type(b'%PDF-1.7'),'application/pdf')
    def test_magic_mp4(self):self.assertEqual(sniff_type(b'\0\0\0\x18ftyp'), 'video/mp4-or-quicktime')
    def test_magic_wav(self):self.assertEqual(sniff_type(b'RIFF1234WAVE'), 'audio/wav')
    def test_unknown_magic(self):self.assertEqual(sniff_type(b'abc'), 'application/octet-stream')
    def test_file_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.txt';p.write_bytes(b'abc')
            a=describe_file(p,'a1')
            self.assertEqual(a['sha256'],'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(a['size'],3)
    def test_unavailable_file(self):
        with self.assertRaises(FileNotFoundError):describe_file('___missing_file', 'a1')


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.c = new_case('example')
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)
        self.asset=self.p/'original.bin';self.asset.write_bytes(b'these are the original bytes')
        self.c=append_event(self.c,'artifact_added',describe_file(self.asset,'a1'))

    def tearDown(self):self.tmp.cleanup()
    def test_bundle(self):
        res=verify_bundle(make_bundle(self.c))
        self.assertTrue(res['bundle_valid'])
        self.assertFalse(res['signature_present'])
        self.assertEqual(res['bundled_originals'],0)
        self.assertEqual(res['signer_trust'],'unsigned')
    def test_bundle_has_no_original_by_default(self):
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c))) as z:
            self.assertNotIn('artifacts/a1',z.namelist())
    def test_include_correct_original(self):
        b=make_bundle(self.c,include_files={'a1':self.asset})
        self.assertEqual(verify_bundle(b)['bundled_originals'],1)
    def test_include_wrong_original(self):
        bad=self.p/'changed.bin';bad.write_bytes(b'changed')
        with self.assertRaises(InvalidCase):make_bundle(self.c,include_files={'a1':bad})
    def test_include_unknown_id(self):
        with self.assertRaises(InvalidCase):make_bundle(self.c,include_files={'other':self.asset})
    def test_verify_external_original_correct(self):
        self.assertTrue(verify_bundle(make_bundle(self.c),originals={'a1':self.asset})['external_file_matches']['a1'])
    def test_verify_external_original_mismatch(self):
        bad=self.p/'changed.bin';bad.write_bytes(b'changed')
        r=verify_bundle(make_bundle(self.c),originals={'a1':bad})
        self.assertFalse(r['external_file_matches']['a1'])
        self.assertFalse(r['all_external_matches'])
    def test_bundle_bad_manifest(self):
        blob=make_bundle(self.c)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            data={n:z.read(n) for n in z.namelist()}
        data['manifest.json']=data['manifest.json'].replace(b'traceproof.bundle.v1',b'traceproof.bundle.v0')
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_bundle_bad_event(self):
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c))) as z:data={n:z.read(n) for n in z.namelist()}
        data['case.json']=data['case.json'].replace(b'"subject":"example"',b'"subject":"malice"')
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_bundle_extra_file(self):
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c))) as z:data={n:z.read(n) for n in z.namelist()}
        data['evil.exe']=b'evil'
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_bundle_traversal(self):
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c))) as z:data={n:z.read(n) for n in z.namelist()}
        data['../evil']=b'evil'
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_bundle_duplicate_entry(self):
        blob=io.BytesIO()
        with zipfile.ZipFile(blob,'w') as z:
            z.writestr('case.json',b'{}');z.writestr('case.json',b'{}');z.writestr('manifest.json',b'{}');z.writestr('evaluation.json',b'{}')
        with self.assertRaises(InvalidCase):verify_bundle(blob.getvalue())
    def test_bundle_not_zip(self):
        with self.assertRaises(InvalidCase):verify_bundle(b'NOT ZIP')
    def test_unnatural_manifest(self):
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c))) as z:data={n:z.read(n) for n in z.namelist()}
        manifest=json.loads(data['manifest.json']);data['manifest.json']=json.dumps(manifest,indent=2).encode()
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_signature(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
        except ImportError:self.skipTest('cryptography not installed')
        priv=self.p/'priv.pem';pub=self.p/'pub.pem'
        fingerprint=create_keypair(priv,pub)
        self.assertEqual(len(fingerprint),64)
        result=verify_bundle(make_bundle(self.c,signing_key=priv),trusted_public_key=pub)
        self.assertTrue(result['signature_valid'])
        self.assertEqual(result['signer_trust'],'signature_valid_trusted_key_match')
        if os.name!='nt':self.assertEqual(priv.stat().st_mode & 0o777,0o600)
    def test_signed_but_not_trusted_identity(self):
        priv=self.p/'priv.pem';pub=self.p/'pub.pem';create_keypair(priv,pub)
        result=verify_bundle(make_bundle(self.c,signing_key=priv))
        self.assertEqual(result['signer_trust'],'signature_valid_untrusted_identity')
    def test_wrong_trusted_key(self):
        priv=self.p/'priv.pem';pub=self.p/'pub.pem';create_keypair(priv,pub)
        other=self.p/'other.pem';otherpub=self.p/'otherpub.pem';create_keypair(other,otherpub)
        with self.assertRaises(InvalidCase):verify_bundle(make_bundle(self.c,signing_key=priv),trusted_public_key=otherpub)
    def test_unsigned_trusted_key_required(self):
        priv=self.p/'priv.pem';pub=self.p/'pub.pem';create_keypair(priv,pub)
        with self.assertRaises(InvalidCase):verify_bundle(make_bundle(self.c),trusted_public_key=pub)
    def test_signature_tampering(self):
        priv=self.p/'priv.pem';pub=self.p/'pub.pem';create_keypair(priv,pub)
        with zipfile.ZipFile(io.BytesIO(make_bundle(self.c,signing_key=priv))) as z:data={n:z.read(n) for n in z.namelist()}
        manifest=json.loads(data['manifest.json']);manifest['created_at_local_clock']='2099-01-01'
        data['manifest.json']=canonical(manifest)
        with self.assertRaises(InvalidCase):verify_bundle(self._zip(data))
    def test_keygen_no_overwrite(self):
        priv=self.p/'priv.pem';pub=self.p/'pub.pem';create_keypair(priv,pub)
        with self.assertRaises(FileExistsError):create_keypair(priv,pub)
    def test_large_json_fails(self):
        z=io.BytesIO()
        with zipfile.ZipFile(z,'w') as w:
            w.writestr('case.json',b' '*(5_000_001));w.writestr('evaluation.json',b'{}');w.writestr('manifest.json',b'{}')
        with self.assertRaises(InvalidCase):verify_bundle(z.getvalue())
    @staticmethod
    def _zip(data):
        f=io.BytesIO()
        with zipfile.ZipFile(f,'w') as z:
            for name,blob in data.items():z.writestr(name,blob)
        return f.getvalue()


if __name__ == '__main__':unittest.main()