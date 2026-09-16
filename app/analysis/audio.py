"""Acoustic measurements. Quiet/no-speech recordings are not scored."""
from pathlib import Path
import subprocess
import numpy as np
import soundfile as sf

SR=16000

def decode(source: Path, destination: Path, max_seconds=120):
    try:
        subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-protocol_whitelist','file,pipe',
                        '-i',str(source),'-t',str(max_seconds+1),'-vn','-ac','1','-ar',str(SR),
                        '-c:a','pcm_s16le',str(destination)],check=True,capture_output=True,timeout=45)
        y,sr=sf.read(destination,dtype='float32')
    except (subprocess.SubprocessError,OSError,RuntimeError) as exc:
        raise ValueError('音频无法解码，请上传 WAV / MP3 / M4A / WebM。') from exc
    if not .5<=len(y)/sr<=max_seconds:
        raise ValueError(f'录音时长须为 0.5–{max_seconds} 秒；长音频不会被悄悄截断评分。')
    return y,sr

def quality(y,sr):
    rms=float(np.sqrt(np.mean(y*y))) if len(y) else 0.
    clip=float(np.mean(np.abs(y)>=.995)) if len(y) else 0.
    db=float(20*np.log10(max(rms,1e-10)))
    reasons=[]
    if db < -48: reasons.append('录音过轻或没有声音，请靠近麦克风后重录。')
    if clip>.05: reasons.append('录音严重削波，请降低麦克风增益。')
    return {'usable':not reasons,'rms_dbfs':round(db,2),'clipping_ratio':round(clip,4),'reasons':reasons,
            'noise_snr_db':None,'note':'质量门槛不能排除背景人声或所有噪声。'}

def speech_regions(y,sr):
    from faster_whisper.vad import get_speech_timestamps, VadOptions
    result=get_speech_timestamps(y,VadOptions(min_silence_duration_ms=100,speech_pad_ms=0),sampling_rate=sr)
    return [{'start':r['start']/sr,'end':r['end']/sr} for r in result]

def pitch_summary(y,sr):
    import librosa
    f0,voiced,prob=librosa.pyin(y,fmin=60,fmax=500,sr=sr,frame_length=1024,hop_length=320)
    valid=np.isfinite(f0)&voiced&(prob>=.5)
    values=f0[valid]
    contour=[{'time':round(i*320/sr,3),'hz':round(float(v),1) if valid[i] else None} for i,v in enumerate(f0)]
    result={'method':'librosa.pyin','median_hz':None,'range_semitones':None,'voiced_frame_ratio':round(float(np.mean(valid)),3),
            'contour':contour,'stress_accuracy':None,'rhythm_score':None,'note':'音高变化不等于韵律好坏；未据此推断重音正确性。'}
    if len(values)>=5:
        lo,hi=np.percentile(values,[10,90])
        result.update(median_hz=round(float(np.median(values)),1),range_semitones=round(float(12*np.log2(hi/lo)),2))
    return result

def waveform(y,points=900):
    return [round(float(np.max(np.abs(a))),4) for a in np.array_split(y,min(points,len(y))) if len(a)]
