const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const root=process.env.BOOK_PREVIEW_URL||'http://127.0.0.1:8084/ai4s-book/';
const output=process.env.BOOK_SCREENSHOT_DIR||'.tmp';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BOOK_BROWSER_CHANNEL||'chrome'});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(),errors=[],failed=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',response=>{if(response.url().startsWith(root)&&response.status()>=400)failed.push(response.url());});
 await page.goto(root);await page.waitForSelector('.chapter-card');assert.equal(await page.locator('.chapter-card').count(),3);
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
 }
 assert.equal(figures,32);assert.equal(tips,17);assert.equal(await page.locator('#chapter-body table').count(),2);
 await page.screenshot({path:output+'/book-reader.png'});
 await page.locator('#chapter-body table').first().evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-table.png'});
 await page.setViewportSize({width:390,height:844});await page.locator('#chapter-directory summary').click();
 await page.locator('#chapter-title').evaluate(el=>el.scrollIntoView());await page.screenshot({path:output+'/book-mobile.png'});
 await page.locator('#view-pdf').click();
 const frame=page.frameLocator('#chapter-pdf iframe');await frame.locator('.pdfViewer .page canvas').first().waitFor({timeout:30000});
 assert.ok((await frame.locator('#page-count').textContent()).includes('/'));
 await page.screenshot({path:output+'/book-pdf-mobile.png'});
 await page.locator('#view-html').click();assert.equal(await page.locator('#chapter-body').isVisible(),true);
 await page.locator('#lang-toggle').click();await page.locator('#theme-toggle').click();assert.equal(await page.locator('html').getAttribute('lang'),'en');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await page.locator('#chapter-body h2').last().evaluate(el=>el.scrollIntoView());await page.locator('#chapter-body h2').nth(1).evaluate(el=>el.scrollIntoView());
 await page.waitForFunction(()=>{const a=document.querySelector('#chapter-toc a[aria-current]');return a&&decodeURIComponent(a.hash.slice(1))===document.querySelectorAll('#chapter-body h2')[1].id;});
 const promise=page.waitForEvent('download');await page.locator('#chapter-download').click();const download=await promise;assert.equal(await download.failure(),null);assert.equal(download.suggestedFilename(),'ch03-evaluation.pdf');
 await page.goto(root+'read.html?chapter=missing');await page.waitForFunction(()=>document.querySelector('#chapter-title').textContent.includes('unavailable'));assert.equal(await page.locator('#chapter-download').isVisible(),false);
 assert.equal(errors.length,0,errors.join('\n'));assert.deepEqual(failed,[]);
 assert.equal((await context.request.get(root+'.textbook-source/main.tex')).status(),404);
 console.log('PASS: project subpath, three chapters, 32 figures, 17 tips, 2 tables, links, phone/desktop, PDF mode/download, themes/languages and private-source boundary.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
