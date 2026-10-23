const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const root=process.env.BOOK_PREVIEW_URL||'http://127.0.0.1:8084/ai4s-book/';
const output=process.env.BOOK_SCREENSHOT_DIR||'.tmp';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BOOK_BROWSER_CHANNEL||'chrome'});
 try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(),errors=[],failed=[],pdfRequests=[];
 page.on('request',request=>{if(new URL(request.url()).pathname.toLowerCase().endsWith('.pdf'))pdfRequests.push(request.url());});
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',response=>{if(response.url().startsWith(root)&&response.status()>=400)failed.push(response.url());});
 const catalog=await (await context.request.get(root+'data/textbook/catalog.json')).json();
 const previews=await (await context.request.get(root+'data/textbook/previews/index.json')).json();
 const release=await (await context.request.get(root+'data/site-meta.json')).json();
 const chapters=catalog.chapters.map(chapter=>chapter.id);
 assert.ok(chapters.length>0);assert.equal(previews.sourceHash,catalog.sourceHash);
 await page.goto(root);await page.waitForSelector('.chapter-card');assert.equal(await page.locator('.chapter-card').count(),chapters.length);
 assert.equal(await page.locator('.card-actions a[href*="view=pdf"]').count(),chapters.length);
 assert.equal(await page.locator('.hero-actions a[href="https://bupt-ai4s.github.io/"]').count(),1);
 assert.equal(await page.locator('a[download],a[href*=".pdf"]').count(),0);
 assert.ok((await page.locator('.english-title').textContent()).includes('AI FOR SCIENCE'));
 assert.ok(!/持续修订|持续编写|草稿|原稿|暂不公开/.test(await page.locator('body').innerText()));
 assert.ok(await page.locator('a[href="mailto:ehaihong@bupt.edu.cn"]').count()>0);
 await page.screenshot({path:output+'/book-home.png'});
 const dateFormat=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 for(const lang of ['zh-CN','en']){
  if(await page.locator('html').getAttribute('lang')!==lang)await page.locator('#lang-toggle').click();
  for(const theme of ['light','dark']){
   if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').click();
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:1000});
    await page.waitForFunction(()=>document.querySelector('#last-updated').dateTime.length>0);
    for(const [id,key] of [['first-published','firstPublishedAt'],['last-updated','lastUpdatedAt']]){
     assert.equal(await page.locator('#'+id).getAttribute('datetime'),release[key]);
     assert.equal(await page.locator('#'+id).textContent(),dateFormat.format(new Date(release[key])));
    }
    assert.deepEqual(await page.locator('.publication-times dt').allTextContents(),lang==='en'?['First published','Last updated']:['首次推出','最近更新']);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'publication metadata overflow '+[lang,theme,width].join('/'));
    if(width===390||width===1440){await page.locator('.publication-meta').scrollIntoViewIfNeeded();await page.screenshot({path:output+'/book-home-dates-'+lang+'-'+theme+'-'+width+'.png'});}
   }
  }
 }
 await page.locator('#lang-toggle').click();await page.locator('#theme-toggle').click();
 for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'home overflow '+width);}
 await page.locator('#chapters').evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-chapters.png'});
 const input=page.locator('.page-preview-paging input');
 async function loaded(number){
  await page.waitForFunction(number=>{const image=document.querySelector('.page-preview-sheet[data-page="'+number+'"] img');return image&&!image.hidden&&image.complete&&image.naturalWidth>0;},number);
 }
 async function jump(number){await input.fill(String(number));await input.press('Tab');await loaded(number);await page.waitForFunction(number=>document.querySelector('.page-preview-paging input').value===String(number),number);}
 async function noOverflow(label){for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),label+' overflow '+width);}}
 async function noBookDownloads(){
  assert.equal(await page.locator('a[download],iframe,embed,object').count(),0);
  // External research-paper references are allowed; textbook PDFs stay private.
  assert.deepEqual(await page.locator('a[href]').evaluateAll(links=>links.filter(a=>{const url=new URL(a.href);return url.origin===location.origin&&url.pathname.toLowerCase().endsWith('.pdf');}).map(a=>a.href)),[],'no public textbook PDF links');
 }
 let figures=0,tables=0,tips=0,totalPages=0;
 for(const entry of catalog.chapters){
  const id=entry.id,preview=previews.chapters[id],total=preview.pageCount;totalPages+=total;
  const content=await (await context.request.get(root+entry.contentUrl)).json();
  await page.goto(root+'read.html?chapter='+id);await page.waitForSelector('#chapter-body h2');
  const expected=await page.evaluate(html=>{const template=document.createElement('template');template.innerHTML=html;return {figures:template.content.querySelectorAll('figure').length,tips:template.content.querySelectorAll('blockquote').length,tables:template.content.querySelectorAll('table').length};},content.html);
  assert.equal(await page.locator('#chapter-body figure').count(),expected.figures);figures+=expected.figures;
  assert.equal(await page.locator('#chapter-body blockquote').count(),expected.tips);tips+=expected.tips;
  assert.equal(await page.locator('#chapter-body table').count(),expected.tables);tables+=expected.tables;
  assert.equal(await page.locator('#chapter-body h1').count(),0);
  assert.deepEqual(await page.locator('#chapter-body a[href^="#"]').evaluateAll(links=>links.filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.getAttribute('href'))),[],'broken local references');
  await page.waitForFunction(()=>[...document.querySelectorAll('#chapter-body img')].every(img=>img.complete&&img.naturalWidth>0));
  await noOverflow('reader '+id);
  await page.locator('#view-pdf').click();await loaded(1);
  assert.equal(await page.locator('.page-preview-count').textContent(),' / '+total);
  assert.equal(await page.locator('.page-preview-sheet').count(),total,'all pages have continuous scroll placeholders');
  if(total>1)assert.ok(await page.locator('.page-preview-sheet img[src]').count()<total,'offscreen images load on demand');
  const stage=page.locator('.page-preview-stage');
  if(total>1){
   // Scroll inside the continuous reader without pressing its paging buttons.
   await stage.evaluate(el=>{el.scrollTop=el.querySelector('.page-preview-sheet[data-page="2"]').offsetTop;});
   await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='2');await loaded(2);
   await page.getByRole('button',{name:'上一页',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='1');
   await page.getByRole('button',{name:'下一页',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='2');
  }
  await stage.evaluate(el=>{el.scrollTop=el.scrollHeight;});
  await page.waitForFunction(total=>document.querySelector('.page-preview-paging input').value===String(total),total);await loaded(total);
  assert.equal(await page.getByRole('button',{name:'下一页',exact:true}).isDisabled(),true);
  const middle=Math.max(1,Math.floor(total/2));await jump(middle);
  await stage.evaluate((el,number)=>{const sheet=el.querySelector('.page-preview-sheet[data-page="'+number+'"]');el.scrollTop=sheet.offsetTop+sheet.offsetHeight*.2;},middle);
  // Zoom must keep the same page and the same fractional position within it.
  const before=await stage.evaluate((el,number)=>{const sheet=el.querySelector('.page-preview-sheet[data-page="'+number+'"]');return (el.scrollTop-sheet.offsetTop)/sheet.offsetHeight;},middle);
  for(let count=0;count<4;count++)await page.getByRole('button',{name:'放大',exact:true}).click();
  assert.equal(await input.inputValue(),String(middle));
  const after=await stage.evaluate((el,number)=>{const sheet=el.querySelector('.page-preview-sheet[data-page="'+number+'"]');return (el.scrollTop-sheet.offsetTop)/sheet.offsetHeight;},middle);
  assert.ok(Math.abs(before-after)<.005,'zoom retains reading position');
  await noOverflow('preview '+id);
  await page.getByRole('button',{name:'适合页宽',exact:true}).click();await jump(1);
  await page.screenshot({path:output+'/book-original-'+id+'.png'});
  await noBookDownloads();
  await page.locator('#view-html').click();assert.equal(await page.locator('#chapter-body').isVisible(),true);
  await page.locator('#view-pdf').click();await loaded(1);assert.equal(await input.inputValue(),'1');
  await page.locator('#view-html').click();
 }
 await page.screenshot({path:output+'/book-reader.png'});
 if(await page.locator('#chapter-body table').count()){await page.locator('#chapter-body table').first().evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-table.png'});}
 await page.setViewportSize({width:390,height:844});await page.locator('#chapter-directory summary').click();
 await page.locator('#chapter-title').evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-mobile.png'});
 await page.locator('#view-pdf').click();await loaded(1);
 const mobileTotal=previews.chapters[chapters.at(-1)].pageCount;
 if(mobileTotal>1){
  for(const width of [820,390]){
   await page.setViewportSize({width,height:1000});
   await page.getByRole('button',{name:'适合页宽',exact:true}).click();
   await page.getByRole('button',{name:'缩小',exact:true}).click();await page.getByRole('button',{name:'缩小',exact:true}).click();
   await input.fill(String(mobileTotal-1));await input.press('Tab');
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   assert.equal(await input.inputValue(),String(mobileTotal-1),'50% penultimate-page navigation at '+width);
   assert.ok(await page.locator('.page-preview-stage').evaluate(el=>{const sheet=el.querySelectorAll('.page-preview-sheet')[Number(document.querySelector('.page-preview-paging input').value)-1];return Math.abs(sheet.offsetTop-el.scrollTop)<2;}),'selected page aligns with the reading viewport');
   await jump(mobileTotal);
  }
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'适合页宽',exact:true}).click();await jump(1);
 }
 if(mobileTotal>1){await page.locator('.page-preview-stage').evaluate(el=>{el.scrollTop=el.querySelector('.page-preview-sheet[data-page="2"]').offsetTop;});await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='2');await loaded(2);}
 const mobileMiddle=Math.max(1,Math.floor(mobileTotal/2));await jump(mobileMiddle);
 await page.getByRole('button',{name:'放大',exact:true}).click();assert.equal(await input.inputValue(),String(mobileMiddle));
 await page.getByRole('button',{name:'适合页宽',exact:true}).click();
 await page.locator('.page-preview-stage').evaluate(el=>{el.scrollTop=el.scrollHeight;});await loaded(mobileTotal);await page.waitForFunction(total=>document.querySelector('.page-preview-paging input').value===String(total),mobileTotal);
 await page.screenshot({path:output+'/book-original-mobile.png'});
 await page.locator('#lang-toggle').click();assert.equal(await page.locator('.page-preview-paging button').first().textContent(),'Previous');assert.equal(await page.locator('#chapter-pdf').isVisible(),true);assert.equal(await input.inputValue(),String(mobileTotal));await page.locator('#lang-toggle').click();
 await noBookDownloads();
 await page.locator('#view-html').click();
 await page.locator('#lang-toggle').click();await page.locator('#theme-toggle').click();assert.equal(await page.locator('html').getAttribute('lang'),'en');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await page.locator('#chapter-body h2').last().evaluate(el=>el.scrollIntoView());await page.locator('#chapter-body h2').nth(1).evaluate(el=>el.scrollIntoView());
 await page.waitForFunction(()=>{const a=document.querySelector('#chapter-toc a[aria-current]');if(!a)return false;const headings=[...document.querySelectorAll('#chapter-body h2,#chapter-body h3')],target=document.querySelectorAll('#chapter-body h2')[1],start=headings.indexOf(target),next=headings.findIndex((h,index)=>index>start&&h.tagName==='H2');return headings.slice(start,next<0?undefined:next).some(h=>h.id===decodeURIComponent(a.hash.slice(1)));});
 const first=chapters[0];
 await page.goto(root+'pdf.html?chapter='+first);await page.waitForURL('**/read.html?chapter='+first+'&view=pdf');await loaded(1);
 await page.goto(root+'read.html?chapter='+first+'&view=pdf');await loaded(1);assert.equal(await page.locator('iframe,a[download]').count(),0);
 const retryPage=await context.newPage();let attempts=0;
 await retryPage.route(root+previews.chapters[first].pages[0].image,async route=>{attempts++;if(attempts===1)await route.abort();else await route.continue();});
 await retryPage.goto(root+'read.html?chapter='+first+'&view=pdf');
 const retry=retryPage.locator('.page-preview-sheet[data-page="1"] button');await retry.waitFor({state:'visible'});
 assert.equal(attempts,1,'failed pages wait for an explicit retry');await retry.click();
 await retryPage.waitForFunction(()=>{const image=document.querySelector('.page-preview-sheet[data-page="1"] img');return image&&!image.hidden&&image.complete&&image.naturalWidth>0;});
 assert.equal(attempts,2);await retryPage.close();
 await page.goto(root+'read.html?chapter=missing');await page.waitForFunction(()=>document.querySelector('#chapter-title').textContent.includes('unavailable'));
 assert.equal(errors.length,0,errors.join('\n'));assert.deepEqual(failed,[]);
 assert.deepEqual(pdfRequests,[],'Preview must not request PDF files');
 assert.equal((await context.request.get(root+'.textbook-source/main.tex')).status(),404);
 for(const id of ['scientific-intelligence',...chapters])assert.equal((await context.request.get(root+'data/textbook/pdf/'+id+'.pdf')).status(),404);
 console.log(`PASS: ${chapters.length} chapters, ${totalPages} continuous preview pages, ${figures} figures, ${tables} tables, ${tips} notes; 16 homepage date/language/theme/width combinations; lazy loading, scroll, navigation, zoom position, mobile/desktop, no downloads and no PDF requests.`);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
