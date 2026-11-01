/* Browser QA uses the host's installed Playwright; no project dependency install. */
const {chromium}=require(process.env.BANK_SALARY_PLAYWRIGHT||'playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');

(async()=>{
  const url=process.argv[2]||'http://127.0.0.1:8786/report.html';
  const output=process.argv[3];
  if(!output)throw new Error('Pass an output directory containing expected.json');
  const expected=JSON.parse(fs.readFileSync(path.join(output,'expected.json'),'utf8'));
  const browser=await chromium.launch({headless:true,executablePath:process.env.BANK_SALARY_BROWSER});
  const errors=[],checks=[];
  try{
    const context=await browser.newContext({viewport:{width:1440,height:1100},colorScheme:'light',acceptDownloads:true});
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.reportReady===true,{timeout:7000});
    await Promise.race([page.evaluate(()=>document.fonts.ready),new Promise(r=>setTimeout(r,6000))]);
    const companies=Object.keys(expected.scenario.companies);
    assert.equal(await page.locator('#totalJobs').innerText(),expected.totals.jobs.toLocaleString('en-US'));
    assert.equal(await page.locator('#salaryJobs').innerText(),expected.totals.salary_jobs.toLocaleString('en-US'));
    for(const c of companies){
      const {jobs,salary_jobs}=expected.coverage[c];
      assert.equal(await page.locator(`#coverage-${c}`).innerText(),`${salary_jobs.toLocaleString('en-US')} / ${jobs.toLocaleString('en-US')}（${(salary_jobs/jobs*100).toFixed(1)}%）`);
    }
    assert.equal(await page.locator('svg').count(),4);
    await page.screenshot({path:path.join(output,'desktop-top.png')});
    checks.push(`snapshot totals and per-company salary coverage for ${companies.join(', ')}; all four SVG charts rendered`);
    await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'desktop-analysis.png')});
    const defaultView=await page.locator('#comparisonBody').innerText();
    for(const mode of ['scenario','year','hour']){
      await page.selectOption('#program',mode==='scenario'?'professional':'all');await page.selectOption('#mode',mode);
      assert.equal(Number((await page.locator('#selectedRanges').innerText()).replaceAll(',','')),expected[mode].ranges);
      assert.equal(Number((await page.locator('#selectedJobs').innerText()).replaceAll(',','')),expected[mode].jobs);
      const cells=await page.locator('#comparisonBody tr').evaluateAll(rows=>rows.map(r=>[...r.children].map(c=>c.textContent)));
      assert.equal(cells.length,companies.length);
      companies.forEach((c,i)=>{
        assert.equal(Number(cells[i][2].replaceAll(',','')),expected[mode].companies[c].ranges);
        const displayed=cells[i][4]==='—'?null:Number(cells[i][4].replace(/[$,]/g,''));
        if(displayed===null)assert.equal(expected[mode].companies[c].median,null);
        else assert.ok(Math.abs(displayed-expected[mode].companies[c].median)<.011);
      });
      checks.push(`${mode} counts and company medians independently match SQLite baseline`);
    }
    await page.click('#resetFilters');
    await page.selectOption('#businessDepartment','Technology');
    await page.selectOption('#businessSubdepartment','株式・デリバティブ技術');
    await page.selectOption('#occupation','エンジニア・開発');
    const taxonomyCount=Number((await page.locator('#selectedJobs').innerText()).replaceAll(',',''));
    assert.ok(taxonomyCount>0&&taxonomyCount<expected.scenario.jobs);
    const taxonomyCells=await page.locator('#jobsBody tr').evaluateAll(rows=>rows.map(r=>[...r.children].slice(2,5).map(c=>c.textContent)));
    assert.ok(taxonomyCells.length>0);taxonomyCells.forEach(c=>assert.deepEqual(c,['Technology','株式・デリバティブ技術','エンジニア・開発']));
    await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'taxonomy-filters.png')});
    await page.selectOption('#businessDepartment','投資銀行');
    assert.equal(await page.locator('#businessSubdepartment').inputValue(),'all');assert.equal(await page.locator('#occupation').inputValue(),'all');
    const subOptions=await page.locator('#businessSubdepartment option').allTextContents();assert.ok(subOptions.includes('M&A'));assert.equal(subOptions.includes('株式部'),false);
    checks.push('three independent taxonomy filters update salary results and table; department changes reset dependent options');
    for(const [req,subdepartment] of [['PT-JR042997','電子取引システム'],['PT-JR037125','株式・デリバティブ技術']]){
      await page.click('#resetFilters');await page.fill('#query',req);await page.waitForTimeout(250);
      assert.equal(await page.locator('#selectedJobs').innerText(),'1');
      assert.deepEqual(await page.locator('#jobsBody tr').first().locator('td').evaluateAll(cells=>cells.slice(2,5).map(c=>c.textContent)),['Technology',subdepartment,'エンジニア・開発']);
      await page.locator(`[data-job="MS:${req}"]`).click();
      assert.equal(await page.locator('#dialogClassification .classification-details strong').first().innerText(),'Technology');
      await page.mouse.move(10,10);
      if(req==='PT-JR037125')await page.locator('#jobDialog').screenshot({path:path.join(output,'technology-correction.png')});
      await page.click('#closeDialog');
    }
    checks.push('both user-reported trading technology leads are Technology, with correct technical roles and source evidence');
    await page.click('#resetFilters');await page.fill('#query','JR036102');await page.waitForTimeout(250);
    assert.equal(await page.locator('#selectedJobs').innerText(),'1');
    assert.deepEqual(await page.locator('#jobsBody tr').first().locator('td').evaluateAll(cells=>cells.slice(2,5).map(c=>c.textContent)),['マーケッツ','債券部','トレーダー']);
    await page.locator('[data-job="MS:JR036102"]').click();
    assert.equal(await page.locator('#dialogClassification .classification-details strong').nth(2).innerText(),'トレーダー');
    await page.mouse.move(10,10);await page.locator('#jobDialog').screenshot({path:path.join(output,'xva-correction.png')});
    await page.click('#closeDialog');
    checks.push('xVA Trading is a trader in the job table and source dialog');
    await page.click('#resetFilters');await page.selectOption('#breakdown','department');
    await page.mouse.move(10,10);
    await page.locator('#breakdown').locator('..').locator('..').locator('..').screenshot({path:path.join(output,'department-heatmap.png')});
    await page.locator('#rankBody [data-rank="マーケッツ"][data-company="MS"]').click();
    assert.equal(await page.locator('#businessDepartment').inputValue(),'マーケッツ');
    assert.ok(await page.locator('[data-company-filter="MS"]').isChecked());
    await page.selectOption('#breakdown','subdepartment');await page.locator('#rankBody [data-rank="マーケッツ / 株式部"][data-company="MS"]').click();
    assert.equal(await page.locator('#businessSubdepartment').inputValue(),'株式部');
    await page.selectOption('#breakdown','occupation');assert.equal(await page.locator('#breakdownHeading').innerText(),'職種');
    checks.push('department, subdepartment and occupation heatmaps render; cells apply the corresponding filters');
    await page.click('#resetFilters');
    await page.fill('#query','210640571');await page.waitForTimeout(250);
    assert.equal(await page.locator('#selectedJobs').innerText(),'1');
    await page.locator('[data-job="JPM:210640571"]').click();
    assert.ok(await page.locator('#jobDialog').isVisible());
    assert.equal(await page.locator('#dialogData .evidence-row').count(),3);
    assert.ok((await page.locator('#dialogLink').getAttribute('href')).includes('jpmc.fa.oraclecloud.com'));
    const classification=await page.locator('#dialogClassification').innerText();
    for(const text of ['決済・トランザクションバンキング','金融機関向け決済','営業・セールス','公開部門','Payments Sales'])assert.ok(classification.includes(text));
    await page.click('#closeDialog');checks.push('keyword lookup; complete source evidence and official link');
    const downloadPromise=page.waitForEvent('download');await page.click('#downloadCSV');const download=await downloadPromise;
    const file=path.join(output,'download-check.csv');await download.saveAs(file);
    const csv=fs.readFileSync(file,'utf8');assert.ok(csv.includes('period_original'));assert.ok(csv.includes('annual_candidate'));assert.ok(csv.includes('210640571'));
    for(const text of ['business_department','business_subdepartment','occupation_evidence','決済・トランザクションバンキング','金融機関向け決済','営業・セールス'])assert.ok(csv.includes(text));fs.unlinkSync(file);
    checks.push('filtered CSV contains all three labels and provenance, source units, job ID and explicit scenario assumption');
    assert.deepEqual(expected.samples.map(s=>s.id.split(':')[0]),['BOFA','CITI']);
    for(const sample of expected.samples){
      await page.click('#resetFilters');await page.fill('#query',sample.req);await page.waitForTimeout(250);
      await page.locator(`[data-job="${sample.id}"]`).first().click();
      assert.equal(await page.locator('#dialogData .evidence-row').count(),sample.ranges);
      assert.equal(new URL(await page.locator('#dialogLink').getAttribute('href')).host,sample.host);
      await page.click('#closeDialog');
    }
    checks.push(`added banks: ${expected.samples.map(s=>s.id).join(', ')} show every saved pay range and the official link`);
    await page.click('#resetFilters');
    for(const c of companies)await page.uncheck(`[data-company-filter="${c}"]`);
    assert.equal(await page.locator('#selectedRanges').innerText(),'0');assert.ok(await page.locator('#downloadCSV').isDisabled());
    checks.push('empty selection shows a proper empty state');
    await page.click('#resetFilters');await page.selectOption('#status','missing');
    assert.equal(await page.locator('#selectedRanges').innerText(),'0');assert.ok((await page.locator('#tableCount').innerText()).includes('求人'));
    checks.push('missing-pay jobs remain inspectable without entering salary statistics');
    await page.click('#resetFilters');await page.locator('#rankBody [data-rank="Vice President"][data-company="MS"]').click();
    assert.equal(await page.locator('#rank').inputValue(),'Vice President');assert.ok(await page.locator('[data-company-filter="MS"]').isChecked());assert.equal(await page.locator('[data-company-filter="GS"]').isChecked(),false);
    checks.push('heatmap click applies company and title-rank filters');
    await page.click('#resetFilters');await page.locator('#distributionChart').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'desktop-charts.png')});
    await page.locator('#boxChart').locator('..').screenshot({path:path.join(output,'salary-comparison.png')});
    await page.click('#themeButton');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'dark-analysis.png')});
    checks.push('dark appearance renders');
    const svgTextSizes=await page.locator('#coverageChart svg text').evaluateAll(nodes=>nodes.map(n=>({font:parseFloat(getComputedStyle(n).fontSize),scale:n.getScreenCTM().a})));
    const minRenderedText=Math.min(...svgTextSizes.map(t=>t.font*t.scale));
    assert.ok(minRenderedText>=12,`Overview labels shrank to ${minRenderedText}px`);
    const mobile=await context.newPage();await mobile.setViewportSize({width:390,height:844});
    mobile.on('pageerror',e=>errors.push(e.message));await mobile.goto(url,{waitUntil:'domcontentloaded'});await mobile.waitForFunction(()=>window.reportReady===true,{timeout:7000});
    const width=await mobile.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
    assert.ok(width.document<=width.viewport+2,JSON.stringify(width));
    await mobile.screenshot({path:path.join(output,'mobile-top.png')});
    await mobile.locator('#boxChart').scrollIntoViewIfNeeded();await mobile.screenshot({path:path.join(output,'mobile-chart.png')});
    checks.push('390px mobile layout has no page-wide overflow; charts retain local scroll');
    await context.setOffline(true);await page.selectOption('#program','all');await page.selectOption('#mode','year');
    assert.equal(Number((await page.locator('#selectedRanges').innerText()).replaceAll(',','')),expected.year.ranges);
    checks.push('embedded data and controls work with the network offline');
    assert.equal(errors.length,0,errors.join('\n'));
    const result={url,ok:true,checks,jsErrors:errors,defaultComparisonText:defaultView,minOverviewTextPixels:minRenderedText,mobileWidth:width};
    fs.writeFileSync(path.join(output,'browser-checks.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
