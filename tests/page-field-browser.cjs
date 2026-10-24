const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const root=process.env.BOOK_PREVIEW_URL||'http://127.0.0.1:8094/ai4s-book/';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await page.goto(root+'read.html?chapter=ch06-scientific-data&view=pdf&lang=zh');
  const input=page.locator('.page-preview-paging input');
  await page.waitForFunction(()=>document.querySelector('.page-preview-sheet[data-page="1"] img')?.naturalWidth>0);
  await input.fill('27');
  // A pending scroll notification must not erase a page number being edited.
  await page.locator('.page-preview-stage').evaluate(stage=>stage.scrollTop=stage.querySelector('[data-page="2"]').offsetTop);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(await input.inputValue(),'27','scroll tracking preserves the number being typed');
  await input.press('Tab');
  await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='27');
  assert(await page.locator('.page-preview-stage').evaluate(stage=>Math.abs(stage.scrollTop-stage.querySelector('[data-page="27"]').offsetTop)<2));
  await input.focus();
  await page.locator('.page-preview-stage').evaluate(stage=>stage.scrollTop=stage.querySelector('[data-page="3"]').offsetTop);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await input.press('Tab');
  await page.waitForFunction(()=>document.querySelector('.page-preview-paging input').value==='3');
  console.log('PASS: preview scrolling preserves the page number during editing, commits the typed destination, and refreshes the page indicator on blur.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
