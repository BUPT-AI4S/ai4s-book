import {$,node,link,setup,tr,json,chapterUrl} from './shared.mjs';
let catalog;
const descriptions={'ch13-knowledge-rag':['知识如何进入推理','Knowledge for reasoning'],'ch16-autonomous-laboratory':['计算如何连接实验','Connecting computation and experiments'],'ch03-evaluation':['证据如何支持结论','Evidence for credible conclusions']};
function render(){
 if(!catalog)return;
 $('chapter-cards').replaceChildren(...catalog.chapters.map(chapter=>{
  const card=node('article',undefined,'chapter-card'),top=node('div',undefined,'card-top');top.append(node('span',String(chapter.number).padStart(2,'0'),'card-number'),node('span',tr('开放阅读','Read online'),'access-badge'));
  const heading=node('h3');heading.lang='zh-CN';heading.append(link(chapter.title,chapterUrl(chapter.id)));
  const description=node('p',chapter.summary,'card-description');description.lang='zh-CN';const subtitle=descriptions[chapter.id]||[chapter.title,chapter.title];
  const actions=node('div',undefined,'card-actions');actions.append(link(tr('在线阅读 →','Read online →'),chapterUrl(chapter.id)));
  actions.append(link(tr('PDF 预览 ↗','PDF preview ↗'),chapterUrl(chapter.id)+'&view=pdf'));
  card.append(top,node('p',tr(...subtitle),'card-kicker'),heading,description,actions);return card;
 }));$('catalog-status').hidden=true;
}
setup(render);
try{catalog=await json('data/textbook/catalog.json');if(catalog.schemaVersion!==1||!catalog.chapters?.length)throw new Error('Invalid catalog');render();}catch(error){console.error(error);$('catalog-status').textContent=tr('章节加载失败，请刷新重试。','Chapters could not be loaded. Please refresh.');}
