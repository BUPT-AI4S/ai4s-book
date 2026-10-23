const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const root=process.env.BOOK_PREVIEW_URL||'http://127.0.0.1:8085/ai4s-book/';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const previews=await(await page.request.get(root+'data/textbook/previews/index.json')).json();
 const target=previews.chapters['ch06-scientific-data'].pages[1].links[1];
 async function loaded(n){await page.waitForFunction(n=>{const im=document.querySelector('.page-preview-sheet[data-page="'+n+'"] img');return im&&!im.hidden&&im.naturalWidth>0},n)}
 async function zoom(value){await page.getByRole('button',{name:'适合页宽',exact:true}).click();for(let n=100;n!==value;n+=value>100?25:-25)await page.getByRole('button',{name:value>100?'放大':'缩小',exact:true}).click()}
 async function position(){return page.locator('.page-preview-stage').evaluate(el=>{const sheets=[...el.querySelectorAll('.page-preview-sheet')];const i=sheets.findLastIndex(s=>s.offsetTop<=el.scrollTop);return {page:i+1,fraction:(el.scrollTop-sheets[i].offsetTop)/sheets[i].offsetHeight}})}
 for(const [width,beforeZoom,afterZoom] of [[1440,100,175],[390,175,50],[390,50,175]]){
  await page.setViewportSize({width,height:1000});
  await page.goto(root+'read.html?chapter=ch06-scientific-data&view=pdf&lang=zh');await loaded(1);await zoom(beforeZoom);
  const input=page.locator('.page-preview-paging input');await input.fill('2');await input.press('Tab');await loaded(2);
  const anchor=page.locator('.page-preview-sheet[data-page="2"] .preview-link').nth(1);
  await anchor.scrollIntoViewIfNeeded();
  const before=await position();
  const geometry=await anchor.evaluate(a=>{const p=a.closest('.page-preview-sheet').getBoundingClientRect(),r=a.getBoundingClientRect();return [(r.x-p.x)/p.width,(r.y-p.y)/p.height,r.width/p.width,r.height/p.height]});
  geometry.forEach((v,i)=>assert(Math.abs(v-target.rect[i])<.0002,'link rectangle follows original citation after zoom'));
  await page.screenshot({path:'.tmp/citation-'+width+'-'+beforeZoom+'-before.png'});
  await anchor.click();await loaded(target.page);await page.waitForFunction(n=>document.querySelector('.page-preview-paging input').value===String(n),target.page);
  const landed=await position();assert.equal(landed.page,target.page);assert(Math.abs(landed.fraction-target.y)<.1,'jump to exact reference position');
  await page.screenshot({path:'.tmp/citation-'+width+'-'+beforeZoom+'-reference.png'});
  await zoom(afterZoom);await page.locator('.preview-return').click();
  const restored=await position();assert.equal(restored.page,before.page,'return preserves source page after zoom');assert(Math.abs(restored.fraction-before.fraction)<.01,'return preserves citation position after zoom');
 }
 console.log('PASS: screenshot citation [2] jumps to reference page 52; exact overlay alignment and return after zoom on desktop/mobile.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
