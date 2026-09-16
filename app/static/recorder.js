export class Recorder {
  async start(onSeconds){
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw new Error('浏览器不支持录音，请使用桌面 Chrome / Edge 的 localhost 页面，或上传音频。');
    this.stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:false}});
    const mime=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(m=>MediaRecorder.isTypeSupported(m));
    try{this.recorder=new MediaRecorder(this.stream,mime?{mimeType:mime}:undefined);}catch(e){this.stream.getTracks().forEach(t=>t.stop());throw e;}
    this.parts=[];this.recorder.ondataavailable=e=>{if(e.data.size)this.parts.push(e.data);};
    this.finished=new Promise((resolve,reject)=>{this.recorder.onstop=()=>{this.cleanup();resolve(new Blob(this.parts,{type:this.recorder.mimeType}));};this.recorder.onerror=()=>{this.cleanup();reject(new Error('录音失败，请检查麦克风或上传音频。'));};});
    this.recorder.start(250);this.started=Date.now();this.interval=setInterval(()=>onSeconds((Date.now()-this.started)/1000),250);
  }
  cleanup(){clearInterval(this.interval);this.stream?.getTracks().forEach(t=>t.stop());}
  stop(){if(this.recorder?.state==='recording')this.recorder.stop();return this.finished;}
}
