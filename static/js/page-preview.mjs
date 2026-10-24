import {node,json,tr} from './shared.mjs';

export class PagePreview {
 constructor(root,chapter,sourceHash){
  this.root=root;this.chapter=chapter;this.sourceHash=sourceHash;this.page=1;this.zoom=100;this.sheets=[];this.history=[];
  const toolbar=node('div',undefined,'page-preview-toolbar');toolbar.setAttribute('role','group');
  this.previous=node('button');this.previous.type='button';this.previous.onclick=()=>this.select(this.page-1);
  this.next=node('button');this.next.type='button';this.next.onclick=()=>this.select(this.page+1);
  this.input=node('input');this.input.type='number';this.input.min='1';this.input.value='1';this.input.onchange=()=>this.select(Number(this.input.value)||this.page);
  this.input.addEventListener('blur',()=>{this.input.value=String(this.page);});
  this.count=node('span',' / —','page-preview-count');
  this.returnButton=node('button',undefined,'preview-return');this.returnButton.type='button';this.returnButton.hidden=true;this.returnButton.onclick=()=>this.returnToCitation();
  const paging=node('div',undefined,'page-preview-paging');paging.append(this.previous,this.input,this.count,this.next,this.returnButton);
  const zooming=node('div',undefined,'page-preview-zoom');
  this.smaller=node('button','−');this.smaller.type='button';this.smaller.onclick=()=>this.resize(this.zoom-25);
  this.reset=node('button','100%');this.reset.type='button';this.reset.onclick=()=>this.resize(100);
  this.larger=node('button','+');this.larger.type='button';this.larger.onclick=()=>this.resize(this.zoom+25);
  zooming.append(this.smaller,this.reset,this.larger);toolbar.append(paging,zooming);
  this.status=node('p',undefined,'page-preview-status');this.status.setAttribute('role','status');
  this.stage=node('div',undefined,'page-preview-stage');this.stage.tabIndex=0;
  this.pages=node('div',undefined,'page-preview-pages');this.stage.append(this.pages);root.replaceChildren(toolbar,this.status,this.stage);
  this.stage.addEventListener('scroll',()=>{if(!this.scrollFrame)this.scrollFrame=requestAnimationFrame(()=>{this.scrollFrame=0;this.trackPage();});},{passive:true});
  this.stage.onkeydown=event=>{if(event.key==='ArrowLeft'){event.preventDefault();this.select(this.page-1);}if(event.key==='ArrowRight'){event.preventDefault();this.select(this.page+1);}};
  this.translate();this.update();
 }
 translate(){
  this.previous.textContent=tr('上一页','Previous');this.next.textContent=tr('下一页','Next');
  this.returnButton.textContent=tr('返回引用','Back to citation');
  this.input.setAttribute('aria-label',tr('预览页码','Preview page number'));
  this.smaller.setAttribute('aria-label',tr('缩小','Zoom out'));this.larger.setAttribute('aria-label',tr('放大','Zoom in'));this.reset.setAttribute('aria-label',tr('适合页宽','Fit page width'));
  this.stage.setAttribute('aria-label',tr('PDF 原版连续阅读','Original PDF continuous reader'));this.root.firstElementChild.setAttribute('aria-label',tr('预览控制','Preview controls'));
  for(const [index,sheet] of this.sheets.entries()){
   const label=tr('第 '+(index+1)+' 页','Page '+(index+1));sheet.setAttribute('aria-label',label);sheet.image.alt=label;
   sheet.placeholder.textContent=label;sheet.retry.textContent=tr('页面加载失败，点击重试','Page could not load. Retry');
   for(const anchor of sheet.links.querySelectorAll('a'))anchor.setAttribute('aria-label',anchor.dataset.targetPage?tr('跳转至第 '+anchor.dataset.targetPage+' 页','Go to page '+anchor.dataset.targetPage):tr('打开参考文献链接：','Open reference link: ')+anchor.href);
  }
  this.showStatus();
 }
 async show(){
  this.translate();
  if(this.data)return;
  if(this.pending)return this.pending;
  this.pending=(async()=>{
   try{
    const index=await json('data/textbook/previews/index.json'),data=index.chapters?.[this.chapter.id];
    if(index.schemaVersion!==1||index.sourceHash!==this.sourceHash||!data?.pages?.length||data.pageCount!==data.pages.length||data.pages.some(page=>!/^data\/textbook\/previews\/pages\/[a-f0-9]{64}\.webp$/.test(page.image)||!Number.isFinite(page.width)||page.width<=0||!Number.isFinite(page.height)||page.height<=0))throw new Error('Preview version mismatch');
    this.data=data;this.input.max=String(data.pageCount);this.count.textContent=' / '+data.pageCount;
    // Reserve every page's geometry so downloads never shift later pages.
    this.sheets=data.pages.map((page,index)=>{
     const sheet=node('div',undefined,'page-preview-sheet');sheet.dataset.page=String(index+1);sheet.style.aspectRatio=page.width+' / '+page.height;sheet.setAttribute('role','group');
     sheet.placeholder=node('span',undefined,'page-preview-placeholder');sheet.image=node('img');sheet.image.width=page.width;sheet.image.height=page.height;sheet.image.decoding='async';sheet.image.draggable=false;sheet.image.hidden=true;sheet.image.dataset.page=String(index+1);
     sheet.retry=node('button',undefined,'page-preview-retry');sheet.retry.type='button';sheet.retry.hidden=true;sheet.retry.onclick=()=>this.load(sheet,true);
     sheet.links=node('div',undefined,'preview-links');sheet.links.hidden=true;
     for(const target of page.links||[]){
      const anchor=node('a',undefined,'preview-link');
      const rect=target.rect;
      if(!Array.isArray(rect)||rect.length!==4||!rect.every(value=>Number.isFinite(value)&&value>=0&&value<=1))throw new Error('Invalid preview link rectangle');
      [anchor.style.left,anchor.style.top,anchor.style.width,anchor.style.height]=rect.map(value=>(100*value)+'%');
      if(Number.isInteger(target.page)&&target.page>=1&&target.page<=data.pageCount&&[target.x,target.y].every(value=>Number.isFinite(value)&&value>=0&&value<=1)){
       anchor.href='#preview-page-'+target.page;anchor.dataset.targetPage=String(target.page);anchor.onclick=event=>{event.preventDefault();this.follow(target);};
      }else if(typeof target.href==='string'&&/^(https?:\/\/|mailto:)/i.test(target.href)){
       anchor.href=target.href;anchor.target='_blank';anchor.rel='noopener noreferrer';anchor.title=target.href;
      }else throw new Error('Invalid preview link destination');
      sheet.links.append(anchor);
     }
     sheet.append(sheet.placeholder,sheet.image,sheet.links,sheet.retry);return sheet;
    });
    this.pages.replaceChildren(...this.sheets);this.translate();
    this.observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)this.load(entry.target);},{root:this.stage,rootMargin:'100% 0px'});
    this.sheets.forEach(sheet=>this.observer.observe(sheet));
    this.viewportObserver=new ResizeObserver(()=>this.reserveEndSpace());this.viewportObserver.observe(this.stage);this.select(1);
   }catch(error){console.error(error);this.root.setAttribute('aria-busy','false');this.status.hidden=false;this.status.textContent=tr('预览加载失败，请切回网页正文后重试。','The preview could not load. Switch to web text and retry.');}
   finally{this.pending=null;}
  })();return this.pending;
 }
 load(sheet,retry=false){
  if(sheet.state==='loading'||sheet.state==='loaded'||(sheet.state==='error'&&!retry))return;
  sheet.state='loading';sheet.retry.hidden=true;sheet.placeholder.hidden=false;
  const image=sheet.image;
  image.onload=async()=>{try{await image.decode();}catch{}sheet.state='loaded';image.hidden=false;sheet.links.hidden=false;sheet.placeholder.hidden=true;this.showStatus();};
  image.onerror=()=>{sheet.state='error';sheet.placeholder.hidden=true;sheet.retry.hidden=false;this.showStatus();};
  image.src=this.data.pages[Number(sheet.dataset.page)-1].image;this.showStatus();
 }
 showStatus(){
  const state=this.sheets[this.page-1]?.state;
  this.root.setAttribute('aria-busy',String(!this.data||state==='loading'));
  this.status.hidden=!!this.data&&state==='loaded';
  this.status.textContent=!this.data?tr('正在加载预览…','Loading preview…'):state==='error'?tr('本页加载失败，请点击页面中的重试按钮。','This page could not load. Use its retry button.'):tr('正在加载页面…','Loading page…');
 }
 update(){this.previous.disabled=!this.data||this.page===1;this.next.disabled=!this.data||this.page===this.data.pageCount;this.input.disabled=!this.data;}
 currentAt(offset){
  let low=0,high=this.sheets.length-1;
  while(low<high){const middle=Math.ceil((low+high)/2);if(this.sheets[middle].offsetTop<=offset)low=middle;else high=middle-1;}
  return low;
 }
 trackPage(){
  if(!this.data||!this.stage.clientHeight)return;
  const atBottom=this.stage.scrollHeight-this.stage.scrollTop-this.stage.clientHeight<2;
  this.page=atBottom?this.data.pageCount:this.currentAt(this.stage.scrollTop+Math.min(80,this.stage.clientHeight*.15))+1;
  if(document.activeElement!==this.input)this.input.value=String(this.page);
  this.update();this.load(this.sheets[this.page-1]);this.showStatus();
 }
 reserveEndSpace(){
  // A short final page must still be able to align at the viewport's top.
  if(this.sheets.length&&this.stage.clientHeight)this.pages.style.paddingBottom=Math.max(0,this.stage.clientHeight-this.sheets.at(-1).offsetHeight)+'px';
 }
 select(value){
  if(!this.data)return;
  this.page=Math.max(1,Math.min(this.data.pageCount,Math.round(value)));this.input.value=String(this.page);this.update();
  const sheet=this.sheets[this.page-1];this.load(sheet,true);this.reserveEndSpace();this.stage.scrollTop=sheet.offsetTop;this.stage.scrollLeft=0;this.showStatus();
 }
 follow(target){
  const index=this.currentAt(this.stage.scrollTop),source=this.sheets[index];
  this.history.push({index,fraction:(this.stage.scrollTop-source.offsetTop)/source.offsetHeight,horizontal:(this.stage.scrollLeft+this.stage.clientWidth/2)/this.pages.offsetWidth});this.returnButton.hidden=false;
  this.select(target.page);
  const sheet=this.sheets[target.page-1];
  const offset=Math.min(target.y*sheet.offsetHeight,Math.max(0,sheet.offsetHeight-100));
  this.stage.scrollTop=sheet.offsetTop+Math.max(0,offset-24);
  this.stage.scrollLeft=Math.max(0,target.x*sheet.offsetWidth-this.stage.clientWidth*.15);
  this.stage.focus({preventScroll:true});
 }
 returnToCitation(){
  const position=this.history.pop();if(!position)return;
  const sheet=this.sheets[position.index];
  this.reserveEndSpace();this.stage.scrollTop=sheet.offsetTop+position.fraction*sheet.offsetHeight;this.stage.scrollLeft=position.horizontal*this.pages.offsetWidth-this.stage.clientWidth/2;this.returnButton.hidden=!this.history.length;
  this.trackPage();this.stage.focus({preventScroll:true});
 }
 resize(value){
  // Anchor the same point of the same page at the top of the viewport.
  const top=this.stage.scrollTop,index=this.sheets.length?this.currentAt(top):0,sheet=this.sheets[index];
  const fraction=sheet?(top-sheet.offsetTop)/sheet.offsetHeight:0;
  const horizontal=this.pages.offsetWidth?(this.stage.scrollLeft+this.stage.clientWidth/2)/this.pages.offsetWidth:.5;
  this.zoom=Math.max(50,Math.min(250,value));this.pages.style.width=this.zoom+'%';this.reserveEndSpace();this.reset.textContent=this.zoom+'%';this.smaller.disabled=this.zoom===50;this.larger.disabled=this.zoom===250;
  if(sheet){this.stage.scrollTop=sheet.offsetTop+fraction*sheet.offsetHeight;this.stage.scrollLeft=horizontal*this.pages.offsetWidth-this.stage.clientWidth/2;this.trackPage();}
 }
}
