import {$,node,link,setup,tr,json,localResource,chapterUrl} from './shared.mjs';
import {PagePreview} from './page-preview.mjs?v=links-1';
let catalog,chapter,preview,mode=new URLSearchParams(location.search).get('view')==='pdf'?'pdf':'html';
function renderChrome(){
 if(!chapter)return;document.title=chapter.title+' · AI4SBook';$('chapter-title').textContent=chapter.title;$('chapter-number').textContent=tr('第 '+chapter.number+' 章','CHAPTER '+String(chapter.number).padStart(2,'0'));
 $('chapter-toc').replaceChildren(...chapter.toc.filter(item=>item.level<=3).map(item=>{const a=link(item.title,'#'+encodeURIComponent(item.id));a.dataset.level=item.level;a.onclick=()=>{if(mode==='pdf')setMode('html');if(matchMedia('(max-width:800px)').matches)$('chapter-directory').open=false;};return a;}));
 $('book-directory').replaceChildren(node('p',tr('全书章节','All chapters')),...catalog.chapters.map(item=>{const a=link(String(item.number).padStart(2,'0')+' '+item.title,chapterUrl(item.id));if(item.id===chapter.id)a.setAttribute('aria-current','page');return a;}));
 const index=catalog.chapters.findIndex(item=>item.id===chapter.id),pagination=$('chapter-pagination');pagination.replaceChildren();
 for(const [item,label] of [[catalog.chapters[index-1],tr('← 上一章','← Previous')],[null,tr('章节目录','All chapters')],[catalog.chapters[index+1],tr('下一章 →','Next →')]]){if(!item&&label!==tr('章节目录','All chapters')){pagination.append(node('span'));continue;}const a=link('',item?chapterUrl(item.id):'index.html#chapters');a.append(node('small',label));if(item)a.append(node('span',item.title));pagination.append(a);}pagination.hidden=false;
 $('view-html').disabled=false;$('view-pdf').disabled=false;setMode(mode,false);
}
function setMode(value,update=true){
 mode=value==='pdf'?'pdf':'html';$('chapter-body').hidden=mode==='pdf';$('chapter-pdf').hidden=mode!=='pdf';$('view-html').setAttribute('aria-pressed',String(mode==='html'));$('view-pdf').setAttribute('aria-pressed',String(mode==='pdf'));
 if(chapter&&mode==='pdf'){preview??=new PagePreview($('chapter-pdf'),chapter,catalog.sourceHash);void preview.show();}
 if(update){const url=new URL(location.href);if(mode==='pdf')url.searchParams.set('view','pdf');else url.searchParams.delete('view');history.replaceState(null,'',url);}
}
$('view-html').onclick=()=>setMode('html');$('view-pdf').onclick=()=>setMode('pdf');
setup(renderChrome);
try{
 catalog=await json('data/textbook/catalog.json');const entry=catalog.chapters.find(item=>item.id===new URLSearchParams(location.search).get('chapter'));if(!entry)throw new Error('missing');chapter=await json(localResource(entry.contentUrl,'chapter'));if(chapter.id!==entry.id||chapter.sourceHash!==catalog.sourceHash)throw new Error('Chapter version mismatch');
 const template=document.createElement('template');template.innerHTML=chapter.html;template.content.querySelectorAll('script,iframe,embed,object').forEach(el=>el.remove());$('chapter-body').replaceChildren(template.content);$('chapter-body').querySelectorAll('table').forEach(table=>{const wrap=node('div',undefined,'table-scroll');table.before(wrap);wrap.append(table);});$('chapter-status').hidden=true;renderChrome();
 const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting)$('chapter-toc').querySelectorAll('a').forEach(a=>{if(decodeURIComponent(a.hash.slice(1))===entry.target.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}},{rootMargin:'-15% 0px -70% 0px'});$('chapter-body').querySelectorAll('h2[id],h3[id]').forEach(el=>observer.observe(el));
 if(location.hash&&mode==='html')requestAnimationFrame(()=>document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView());
}catch(error){console.error(error);$('chapter-title').textContent=tr('章节暂不可用','Chapter unavailable');$('chapter-status').replaceChildren(node('span',error.message==='missing'?tr('未找到该章节。','Chapter not found.'):tr('章节加载失败，请刷新重试。','The chapter could not be loaded.')),link(tr('返回目录 →','All chapters →'),'index.html#chapters'));$('reader-controls').hidden=true;}
