from pathlib import Path
from app.models import Word, Transcript

class FasterWhisperASR:
    def __init__(self,settings):
        self.settings=settings; self.model=None
    def transcribe(self,path:Path):
        from faster_whisper import WhisperModel
        if self.model is None:
            self.model=WhisperModel(self.settings.asr_model,device=self.settings.device,compute_type=self.settings.compute_type)
        segments,_=self.model.transcribe(str(path),language='en',beam_size=5,word_timestamps=True,
                                        vad_filter=True,condition_on_previous_text=False)
        segments=list(segments)
        words=[Word(w.word.strip(),w.start,w.end,w.probability) for s in segments for w in (s.words or [])]
        return Transcript(' '.join(s.text.strip() for s in segments),words,f'faster-whisper:{self.settings.asr_model}')

class WhisperXAligner:
    def __init__(self,device='cpu'):
        self.device=device; self.model=None; self.metadata=None
    def align(self,path,transcript):
        import whisperx
        if self.model is None:
            self.model,self.metadata=whisperx.load_align_model(language_code='en',device=self.device)
        audio=whisperx.load_audio(str(path))
        result=whisperx.align([{'text':transcript.text,'start':0,'end':len(audio)/16000}],
                             self.model,self.metadata,audio,self.device,return_char_alignments=False)
        words=[Word(w['word'],w.get('start'),w.get('end'),None,w.get('score')) for w in result['word_segments']]
        return Transcript(transcript.text,words,transcript.provider,'whisperx-forced-hypothesis')
