from importlib.metadata import version,PackageNotFoundError
import json
from app.analysis.audio import decode,quality,speech_regions,pitch_summary,waveform
from app.analysis.text import compare
from app.analysis.features import extract
from app.analysis.scoring import score,RUBRIC
from app.providers.asr import FasterWhisperASR,WhisperXAligner
from app.providers.pronunciation import AzurePronunciation,unavailable
from app.providers.local_pronunciation import LocalPronunciation
from app.coach import coach,enhance

class Pipeline:
    def __init__(self,settings,asr=None,vad=None):
        self.settings=settings;self.asr=asr or FasterWhisperASR(settings);self.vad=vad or speech_regions
        self.aligner=WhisperXAligner(settings.device) if settings.alignment=='whisperx' else None
        self.local_pronunciation=LocalPronunciation(settings.phoneme_model) if settings.pronunciation=='local' else None
    def run(self,source,reference,task_type='read_aloud'):
        y,sr=decode(source,source.with_name('audio.wav'),self.settings.max_seconds)
        q=quality(y,sr);duration=len(y)/sr
        base={'schema_version':2,'task_type':task_type,'quality':q,'duration':duration,'waveform':waveform(y),'scores':None}
        if not q['usable']:return 'rejected',base
        if task_type in {'phoneme','word'}:
            if duration>20:raise ValueError('单词和音标专项每次最多 20 秒，请缩短录音。')
            if not self.local_pronunciation:raise ValueError('请启用本地音素模型后再做专项练习。')
            pron=(self.local_pronunciation.assess_ipa(y,sr,reference) if task_type=='phoneme'
                  else self.local_pronunciation.assess(y,sr,reference))
            # A speech VAD trained on words can reject valid isolated unvoiced fricatives.
            # This branch therefore checks recording quality, but never invents a fluency/content score.
            target=reference.strip('/[] ')
            tip={'θ':'舌尖轻放上下齿之间，让气流从舌齿间通过；再放进 think、three 里练习。',
                 'ð':'舌尖轻触上下齿之间，保持气流并让声带振动；再放进 this、they 里练习。'}.get(target,
                 '先复听音素对照，再把目标放进一个常用单词或短语重新录制。')
            return 'done',{**base,'pronunciation':pron,'warnings':[
                '专项练习不评内容、流利度或 PTE 总分。模型对孤立音素的可靠性低于连续语音，噪声也可能被误识别。'],
                'provenance':{'pronunciation':pron['model'],'asr':'not used for targeted practice'},
                'comparison_signature':task_type+'|'+json.dumps(pron['model'],sort_keys=True),
                'coach':{'source':'target-practice','actions':[{'id':'target-practice','title':'先听，再核对目标发音',
                    'detail':tip,'target':'录 1–3 秒，先发目标音，再另录例词验证。模型提示仅供复听参考。','evidence':['pronunciation.words']}]}}
        regions=self.vad(y,sr)
        if sum(r['end']-r['start'] for r in regions)<.3:
            q['usable']=False;q['reasons'].append('未检测到足够语音，请检查麦克风。');return 'rejected',base
        transcription=self.asr.transcribe(source.with_name('audio.wav'));warnings=[]
        if self.aligner:
            try:transcription=self.aligner.align(source.with_name('audio.wav'),transcription)
            except Exception:
                warnings.append('精对齐不可用，保留 ASR 估计边界。')
        comparison=compare(reference,transcription.text)
        if not comparison['spoken_tokens']:
            q['usable']=False;q['reasons'].append('识别结果为空，无法评分。');return 'rejected',base
        pitch=pitch_summary(y,sr)
        features=extract(duration,regions,transcription.words,comparison,reference,y,sr,pitch)
        pron=unavailable()
        if self.local_pronunciation:
            try:pron=self.local_pronunciation.assess(y,sr,reference,comparison,features['words'])
            except Exception:
                pron=unavailable('本地音素分析未完成，请检查本地模型文件；本次内容和流利度结果仍可查看。')
                warnings.append('本地发音模块失败，本次没有发音评测结果。')
        if self.settings.pronunciation=='azure':
            if not self.settings.cloud_enabled: pron=unavailable('云端上传未获本机配置启用。')
            else:
                try:pron=AzurePronunciation().assess(source.with_name('audio.wav'),reference)
                except Exception:pron=unavailable('Azure 适配器失败；请检查可选依赖、网络与配置。')
        scores=score(comparison,features,pron)
        if features['word_count']<RUBRIC['minimum_scored_words']:
            scores=None;warnings.append('有效词数不足 3，仅显示测量，不生成总分。')
        dependencies={}
        for name in ['faster-whisper','librosa','numpy','onnxruntime','cmudict','azure-cognitiveservices-speech','whisperx']:
            try:dependencies[name]=version(name)
            except PackageNotFoundError:pass
        result={**base,'transcript':transcription.text,'comparison':comparison,'features':features,'prosody':pitch,
                'pronunciation':pron,'scores':scores,'warnings':warnings,
                'provenance':{'asr':transcription.provider,'alignment':transcription.alignment,'vad':'silero-via-faster-whisper',
                              'dependencies':dependencies,'rubric_version':RUBRIC['version'],'pronunciation':pron.get('model',pron.get('provider'))},
                'comparison_signature':'|'.join([transcription.provider,transcription.alignment,
                    str(sorted(dependencies.items())),scores['rubric_hash'] if scores else 'unscored',','.join(scores['components']) if scores else 'none',json.dumps(pron.get('model',pron.get('provider')),sort_keys=True)])}
        result['coach']=coach(result)
        if self.settings.cloud_enabled:result['coach']=enhance(result['coach'],result)
        return 'done',result
