const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const root=process.env.BOOK_PREVIEW_URL||'http://127.0.0.1:8084/ai4s-book/';
const output=process.env.BOOK_SCREENSHOT_DIR||'.tmp';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BOOK_BROWSER_CHANNEL||'chrome'});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(),errors=[],failed=[],pdfRequests=[];
 page.on('request',request=>{if(new URL(request.url()).pathname.endsWith('.pdf'))pdfRequests.push(request.url());});
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',response=>{if(response.url().startsWith(root)&&response.status()>=400)failed.push(response.url());});
 await page.goto(root);await page.waitForSelector('.chapter-card');assert.equal(await page.locator('.chapter-card').count(),3);
 assert.equal(await page.locator('.card-actions a[href*="view=pdf"]').count(),3);
 assert.equal(await page.locator('.hero-actions a[href=\"https://bupt-ai4s.github.io/\"]').count(),1);
 assert.equal(await page.locator('a[download],a[href*=\".pdf\"]').count(),0);
 assert.ok((await page.locator('.english-title').textContent()).includes('AI FOR SCIENCE'));
 assert.ok(!/持续修订|持续编写|草稿|原稿|暂不公开/.test(await page.locator('body').innerText()));
 assert.ok(await page.locator('a[href=\"mailto:ehaihong@bupt.edu.cn\"]').count()>0);
 await page.screenshot({path:output+'/book-home.png'});
 for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'home overflow '+width);}
 await page.locator('#chapters').evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-chapters.png'});
 let figures=0,tips=0;
 const chapters=['ch13-knowledge-rag','ch16-autonomous-laboratory','ch03-evaluation'];
 for(const id of chapters){
  await page.goto(root+'read.html?chapter='+id);await page.waitForSelector('#chapter-body h2');
  figures+=await page.locator('#chapter-body figure').count();tips+=await page.locator('#chapter-body blockquote').count();
  assert.equal(await page.locator('#chapter-body h1').count(),0);
  assert.deepEqual(await page.locator('#chapter-body a[href^="#"]').evaluateAll(links=>links.filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.getAttribute('href'))),[],'broken local references');
  await page.waitForFunction(()=>[...document.querySelectorAll('#chapter-body img')].every(img=>img.complete&&img.naturalWidth>0));
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'reader overflow '+id+' '+width);}
  await page.locator('#view-pdf').click();
  await page.waitForFunction(()=>{const image=document.querySelector('#chapter-pdf img');return image&&!image.hidden&&document.querySelector('#chapter-pdf').getAttribute('aria-busy')==='false'&&image.complete&&image.naturalWidth===1600;});
  const total={'ch13-knowledge-rag':47,'ch16-autonomous-laboratory':35,'ch03-evaluation':33}[id];
  assert.equal(await page.locator('.page-preview-count').textContent(),' / '+total);
  await page.getByRole('button',{name:'下一页',exact:true}).click();assert.equal(await page.locator('.page-preview-paging input').inputValue(),'2');
  await page.locator('.page-preview-paging input').fill(String(total));await page.locator('.page-preview-paging input').press('Tab');
  assert.equal(await page.getByRole('button',{name:'下一页',exact:true}).isDisabled(),true);
  await page.getByRole('button',{name:'适合页宽',exact:true}).click();
  for(let count=0;count<4;count++)await page.getByRole('button',{name:'放大',exact:true}).click();
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'preview overflow '+id+' '+width);}
  await page.locator('.page-preview-paging input').fill('1');await page.locator('.page-preview-paging input').press('Tab');await page.getByRole('button',{name:'适合页宽',exact:true}).click();
  await page.waitForFunction(()=>{const image=document.querySelector('#chapter-pdf img');return image&&!image.hidden&&document.querySelector('#chapter-pdf').getAttribute('aria-busy')==='false'&&image.complete;});
  await page.screenshot({path:output+'/book-original-'+id+'.png'});
  assert.equal(await page.locator('a[download],a[href$=".pdf"],iframe,embed,object').count(),0);
  await page.locator('#view-html').click();
 }
 assert.equal(figures,32);assert.equal(tips,17);assert.equal(await page.locator('#chapter-body table').count(),2);
 await page.screenshot({path:output+'/book-reader.png'});
 await page.locator('#chapter-body table').first().evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-table.png'});
 await page.setViewportSize({width:390,height:844});await page.locator('#chapter-directory summary').click();
 await page.locator('#chapter-title').evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-mobile.png'});
 await page.locator('#view-pdf').click();await page.waitForFunction(()=>{const image=document.querySelector('#chapter-pdf img');return image&&!image.hidden&&document.querySelector('#chapter-pdf').getAttribute('aria-busy')==='false'&&image.complete;});await page.screenshot({path:output+'/book-original-mobile.png'});
 await page.locator('#lang-toggle').click();assert.equal(await page.locator('.page-preview-paging button').first().textContent(),'Previous');assert.equal(await page.locator('#chapter-pdf').isVisible(),true);await page.locator('#lang-toggle').click();
 assert.equal(await page.locator('a[download],a[href*=\".pdf\"],iframe').count(),0);
 await page.locator('#view-html').click();
 await page.locator('#lang-toggle').click();await page.locator('#theme-toggle').click();assert.equal(await page.locator('html').getAttribute('lang'),'en');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await page.locator('#chapter-body h2').last().evaluate(el=>el.scrollIntoView());await page.locator('#chapter-body h2').nth(1).evaluate(el=>el.scrollIntoView());
 await page.waitForFunction(()=>{const a=document.querySelector('#chapter-toc a[aria-current]');return a&&decodeURIComponent(a.hash.slice(1))===document.querySelectorAll('#chapter-body h2')[1].id;});
 await page.goto(root+'pdf.html?chapter=ch13-knowledge-rag');await page.waitForURL('**/read.html?chapter=ch13-knowledge-rag&view=pdf');await page.locator('#chapter-pdf img').waitFor();
 await page.goto(root+'read.html?chapter=ch13-knowledge-rag&view=pdf');await page.locator('#chapter-pdf img').waitFor();assert.equal(await page.locator('iframe,a[download]').count(),0);
 await page.goto(root+'read.html?chapter=missing');await page.waitForFunction(()=>document.querySelector('#chapter-title').textContent.includes('unavailable'));
 assert.equal(errors.length,0,errors.join('\n'));assert.deepEqual(failed,[]);
 assert.deepEqual(pdfRequests,[],'Preview must not request PDF files');
 assert.equal((await context.request.get(root+'.textbook-source/main.tex')).status(),404);
 for(const id of ['scientific-intelligence',...chapters])assert.equal((await context.request.get(root+'data/textbook/pdf/'+id+'.pdf')).status(),404);
 console.log('PASS: three chapters, 115 preview pages, navigation, zoom, mobile/desktop, course/email, themes/languages, no downloads and no PDF requests.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
