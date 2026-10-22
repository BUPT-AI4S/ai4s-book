import {node,json,tr} from './shared.mjs';

export class PagePreview {
 constructor(root,chapter,sourceHash){
  this.root=root;this.chapter=chapter;this.sourceHash=sourceHash;this.page=1;this.zoom=100;
  const toolbar=node('div',undefined,'page-preview-toolbar');toolbar.setAttribute('role','group');
  this.previous=node('button');this.previous.type='button';this.previous.onclick=()=>this.select(this.page-1);
  this.next=node('button');this.next.type='button';this.next.onclick=()=>this.select(this.page+1);
  this.input=node('input');this.input.type='number';this.input.min='1';this.input.value='1';this.input.onchange=()=>this.select(Number(this.input.value)||this.page);
  this.count=node('span',' / —','page-preview-count');
  const paging=node('div',undefined,'page-preview-paging');paging.append(this.previous,this.input,this.count,this.next);
  const zooming=node('div',undefined,'page-preview-zoom');
  this.smaller=node('button','−');this.smaller.type='button';this.smaller.onclick=()=>this.resize(this.zoom-25);
  this.reset=node('button','100%');this.reset.type='button';this.reset.onclick=()=>this.resize(100);
  this.larger=node('button','+');this.larger.type='button';this.larger.onclick=()=>this.resize(this.zoom+25);
  zooming.append(this.smaller,this.reset,this.larger);toolbar.append(paging,zooming);
  this.status=node('p',undefined,'page-preview-status');this.status.setAttribute('role','status');
  this.stage=node('div',undefined,'page-preview-stage');this.stage.tabIndex=0;
  this.sheet=node('div',undefined,'page-preview-sheet');this.image=node('img');this.image.decoding='async';this.image.draggable=false;this.image.hidden=true;
  this.sheet.append(this.image);this.stage.append(this.sheet);root.replaceChildren(toolbar,this.status,this.stage);
  this.stage.onkeydown=event=>{if(event.key==='ArrowLeft'){event.preventDefault();this.select(this.page-1);}if(event.key==='ArrowRight'){event.preventDefault();this.select(this.page+1);}};
  this.translate();this.update();
 }
 translate(){
  this.previous.textContent=tr('上一页','Previous');this.next.textContent=tr('下一页','Next');
  this.input.setAttribute('aria-label',tr('预览页码','Preview page number'));
  this.smaller.setAttribute('aria-label',tr('缩小','Zoom out'));this.larger.setAttribute('aria-label',tr('放大','Zoom in'));this.reset.setAttribute('aria-label',tr('适合页宽','Fit page width'));
  this.stage.setAttribute('aria-label',tr('PDF 原版页面','Original PDF page'));this.root.firstElementChild.setAttribute('aria-label',tr('预览控制','Preview controls'));
  this.image.alt=tr('第 '+this.page+' 页','Page '+this.page);
  if(!this.data)this.status.textContent=tr('正在加载预览…','Loading preview…');
 }
 async show(){
  this.translate();
  if(this.data)return;
  if(this.pending)return this.pending;
  this.pending=(async()=>{
   try{
    const index=await json('data/textbook/previews/index.json'),data=index.chapters?.[this.chapter.id];
    if(index.schemaVersion!==1||index.sourceHash!==this.sourceHash||!data?.pages?.length||data.pageCount!==data.pages.length||data.pages.some(page=>!/^data\/textbook\/previews\/pages\/[a-f0-9]{64}\.webp$/.test(page.image)))throw new Error('Preview version mismatch');
    this.data=data;this.input.max=String(data.pageCount);this.count.textContent=' / '+data.pageCount;this.select(1);
   }catch(error){console.error(error);this.root.setAttribute('aria-busy','false');this.status.hidden=false;this.status.textContent=tr('预览加载失败，请切回网页正文后重试。','The preview could not load. Switch to web text and retry.');}
   finally{this.pending=null;}
  })();return this.pending;
 }
 update(){this.previous.disabled=!this.data||this.page===1;this.next.disabled=!this.data||this.page===this.data.pageCount;this.input.disabled=!this.data;}
 select(value){
  if(!this.data)return;
  this.page=Math.max(1,Math.min(this.data.pageCount,Math.round(value)));this.input.value=String(this.page);this.update();
  const page=this.data.pages[this.page-1],image=node('img'),request=this.loadId=(this.loadId||0)+1;
  image.width=page.width;image.height=page.height;image.alt=tr('第 '+this.page+' 页','Page '+this.page);image.dataset.page=String(this.page);image.decoding='async';image.draggable=false;
  this.root.setAttribute('aria-busy','true');this.status.hidden=false;this.status.textContent=tr('正在加载页面…','Loading page…');
  image.onload=async()=>{try{await image.decode();}catch{}if(request!==this.loadId)return;this.image=image;this.sheet.replaceChildren(image);this.stage.scrollTop=0;this.stage.scrollLeft=0;this.status.hidden=true;this.root.setAttribute('aria-busy','false');};
  image.onerror=()=>{if(request!==this.loadId)return;this.root.setAttribute('aria-busy','false');this.status.hidden=false;this.status.textContent=tr('本页加载失败，请重新选择页码重试。','This page could not load. Select the page again to retry.');};
  image.src=page.image;
 }
 resize(value){this.zoom=Math.max(50,Math.min(250,value));this.sheet.style.width=this.zoom+'%';this.reset.textContent=this.zoom+'%';this.smaller.disabled=this.zoom===50;this.larger.disabled=this.zoom===250;}
}
