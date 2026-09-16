"""Opt-in cloud assessment. Provider results are not PTE predictions."""
import json
import os
import threading

def unavailable(reason='未启用专用发音评测；ASR 置信度不能代替发音分。'):
    return {'status':'unavailable','reason':reason,'words':[],'accuracy_score':None,'prosody_score':None}

class AzurePronunciation:
    def assess(self,path,reference):
        import azure.cognitiveservices.speech as sdk
        key=os.getenv('AZURE_SPEECH_KEY'); region=os.getenv('AZURE_SPEECH_REGION')
        if not key or not region: return unavailable('缺少 Azure Speech 配置。')
        cfg=sdk.SpeechConfig(subscription=key,region=region)
        recognizer=sdk.SpeechRecognizer(speech_config=cfg,language='en-US',audio_config=sdk.audio.AudioConfig(filename=str(path)))
        pa=sdk.PronunciationAssessmentConfig(reference_text=reference,
            grading_system=sdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=sdk.PronunciationAssessmentGranularity.Phoneme,enable_miscue=False)
        pa.enable_prosody_assessment(); pa.apply_to(recognizer)
        done=threading.Event(); results=[]; errors=[]
        def recognized(evt):
            if evt.result.reason==sdk.ResultReason.RecognizedSpeech:
                try: results.append(json.loads(evt.result.properties.get(sdk.PropertyId.SpeechServiceResponse_JsonResult)))
                except (ValueError,TypeError): errors.append('invalid_response')
        def canceled(evt):
            if evt.reason==sdk.CancellationReason.Error: errors.append('provider_error')
            done.set()
        recognizer.recognized.connect(recognized)
        recognizer.session_stopped.connect(lambda evt:done.set())
        recognizer.canceled.connect(canceled)
        recognizer.start_continuous_recognition_async().get()
        try:
            if not done.wait(180): return unavailable('Azure 评测超时；本地分析仍然保留。')
        finally:
            recognizer.stop_continuous_recognition_async().get()
        if errors or not results: return unavailable('Azure 评测未成功；请检查网络、区域与密钥。')
        words=[]; prosody=[]
        for result in results:
            best=(result.get('NBest') or [{}])[0]
            segment_words=best.get('Words',[])
            for w in segment_words:
                words.append({'word':w['Word'],'start':w.get('Offset',0)/1e7,
                              'duration':w.get('Duration',0)/1e7,
                              'accuracy':w.get('PronunciationAssessment',{}).get('AccuracyScore'),
                              'error_type':w.get('PronunciationAssessment',{}).get('ErrorType'),
                              'phonemes':w.get('Phonemes',[]),'syllables':w.get('Syllables',[])})
            p=best.get('PronunciationAssessment',{}).get('ProsodyScore')
            if p is not None: prosody.append((float(p),max(1,len(segment_words))))
        accuracies=[float(w['accuracy']) for w in words if w['accuracy'] is not None]
        if not accuracies: return unavailable('服务未返回可用的词级发音结果。')
        return {'status':'available','provider':'azure-en-US','words':words,'raw_segments':results,
                'accuracy_score':sum(accuracies)/len(accuracies),
                'prosody_score':sum(v*n for v,n in prosody)/sum(n for _,n in prosody) if prosody else None,
                'aggregation':'arithmetic mean of word accuracy; word-count weighted segment prosody; custom aggregation, not vendor overall',
                'note':'音素低分只提示复听，不自动断言 θ→s 或尾辅音缺失。'}
