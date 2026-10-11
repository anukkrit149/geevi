/* Synthetic workflow only. No medical recommendations or real authorizations. */
(function (root) {
  const P=typeof module!=='undefined'&&module.exports?require('./pdf-evidence.js'):root.PdfEvidence;
  const clone = value => JSON.parse(JSON.stringify(value));
  const patients = {
    meera: {name:'Meera', age:42, genetics:'NPM1 mutation reported; FLT3-ITD not detected.', fitness:'Independent; specialist assessment supports intensive treatment.', cardiac:'Organ assessment documented in the fictional baseline.', plan:'Intensive-treatment strategy', explanation:'Your doctor has discussed treatment in hospital. Your care team is arranging the next step.'},
    arun: {name:'Arun', age:74, genetics:'Complex chromosome findings and TP53 mutation reported.', fitness:'Frailty and cardiac disease; current specialist assessment initially pending.', cardiac:'Updated cardiac/fitness assessment pending.', plan:'Lower-intensity strategy', explanation:'Your doctor has discussed a treatment approach that requires close monitoring. Your care team will confirm the setting and next visit.'}
  };
  const library = {
    intensive: {title:'Example A · Intensive-treatment cohort', version:'DEMO-A/1', criterion:'Adults with newly diagnosed non-APL AML, adequate organ assessment and fitness for intensive treatment.', limitations:'Synthetic teaching criteria, not a real study. No measured benefit, survival or toxicity estimates are supplied.'},
    lower: {title:'Example B · Less-intensive-treatment cohort', version:'DEMO-B/1', criterion:'Adults with newly diagnosed non-APL AML judged unsuitable for intensive treatment after documented specialist assessment.', limitations:'Synthetic teaching criteria, not a real study. Age alone is not the selection criterion; this is not a prescribing rule.'}
  };
  function create(id) {return {id,revision:1,assessmentReady:id==='meera',amendments:0,evidence:[],plan:'',rationale:'',explanation:patients[id].explanation,approval:null,history:[],handoff:null,familyAcknowledged:false,events:[]};}
  function log(s,actor,message) {s.events.push({at:new Date().toISOString(),actor,message,revision:s.revision});}
  function revise(s,actor,message) {
    if(s.approval){s.history.push(clone({approval:s.approval,handoff:s.handoff}));s.approval=null;s.handoff=null;s.familyAcknowledged=false;}
    s.revision++;log(s,actor,message);
  }
  function rows(s,type) {
    const a=s.id==='arun',ready=s.assessmentReady;
    return [
      {key:'diagnosis',label:'Disease',criterion:'Non-APL AML',value:'Non-APL AML documented',status:'matches',source:`${s.id.toUpperCase()}-PATH/1 · synthetic diagnostic assessment`},
      {key:'setting',label:'Treatment setting',criterion:'Newly diagnosed',value:'Newly diagnosed; no prior disease-directed treatment in this scenario',status:'matches',source:`${s.id.toUpperCase()}-HISTORY/1 · synthetic intake`},
      {key:'fitness',label:'Functional assessment',criterion:type==='intensive'?'Suitable for intensive treatment':'Unsuitable for intensive treatment',value:!ready?'Current specialist assessment pending':a?'Specialist records intensive treatment as unsuitable':'Specialist records fitness for intensive treatment',status:!ready?'unknown':((type==='intensive')!==a?'matches':'differs'),source:`${s.id.toUpperCase()}-FIT/${ready?2:1} · synthetic specialist assessment`},
      {key:'cardiac',label:'Organ assessment',criterion:type==='intensive'?'Adequate organ assessment for this example cohort':'Documented specialist review of relevant comorbidity',value:!ready?'Awaiting current assessment':a?'Cardiac limitations documented by specialist':'Assessment documents adequate organ function',status:!ready?'unknown':(a&&type==='intensive'?'differs':'matches'),source:`${s.id.toUpperCase()}-ORG/${s.amendments+1} · synthetic organ assessment`}
    ];
  }
  function ensureRole(role,allowed) {if(!allowed.includes(role))throw Error('This action belongs to a different demonstration role.');}
  function attach(s,type,role,reference) {
    ensureRole(role,['oncologist']);
    if(type!=='custom'&&!library[type])throw Error('Unknown example source.');
    if(type!=='custom'&&s.evidence.some(e=>e.type===type))throw Error('This source is already attached.');
    if(type==='custom') {
      if(!reference||!reference.title.trim())throw Error('Enter a reference title.');
      const url=new URL(reference.url);if(!['https:','http:'].includes(url.protocol))throw Error('Use an http or https research link.');
    }
    revise(s,role,'Research reference attached; current packet requires review.');
    s.evidence.push({id:`E${s.evidence.length+1}`,type,title:type==='custom'?reference.title.trim():library[type].title,url:type==='custom'?reference.url:'',version:type==='custom'?'REFERENCE/1':library[type].version,review:null,reviewHistory:[]});
  }
  function review(s,eid,role,input) {
    ensureRole(role,['oncologist']);const e=s.evidence.find(x=>x.id===eid);if(!e)throw Error('Select an attached source.');
    if(!['supporting','conflicting','contextual','not-applicable'].includes(input.disposition))throw Error('Choose a disposition.');
    if(e.type==='custom'&&input.disposition==='supporting')throw Error('A reference-only attachment is contextual in this demo; it has no extracted criteria.');
    if(e.type==='pdf'&&!e.pdf.extractionReview)throw Error('Review the PDF source passages and confirm its extraction first.');
    if(e.type==='pdf'&&input.disposition==='supporting'&&!e.pdf.candidates.some(c=>c.status==='included'&&c.kind==='criterion'&&c.mapping?.field!=='context'))throw Error('Supporting PDF evidence needs at least one source-verified, mapped patient criterion.');
    if(!input.checked)throw Error('Inspect the sources and confirm the review.');
    if(!input.note||input.note.trim().length<12)throw Error('Add a review rationale of at least 12 characters.');
    revise(s,role,`${e.id} applicability review signed (simulation).`);
    if(e.review)e.reviewHistory.push(clone(e.review));
    e.review={at:new Date().toISOString(),signer:'Dr. Rao · demo oncologist',disposition:input.disposition,note:input.note.trim(),rows:e.type==='pdf'?clone(pdfRows(s,e)):e.type==='custom'?[]:clone(rows(s,e.type)),patientVersion:s.amendments+1,extractionVersion:e.pdf?.extractionVersion||null};
  }
  function pdfRows(s,e){return e.pdf.candidates.filter(c=>c.status==='included'&&c.kind==='criterion').map(c=>P.comparison(s,c));}
  function attachPdf(s,pdf,role){
    ensureRole(role,['oncologist']);
    if(!/^[a-f0-9]{64}$/.test(pdf.hash)||!Array.isArray(pdf.pages)||!pdf.pages.length)throw Error('A parsed PDF with a source fingerprint is required.');
    if(s.evidence.some(e=>e.pdf?.hash===pdf.hash))throw Error('This identical PDF is already attached to this patient. Its original file has been restored locally if needed.');
    if(!pdf.candidates.every(c=>P.citationValid(pdf,c)))throw Error('A proposed passage does not match its source page.');
    revise(s,role,'Research PDF attached; extracted passages await review.');
    const data=clone(pdf);data.extractionVersion=1;data.extractionReview=null;data.linkedStrategy='';
    data.candidates=data.candidates.map(c=>({...c,sourceHash:pdf.hash,status:'pending',seen:false}));
    s.evidence.push({id:`E${s.evidence.length+1}`,type:'pdf',title:String(pdf.title).slice(0,250),version:`PDF-${pdf.hash.slice(0,12)}`,pdf:data,review:null,reviewHistory:[]});
  }
  function pdfItem(s,eid){const e=s.evidence.find(e=>e.id===eid&&e.type==='pdf');if(!e)throw Error('Select an uploaded PDF.');return e;}
  function invalidatePdf(s,e,role,message){revise(s,role,message);if(e.review)e.reviewHistory.push(clone(e.review));e.review=null;e.pdf.extractionReview=null;e.pdf.extractionVersion++;}
  function markSourceSeen(s,eid,cid,role){ensureRole(role,['oncologist']);const e=pdfItem(s,eid),c=e.pdf.candidates.find(c=>c.id===cid);if(!c||!P.citationValid(e.pdf,c))throw Error('The passage cannot be verified against this PDF.');c.seen=true;log(s,role,`${e.id}/${c.id} source passage inspected on PDF page ${c.page}.`);}
  function addPassage(s,eid,role,page,quote,kind){
    ensureRole(role,['oncologist']);const e=pdfItem(s,eid),text=e.pdf.pages[page-1];quote=String(quote||'').trim();
    if(!['criterion','result'].includes(kind)||!text||quote.length<12||quote.length>4000||!text.includes(quote))throw Error('Paste an exact 12–4,000 character passage from the selected extracted page.');
    if(e.pdf.candidates.some(c=>c.page===page&&c.quote===quote))throw Error('This source passage is already listed.');
    invalidatePdf(s,e,role,'Additional source passage selected; extraction review reopened.');const start=text.indexOf(quote);
    e.pdf.candidates.push({id:`P${e.pdf.candidates.length+1}`,kind,page,start,end:start+quote.length,quote,status:'pending',seen:false,sourceHash:e.pdf.hash});
  }
  function savePassage(s,eid,cid,role,input){
    ensureRole(role,['oncologist']);const e=pdfItem(s,eid),c=e.pdf.candidates.find(c=>c.id===cid);if(!c||!P.citationValid(e.pdf,c))throw Error('Source passage is not valid.');
    if(!c.seen)throw Error('Open the original PDF page and mark this passage inspected before using it.');
    if(!['criterion','result'].includes(input.kind))throw Error('Choose criterion or result.');
    if(!input.label||input.label.trim().length<4)throw Error('Give this field a clear label or interpretation.');
    if(input.kind==='criterion')P.validateMapping(input.mapping);
    if(input.kind==='result'&&(!input.context||input.context.trim().length<20))throw Error('Explain the population, comparison and limitations, including what is not established.');
    invalidatePdf(s,e,role,`${e.id}/${c.id} extracted field verified against source.`);
    Object.assign(c,{kind:input.kind,label:input.label.trim(),mapping:input.kind==='criterion'?clone(input.mapping):null,result:input.kind==='result'?clone(input.result||{}):null,context:input.context?.trim()||'',status:'included',verifiedBy:'Dr. Rao · demo oncologist',verifiedAt:new Date().toISOString()});
  }
  function dismissPassages(s,eid,role,cid){ensureRole(role,['oncologist']);const e=pdfItem(s,eid);const candidates=e.pdf.candidates.filter(c=>cid?c.id===cid:c.status==='pending');if(!candidates.length)return;invalidatePdf(s,e,role,'Source suggestions dismissed from the decision extraction.');candidates.forEach(c=>c.status='dismissed');}
  function confirmExtraction(s,eid,role,input){
    ensureRole(role,['oncologist']);const e=pdfItem(s,eid),included=e.pdf.candidates.filter(c=>c.status==='included');
    if(!input.checked)throw Error('Confirm the source-review scope and extraction limitations.');
    if(!included.length)throw Error('Verify at least one source passage.');
    if(e.pdf.candidates.some(c=>c.status==='pending'))throw Error('Review or explicitly dismiss the remaining suggestions.');
    if(included.some(c=>!c.seen||!P.citationValid(e.pdf,c)))throw Error('Each included field needs an inspected, exact source passage.');
    if(!included.some(c=>c.kind==='result')&&String(input.noResults||'').trim().length<12)throw Error('State why no study results are included; do not interpret missing results as zero benefit.');
    if(!['intensive','lower','context'].includes(input.strategy))throw Error('Choose the strategy this extraction will inform, or context only.');
    invalidatePdf(s,e,role,'PDF extraction review confirmed; patient-specific applicability review still required.');
    e.pdf.linkedStrategy=input.strategy;e.pdf.extractionReview={at:new Date().toISOString(),by:'Dr. Rao · demo oncologist',version:e.pdf.extractionVersion,scope:'Selected passages only; automated discovery is incomplete. No personal benefit estimate.',noResults:String(input.noResults||'').trim()};
  }
  function amend(s,role) {
    ensureRole(role,['oncologist']);revise(s,role,'New fictional assessment loaded; evidence reviews reopened. Prior approval, if any, remains in history.');
    s.assessmentReady=true;s.amendments++;s.evidence.forEach(e=>{if(e.review)e.reviewHistory.push(clone(e.review));e.review=null;});
  }
  function savePlan(s,role,input) {
    ensureRole(role,['oncologist']);if(!['intensive','lower'].includes(input.plan))throw Error('Choose an example strategy.');
    const value={plan:input.plan,rationale:(input.rationale||'').trim(),explanation:(input.explanation||'').trim()};
    if(value.rationale.length<20)throw Error('Record at least 20 characters of clinical reasoning.');
    if(value.explanation.length<12)throw Error('Add a plain-language explanation.');
    if(value.plan!==s.plan||value.rationale!==s.rationale||value.explanation!==s.explanation){revise(s,role,'Decision draft saved.');Object.assign(s,value);}
  }
  function blockers(s) {
    const b=[];if(!s.evidence.length)b.push('Attach at least one example evidence source.');
    if(s.evidence.some(e=>!e.review))b.push('Sign an applicability review for every attached source.');
    if(!s.assessmentReady)b.push('Resolve the pending specialist assessment in this non-urgent demo.');
    if(!s.plan)b.push('Save the selected example strategy.');
    if(s.rationale.length<20)b.push('Save a decision rationale.');
    if(!s.evidence.some(e=>(e.type===s.plan||(e.type==='pdf'&&e.pdf.linkedStrategy===s.plan))&&e.review?.disposition==='supporting'))b.push('Review source evidence linked to the selected strategy as supporting.');
    if(s.evidence.some(e=>e.type==='pdf'&&!e.pdf.extractionReview))b.push('Confirm source-linked extraction for every attached PDF.');
    const supports=s.evidence.filter(e=>e.review?.disposition==='supporting');
    if(supports.some(e=>e.review.rows.some(r=>r.status==='unknown')))b.push('Resolve unknown parameters in supporting evidence.');
    return b;
  }
  function approve(s,role,confirmed) {
    ensureRole(role,['oncologist']);if(!confirmed)throw Error('Confirm the scope of this simulated sign-off.');
    const b=blockers(s);if(b.length)throw Error(b.join(' '));if(s.approval)throw Error('This version is already signed.');
    const evidence=clone(s.evidence);evidence.forEach(e=>{if(e.pdf){delete e.pdf.pages;delete e.pdf.layouts;e.pdf.candidates=e.pdf.candidates.filter(c=>c.status==='included');}});
    s.approval={packet:`${s.id.toUpperCase()}-V${s.revision}`,revision:s.revision,at:new Date().toISOString(),signer:'Dr. Rao · demo oncologist',snapshot:clone({patient:patients[s.id],patientId:s.id,assessmentReady:s.assessmentReady,amendments:s.amendments,evidence,plan:s.plan,rationale:s.rationale,explanation:s.explanation})};
    log(s,role,`${s.approval.packet} signed (simulation); no medication order or treatment clearance created.`);
  }
  function send(s,role,team,note) {
    ensureRole(role,['oncologist','coordinator']);if(!s.approval||s.approval.revision!==s.revision)throw Error('A current signed packet is required.');
    if(s.handoff)throw Error('This packet already has a handoff.');
    if(!['Haematology inpatient team','Haematology monitoring team'].includes(team))throw Error('Choose a receiving team.');
    if(!note||note.trim().length<12)throw Error('Add the handoff task and required next step.');
    s.handoff={packet:s.approval.packet,team,note:note.trim(),sentAt:new Date().toISOString(),sentBy:role,acceptedAt:null,acceptedBy:null};log(s,role,`Handoff requested from ${team}; not yet accepted.`);
  }
  function accept(s,role,confirmed) {
    ensureRole(role,['careteam']);if(!s.approval||!s.handoff)throw Error('No current signed handoff is available.');
    if(!confirmed)throw Error('Confirm receipt of the current packet.');if(s.handoff.acceptedAt)throw Error('Already acknowledged.');
    s.handoff.acceptedAt=new Date().toISOString();s.handoff.acceptedBy='Nurse Isha · demo receiving team';log(s,role,'Receiving team acknowledged the packet. Clinical delivery checks and actual treatment remain outstanding.');
  }
  function family(s,role) {ensureRole(role,['family']);if(!s.approval)throw Error('No current approved explanation is available.');if(!s.familyAcknowledged){s.familyAcknowledged=true;log(s,role,'Family acknowledged the explanation; no clinical approval or patient consent implied.');}}
  const api={patients,library,create,rows,attach,review,amend,savePlan,blockers,approve,send,accept,family,attachPdf,pdfRows,markSourceSeen,addPassage,savePassage,dismissPassages,confirmExtraction};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.WorkflowModel=api;
})(globalThis);
