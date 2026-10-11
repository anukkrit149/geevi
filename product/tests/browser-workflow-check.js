(()=>{
const results=[];
function assert(ok,msg){if(!ok)throw Error(msg);results.push(msg)}
function click(sel){const e=document.querySelector(sel);if(!e)throw Error('Missing '+sel);if(e.disabled)throw Error('Disabled '+sel);e.click();}
function change(id,value){const e=document.getElementById(id);e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}));}
function field(form,name,value){const e=document.querySelector('#'+form+' [name="'+name+'"]');if(e.type==='checkbox')e.checked=value;else e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}));}
function submit(id){const f=document.getElementById(id);if(!f.checkValidity())throw Error('Invalid form '+id);f.requestSubmit();}
for(const patient of ['meera','arun']){
change('patient',patient);change('role','oncologist');click('#reset');click('#confirm-reset');
click('[data-attach="intensive"]');click('[data-attach="lower"]');click('[data-go="matching"]');
if(patient==='arun'){
assert(document.querySelector('#screen').innerText.includes('Unknown'),'Arun exposes pending criteria');
click('[data-go="decision"]');assert(document.getElementById('approve-button').disabled,'Arun cannot sign an incomplete packet');
click('[data-go="matching"]');click('[data-action="amend"]');
}
for(const [eid,type] of [['E1','intensive'],['E2','lower']]){
change('evidence-select',eid);
const supporting=(patient==='meera'&&type==='intensive')||(patient==='arun'&&type==='lower');
field('review-form','disposition',supporting?'supporting':'conflicting');
field('review-form','note',supporting?'Reviewed synthetic patient sources: these demo population criteria support the selected strategy.':'The alternative cohort differs in fitness or organ criteria; recorded as conflicting context, not selected.');
field('review-form','checked',true);submit('review-form');
assert(document.querySelector('#screen').innerText.includes('Reviewed as'),patient+' '+eid+' review saved');
}
click('[data-go="decision"]');
field('plan-form','plan',patient==='meera'?'intensive':'lower');
field('plan-form','rationale','Clinician reviewed both fictional cohorts, specialist fitness and alternatives. This is a scenario decision, not a drug prescription.');
field('plan-form','explanation','Your team has reviewed your information and will confirm the next care appointment.');
submit('plan-form');assert(!document.getElementById('approve-button').disabled,patient+' sign enabled only after complete saved review');
field('approve-form','confirmed',true);submit('approve-form');assert(document.querySelector('.sign-stamp'),patient+' signed snapshot visible');
change('role','coordinator');field('handoff-form','note','Please acknowledge this signed packet and coordinate the approved next step; verify current orders in the source system.');submit('handoff-form');
assert(document.querySelector('#screen').innerText.includes('Not yet accepted'),patient+' sending does not imply acceptance');
change('role','careteam');field('accept-form','confirmed',true);submit('accept-form');
assert(document.querySelector('#screen').innerText.includes('treatment has not been administered'),patient+' acknowledgement is distinct from treatment');
change('role','family');assert(!document.querySelector('#approve-form')&&!document.querySelector('#accept-form'),patient+' family view has no clinical controls');click('[data-action="family"]');
change('role','oncologist');click('[data-go="audit"]');click('[data-action="amend"]');
assert(document.querySelector('#patient-header').innerText.includes('Review reopened'),patient+' amendment reopens review');
assert(document.querySelector('#screen').innerText.includes('preserved snapshot'),patient+' old signed packet preserved');
click('[data-go="handoff"]');assert(document.querySelector('#screen').innerText.includes('No current signed packet'),patient+' old approval cannot authorize new handoff');
}
change('patient','meera');change('role','oncologist');click('[data-go="audit"]');
return {passed:results.length,results};
})()
