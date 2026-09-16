import unittest
import numpy as np
from app.analysis.text import compare, tokens
from app.analysis.audio import quality, pitch_summary
from app.analysis.scoring import score

class TextTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(tokens("It's modern—technology!"), ["it's", "modern", "technology"])
    def test_omission(self):
        r=compare('the modern technology works', 'the technology works')
        self.assertEqual(r['counts']['omission'], 1)
        self.assertEqual(r['counts']['match'], 3)
    def test_substitution(self):
        self.assertEqual(compare('three cats', 'free cats')['counts']['substitution'],1)
    def test_repetition(self):
        r=compare('the cat runs', 'the the cat runs')
        self.assertEqual(r['counts']['insertion'],1)
        self.assertEqual(len(r['repetitions']),1)
    def test_empty(self):
        self.assertEqual(compare('one two','')['counts']['omission'],2)
    def test_order_not_full_credit(self):
        self.assertGreater(compare('cats chase mice','mice chase cats')['wer'],0)

class AudioTests(unittest.TestCase):
    def test_silence(self):
        self.assertFalse(quality(np.zeros(16000),16000)['usable'])
    def test_clipping(self):
        self.assertFalse(quality(np.ones(16000),16000)['usable'])
    def test_pitch(self):
        y=.2*np.sin(2*np.pi*180*np.arange(16000)/16000)
        p=pitch_summary(y,16000)
        self.assertAlmostEqual(p['median_hz'],180,delta=6)

class ScoreTests(unittest.TestCase):
    def features(self):
        return {'wpm':140,'internal_silence_ratio':.1,'abnormal_pause_count':0,'repetition_count':0,'word_count':20,'utterance_span':10}
    def test_missing_pronunciation_not_faked(self):
        s=score(compare('one two','one two'),self.features(),None)
        self.assertIsNone(s['pronunciation']['value'])
        self.assertIsNone(s['prosody']['value'])
        self.assertLess(s['coverage'],1)
        self.assertEqual(s['content']['value'],100)
        self.assertTrue(s['fluency']['evidence'])
    def test_pause_penalty_monotonic(self):
        f=self.features(); base=score(compare('one','one'),f,None)
        f['abnormal_pause_count']=4
        bad=score(compare('one','one'),f,None)
        self.assertLess(bad['fluency']['value'],base['fluency']['value'])
    def test_missing_text_not_perfect(self):
        self.assertEqual(score(compare('one two',''),self.features(),None)['content']['value'],0)

if __name__=='__main__': unittest.main()

class MissingAlignmentTests(unittest.TestCase):
    def test_missing_alignment_does_not_imply_fluent(self):
        f={'wpm':140,'internal_silence_ratio':.1,'abnormal_pause_count':0,'repetition_count':0,'word_count':20,'utterance_span':10,'word_mapping_valid':False}
        result=score(compare('one two','one two'),f,None)
        self.assertIsNone(result['fluency']['value'])
