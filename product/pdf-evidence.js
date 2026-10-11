/* Source-linked suggestions, not semantic extraction or clinical recommendations. */
(function(root){
  const fields={age:{label:'Age',unit:'years',type:'number'},disease:{label:'Disease',type:'text'},setting:{label:'Treatment setting',type:'text'},fitness:{label:'Intensive-treatment fitness',type:'text'},npm1:{label:'NPM1',type:'text'},flt3:{label:'FLT3-ITD',type:'text'},tp53:{label:'TP53',type:'text'},ecog:{label:'ECOG performance status',type:'number'},lvef:{label:'LVEF',type:'number',unit:'%'},context:{label:'Context only — not a patient criterion',type:'context'}};
  function suggestions(pages){
    const found=[];let total=0;
    const criterion=/\b(eligib|inclusion|exclusion|excluded|patients? (?:were )?(?:aged|age)|aged?\s*\d|ECOG|unfit|unsuitable|fitness|eligible|enrol|enroll)/i;
    const result=/\b(overall survival|progression.free|complete remission|response rate|hazard ratio|adverse events?|follow.up|median survival|confidence interval|mortality|results)/i;
    pages.forEach((text,index)=>{
      // Sentence/paragraph boundaries only. Reading order and tables require visual review.
      const re=/[\s\S]+?(?:[.!?](?=\s|$)|\n\s*\n|$)/g;let match;
      while((match=re.exec(text))){const raw=match[0],quote=raw.trim();if(quote.length<20)continue;
        const kind=criterion.test(quote)?'criterion':result.test(quote)?'result':null;if(!kind)continue;total++;
        if(found.length>=80)continue;
        const start=match.index+raw.indexOf(quote);
        found.push({id:`P${found.length+1}`,kind,page:index+1,start,end:start+quote.length,quote,status:'pending',seen:false});
      }
    });
    return {candidates:found,total,capped:total>80};
  }
  function citationValid(pdf,c){return Number.isInteger(c.page)&&c.page>=1&&c.page<=pdf.pages.length&&Number.isInteger(c.start)&&Number.isInteger(c.end)&&c.start>=0&&c.end>c.start&&pdf.pages[c.page-1].slice(c.start,c.end)===c.quote;}
  function patientValue(s,key){
    const a=s.id==='arun';
    const values={age:a?74:42,disease:'AML',setting:'newly diagnosed',fitness:s.assessmentReady?(a?'unfit':'fit'):null,npm1:a?null:'mutated',flt3:a?null:'not detected',tp53:a?'mutated':null,ecog:null,lvef:null};
    return values[key]??null;
  }
  function comparison(s,c){
    const m=c.mapping||{},f=fields[m.field],value=patientValue(s,m.field);let status='unknown';
    if(f?.type==='context')status='not-applicable';
    else if(f&&value!==null){
      let match=false;
      if(f.type==='number'){
        const n=Number(m.value);match=m.op==='gte'?value>=n:m.op==='lte'?value<=n:m.op==='range'?value>=n&&value<=Number(m.upper):value===n;
      }else match=String(value).toLowerCase()===String(m.value).trim().toLowerCase();
      if(m.polarity==='exclude')match=!match;status=match?'matches':'differs';
    }
    return {key:c.id,label:f?.label||'Unmapped criterion',criterion:c.label||c.quote,value:value===null?'Not documented in this fictional patient':String(value)+(f?.unit?' '+f.unit:''),status,source:`${s.id.toUpperCase()} · synthetic ${f?.label||'patient'} assessment · evidence v${s.amendments+1}`,citation:{hash:c.sourceHash,page:c.page,start:c.start,end:c.end,quote:c.quote},mapping:m};
  }
  function validateMapping(m){
    const f=fields[m?.field];if(!f)throw Error('Choose the patient parameter to compare.');
    if(f.type==='context')return;
    if(!['include','exclude'].includes(m.polarity))throw Error('Choose inclusion or exclusion logic.');
    if(f.type==='number'){
      if(!['eq','gte','lte','range'].includes(m.op)||String(m.value).trim()===''||!Number.isFinite(Number(m.value)))throw Error('Enter a valid numeric criterion and operator.');
      if(m.op==='range'&&(String(m.upper).trim()===''||!Number.isFinite(Number(m.upper))||Number(m.upper)<Number(m.value)))throw Error('Enter an upper bound at least as large as the lower bound.');
    }else if(m.op!=='eq'||!String(m.value||'').trim())throw Error('Use an exact text value for this parameter.');
  }
  const api={fields,suggestions,citationValid,comparison,validateMapping};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PdfEvidence=api;
})(globalThis);
