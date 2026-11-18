import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import sync_stars as s
class Tests(unittest.TestCase):
    def item(self, name='demo/tool', description='local-llm tool'):
        return {'starred_at':'2026-01-01T00:00:00Z','repo':{'id':1,'full_name':name,'description':description,'topics':['llm'],'private':False}}
    def test_merge_and_rename(self):
        a=s.merge([], [self.item()], 'first')
        b=s.merge(a, [self.item('demo/renamed')], 'second')
        self.assertEqual(b[0]['first_seen'],'first');self.assertEqual(len(b),1)
        self.assertFalse(s.merge(b, [], 'third')[0]['active'])
    def test_no_duplicates(self):
        self.assertEqual(len(s.merge([], [self.item(),self.item()], 'now')),1)
    def test_private_excluded(self):
        r=self.item();r['repo']['private']=True
        self.assertEqual(s.merge([], [r], 'now'),[])
    def test_notes_and_safe_html(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(s,'ROOT',Path(tmp)):
            note='{"1":{"summary":"我自己的笔记","categories":["自定义"],"reviewed":true}}'
            (s.ROOT/'notes.json').write_text(note,encoding='utf8')
            records=s.merge([], [self.item(description='</script><script>alert(1)</script>')], 'now')
            s.render(records,'now','test')
            self.assertEqual((s.ROOT/'notes.json').read_text(encoding='utf8'),note)
            self.assertNotIn('</script><script>alert(1)',(s.ROOT/'search.html').read_text(encoding='utf8'))
            self.assertIn('共 0 项',(s.ROOT/'INBOX.md').read_text(encoding='utf8'))
            self.assertIn('自定义',(s.ROOT/'INDEX.md').read_text(encoding='utf8'))
    def test_invalid_notes_fail(self):
        with self.assertRaises(ValueError):s.enrich(s.merge([], [self.item()], 'now'), {'1':{'categories':'bad'}})
if __name__=='__main__': unittest.main()
