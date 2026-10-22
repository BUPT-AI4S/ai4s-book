import * as pdfjs from '../vendor/pdfjs/pdf.mjs';
import {EventBus,PDFViewer,PDFLinkService} from '../vendor/pdfjs/pdf_viewer.mjs';
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search),en=params.get('lang')==='en';
const tr=(zh,english)=>en?english:zh;document.documentElement.lang=en?'en':'zh-CN';
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&window.parent!==window){event.preventDefault();window.parent.postMessage({type:'ai4s-pdf-exit'},location.origin);}});
pdfjs.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdfjs/pdf.worker.mjs',import.meta.url).href;
const assets=new URL('../vendor/pdfjs/',import.meta.url).href;
const eventBus=new EventBus(),linkService=new PDFLinkService({eventBus,externalLinkTarget:2,externalLinkRel:'noopener noreferrer'});
const viewer=new PDFViewer({container:$('viewer-container'),viewer:$('pdf-viewer'),eventBus,linkService,textLayerMode:1,annotationMode:1,imageResourcesPath:assets+'images/'});linkService.setViewer(viewer);
let task,documentPdf;
function controls(ready){for(const id of ['previous','next','zoom-in','zoom-out','fit-width','page-number'])$(id).disabled=!ready;}
for(const [id,zh,english] of [['previous','上一页','Previous'],['next','下一页','Next'],['fit-width','适合宽度','Fit width'],['pdf-download','下载 PDF','Download PDF'],['retry-pdf','重试','Retry'],['page-label','页码','Page']])$(id).textContent=tr(zh,english);
function message(text,retry=false){$('pdf-message-text').textContent=text;$('pdf-message').hidden=!text;$('retry-pdf').hidden=!retry;}
function update(){const page=viewer.currentPageNumber||1;$('page-number').value=page;$('previous').disabled=page<=1;$('next').disabled=page>=(documentPdf?.numPages||1);$('zoom-level').textContent=Math.round(viewer.currentScale*100)+'%';}
eventBus.on('pagesinit',()=>{viewer.currentScaleValue='page-width';update();});
eventBus.on('pagechanging',update);eventBus.on('scalechanging',update);
eventBus.on('pagerendered',event=>{if(event.error)message(tr('该页渲染失败，请重试。','Could not render this page. Please retry.'),true);else message('');});
$('previous').addEventListener('click',()=>{viewer.currentPageNumber=Math.max(1,viewer.currentPageNumber-1);});
$('next').addEventListener('click',()=>{viewer.currentPageNumber=Math.min(documentPdf?.numPages||1,viewer.currentPageNumber+1);});
$('page-number').addEventListener('change',()=>{viewer.currentPageNumber=Math.max(1,Math.min(documentPdf?.numPages||1,parseInt($('page-number').value,10)||1));update();});
$('zoom-in').addEventListener('click',()=>{viewer.currentScale=Math.min(4,viewer.currentScale*1.2);});
$('zoom-out').addEventListener('click',()=>{viewer.currentScale=Math.max(.25,viewer.currentScale/1.2);});
$('fit-width').addEventListener('click',()=>{viewer.currentScaleValue='page-width';});
new ResizeObserver(()=>{if(documentPdf&&viewer.currentScaleValue==='page-width')viewer.currentScaleValue='page-width';}).observe($('viewer-container'));
async function load(){
  controls(false);message(tr('正在加载 PDF…','Loading PDF…'));documentPdf=null;viewer.setDocument(null);await task?.destroy();
  try{
    const response=await fetch('data/textbook/catalog.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog');const data=await response.json();
    const paper=data.chapters.find(p=>p.id===params.get('chapter'));if(!paper?.pdfUrl)throw new Error('No PDF URL');
    if(!/^data\/textbook\/pdf\/[A-Za-z0-9_-]+\.pdf$/.test(paper.pdfUrl))throw new Error('Unsafe URL');
    const url=new URL(paper.pdfUrl,location.href);
    document.title=paper.title+' · PDF';$('pdf-download').href=url.href;$('pdf-download').download=paper.id+'.pdf';$('pdf-download').hidden=false;
    task=pdfjs.getDocument({url:url.href,cMapUrl:assets+'cmaps/',cMapPacked:true,standardFontDataUrl:assets+'standard_fonts/',wasmUrl:assets+'wasm/',isEvalSupported:false});
    task.onProgress=({loaded,total})=>message(total?tr(`正在加载 PDF… ${Math.min(100,Math.round(loaded/total*100))}%`,`Loading PDF… ${Math.min(100,Math.round(loaded/total*100))}%`):tr('正在加载 PDF…','Loading PDF…'));
    documentPdf=await task.promise;$('page-count').textContent='/ '+documentPdf.numPages;$('page-number').max=documentPdf.numPages;viewer.setDocument(documentPdf);linkService.setDocument(documentPdf);controls(true);update();
  }catch(error){console.error('PDF loading failed',error);message(tr('PDF 加载失败。请重试，或点击“下载 PDF”获取原文。','Could not load PDF. Retry or download the original.'),true);}
}
$('retry-pdf').addEventListener('click',load);load();
