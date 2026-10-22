export const $=id=>document.getElementById(id);
export function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
export function link(text,url,cls){const a=node('a',text,cls);a.href=url;return a;}
export const language=()=>document.documentElement.lang==='en'?'en':'zh';
export const tr=(zh,en)=>language()==='en'?en:zh;
export function setup(onChange=()=>{}){
 function theme(){const dark=document.documentElement.dataset.theme==='dark';$('theme-toggle').textContent=dark?'☀':'☾';$('theme-toggle').setAttribute('aria-label',dark?tr('切换浅色主题','Use light theme'):tr('切换深色主题','Use dark theme'));}
 function apply(lang){document.documentElement.lang=lang==='en'?'en':'zh-CN';document.querySelectorAll('[data-zh][data-en]').forEach(el=>el.textContent=el.dataset[lang]);$('lang-toggle').textContent=lang==='en'?'中文':'EN';try{localStorage.setItem('ai4s-lang',lang);}catch{}onChange();theme();}
 let preferred=new URLSearchParams(location.search).get('lang');try{preferred||=localStorage.getItem('ai4s-lang');}catch{}
 $('lang-toggle').onclick=()=>apply(language()==='en'?'zh':'en');$('theme-toggle').onclick=()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=value;try{localStorage.setItem('ai4s-theme',value);}catch{}theme();};apply(preferred==='en'?'en':'zh');
}
export async function json(path){const response=await fetch(path,{cache:'no-cache'});if(!response.ok)throw new Error(`Could not load ${path}`);return response.json();}
export function localResource(path,type){const folder=type==='pdf'?'pdf':'chapters',extension=type==='pdf'?'pdf':'json';if(typeof path!=='string'||!new RegExp(`^data/textbook/${folder}/[A-Za-z0-9_-]+\\.${extension}$`).test(path))throw new Error('Invalid book resource');return path;}
export const chapterUrl=id=>'read.html?chapter='+encodeURIComponent(id);
