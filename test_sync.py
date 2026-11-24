import unittest
from unittest.mock import patch
import io
import json
import os
import sys
import tempfile
from pathlib import Path
import sync_stars as s
import summarize_stars as ai
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

    def test_only_new_active_ids_without_manual_summary_are_queued(self):
        new = s.merge([], [self.item()], 'day1')
        self.assertEqual(ai.pending_records(new, {}), new)
        for key in ('1', 'demo/tool'):
            self.assertFalse(ai.pending_records(new, {key: {'summary': '手写简介'}}))
        self.assertFalse(ai.pending_records(s.merge(new, [], 'day2'), {}))
        legacy = dict(new[0])
        del legacy['ai_summary']
        self.assertFalse(ai.pending_records(s.merge([legacy], [self.item()], 'day2'), {}))

    def test_summary_survives_rename_and_manual_note_takes_priority(self):
        records = s.merge([], [self.item()], 'day1')
        records[0]['ai_summary'] = '根据文档生成的简介。'
        records = s.merge(records, [self.item('demo/renamed')], 'day2')
        self.assertFalse(ai.pending_records(records, {}))
        self.assertEqual(s.enrich(records, {})[0]['summary'], '根据文档生成的简介。')
        self.assertEqual(s.enrich(records, {'1': {'summary': '我的简介'}})[0]['summary'], '我的简介')

    def test_readme_to_views_and_transient_failure(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(s, 'ROOT', Path(tmp)):
            records = s.merge([], [self.item()], 'day1')
            state = {'records': records, 'last_sync': 'day1'}
            path = s.ROOT / 'stars.json'
            with patch.object(ai, 'readme_excerpt', side_effect=TimeoutError('timeout')):
                ai.summarize(state, path, records, None)
            self.assertEqual(ai.pending_records(records, {}), records)
            with patch('urllib.request.urlopen', return_value=io.BytesIO(b'A local search tool.')), \
                 patch.object(ai, 'HTTPSConnection') as connect:
                connection = connect.return_value
                response = connection.getresponse.return_value
                response.status = 200
                response.read.return_value = json.dumps({'choices': [
                    {'message': {'content': '可以在本地搜索文件。'}, 'finish_reason': 'stop'}]}).encode()
                ai.summarize(state, path, records, 'test-only-credential')
            connect.assert_called_once_with('relay.tuyoo.com', timeout=35)
            args, kwargs = connection.request.call_args
            self.assertEqual(args, ('POST', '/v1/chat/completions'))
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-only-credential')
            body = json.loads(kwargs['body'])
            self.assertEqual(body['model'], 'gpt-6.2-sol')
            self.assertEqual(json.loads(body['messages'][1]['content']),
                             {'repository': 'demo/tool', 'README': 'A local search tool.'})
            self.assertNotIn(b'test-only-credential', kwargs['body'])
            saved = json.loads(path.read_text(encoding='utf8'))['records']
            s.render(saved, 'day1', 'owner')
            for filename in ('INBOX.md', 'INDEX.md', 'search.html'):
                self.assertIn('可以在本地搜索文件。', (s.ROOT/filename).read_text(encoding='utf8'))
            self.assertFalse(ai.pending_records(saved, {}))
            state['records'] = s.merge(saved, [self.item('demo/renamed', 'New upstream description')], 'day2')
            path.write_text(json.dumps(state), encoding='utf8')
            with patch.object(sys, 'argv', ['summarize_stars.py']), patch.dict(os.environ, AI_API_KEY='test-only'), \
                 patch.object(ai, 'readme_excerpt') as readme, patch.object(ai, 'HTTPSConnection') as relay:
                ai.main()
            readme.assert_not_called()
            relay.assert_not_called()
            self.assertEqual(state['records'][0]['ai_summary'], '可以在本地搜索文件。')

    def test_missing_readme_falls_back_without_requeuing(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = s.merge([], [self.item()], 'day1')
            with patch.object(ai, 'readme_excerpt', return_value=''):
                ai.summarize({'records': records}, Path(tmp)/'stars.json', records, None)
            self.assertFalse(ai.pending_records(s.merge(records, [self.item()], 'day2'), {}))
            self.assertEqual(records[0]['description'], 'local-llm tool')

    def test_invalid_model_output_is_not_saved(self):
        for text, reason in [('资料不足。', 'stop'), ('An English sentence.', 'stop'),
                             ('可以搜索文件', 'length'), ('泄漏 test-only-credential。', 'stop')]:
            with self.subTest(text=text), patch.object(ai, 'HTTPSConnection') as connect:
                response = connect.return_value.getresponse.return_value
                response.status = 200
                response.read.return_value = json.dumps({'choices': [
                    {'message': {'content': text}, 'finish_reason': reason}]}).encode()
                with self.assertRaises(ValueError):
                    ai.generate_summary('test-only-credential', 'demo/tool', 'file search')

    def test_incomplete_summaries_have_a_bounded_retry_count(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ai, 'readme_excerpt', return_value='overview'), \
             patch.object(ai, 'generate_summary', side_effect=TimeoutError) as relay:
            records = []
            for day in range(5):
                records = s.merge(records, [self.item()], str(day))
                ai.summarize({'records': records}, Path(tmp)/'stars.json', ai.pending_records(records, {}), 'test-only')
            self.assertEqual(relay.call_count, ai.MAX_ATTEMPTS)
            self.assertIsNone(records[0]['ai_summary'])

    def test_gateway_error_stops_batch_without_leaking_reply(self):
        records = s.merge([], [self.item()], 'day1')
        pending = [records[0], dict(records[0], id=2)]
        for code in (302, 401, 429):
            with self.subTest(code=code), patch.object(ai, 'readme_excerpt', return_value='overview'), \
                 patch.object(ai, 'HTTPSConnection') as connect:
                reply = connect.return_value.getresponse.return_value
                reply.status = code
                ai.summarize({'records': pending}, None, pending, 'test-only')
                self.assertEqual(connect.call_count, 1)
                reply.read.assert_not_called()
                self.assertEqual(ai.pending_records(pending, {}), pending)

    def test_missing_key_skips_network_and_per_run_limit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(s, 'ROOT', Path(tmp)):
            repo = s.merge([], [self.item()], 'day1')[0]
            records = [dict(repo, id=i) for i in range(ai.MAX_PER_RUN + 2)]
            state = {'records': records}
            path = s.ROOT / 'stars.json'
            path.write_text(json.dumps(state), encoding='utf8')
            with patch.object(sys, 'argv', ['summarize_stars.py']), patch.dict(os.environ, AI_API_KEY=''), \
                 patch.object(ai, 'readme_excerpt') as readme:
                ai.main()
            readme.assert_not_called()
            with patch.object(ai, 'readme_excerpt', return_value='overview'), \
                 patch.object(ai, 'generate_summary', return_value='可以搜索文件。') as relay:
                ai.summarize(state, path, records, 'test-only')
            self.assertEqual(relay.call_count, ai.MAX_PER_RUN)
            self.assertEqual(len(ai.pending_records(records, {})), 2)

    def test_readme_prefers_project_overview_to_usage_example(self):
        overview = 'A cross-browser 3D library for rendering scenes with JavaScript, supporting WebGL and WebGPU.'
        readme = (overview + '\n\n### Usage\nCreate a rotating cube in this example.').encode()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(readme)):
            self.assertEqual(ai.readme_excerpt('demo/tool'), overview)
if __name__=='__main__': unittest.main()
