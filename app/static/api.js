export async function api(path, options={}) {
  const response=await fetch('/api'+path,options);
  if(!response.ok){let message;try{const body=await response.json();message=typeof body.detail==='string'?body.detail:'请求参数无效。';}catch{message='服务暂时不可用。';}throw new Error(message);}
  return response.json();
}
export const $=id=>document.getElementById(id);
export function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
