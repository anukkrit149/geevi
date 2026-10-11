/* All parsing/rendering stays in the browser. No PDF scripting or external AI. */
(function(root){
  let libraryPromise,dbPromise;const loaded=new Map();
  const base=new URL('./vendor/pdfjs/',document.currentScript.src).href;
  async function library(){if(!libraryPromise)libraryPromise=import(base+'pdf.min.mjs').then(lib=>{lib.GlobalWorkerOptions.workerSrc=base+'pdf.worker.min.mjs';return lib;});return libraryPromise;}
  function database(){if(!dbPromise)dbPromise=new Promise((resolve,reject)=>{const r=indexedDB.open('casebook-pdf-library',1);r.onupgradeneeded=()=>r.result.createObjectStore('documents',{keyPath:'hash'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(Error('PDF storage is unavailable. Enable browser storage before uploading.'));});return dbPromise;}
  async function put(value){const db=await database();await new Promise((resolve,reject)=>{const tx=db.transaction('documents','readwrite');tx.objectStore('documents').put(value);tx.oncomplete=resolve;tx.onerror=()=>reject(Error('Could not save the original PDF locally. Free browser storage and retry.'));tx.onabort=()=>reject(Error('Local PDF storage was interrupted.'));});}
  async function get(hash){const db=await database();return new Promise((resolve,reject)=>{const r=db.transaction('documents').objectStore('documents').get(hash);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(Error('Could not read the original PDF from browser storage.'));});}
  async function parse(bytes){const lib=await library();const task=lib.getDocument({data:new Uint8Array(bytes.slice(0)),isEvalSupported:false,enableXfa:false,cMapUrl:base+'cmaps/',cMapPacked:true,standardFontDataUrl:base+'standard_fonts/',wasmUrl:base+'wasm/',useSystemFonts:false});
    task.onPassword=()=>{task.destroy();};
    try{return await timeout(task.promise,15000,()=>task.destroy());}catch(error){if(/timed out/i.test(error.message))throw error;if(/password|destroyed/i.test(error.message))throw Error('Password-protected PDFs are not supported. Upload an authorized unprotected copy.');throw Error('This PDF could not be read. Check the file or export a fresh PDF.');}
  }
  function timeout(promise,ms,onTimeout){let timer;return Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>{onTimeout?.();reject(Error('PDF processing timed out. Try a smaller or simpler article PDF.'));},ms);})]).finally(()=>clearTimeout(timer));}
  async function upload(file,onProgress=()=>{},options={}){
    if(location.protocol==='file:')throw Error('Open the local HTTP preview to use PDF uploads; direct file browsing cannot load the PDF worker.');
    if(!file||file.size>15*1024*1024)throw Error('Choose a PDF no larger than 15 MB.');
    if(!file.name.toLowerCase().endsWith('.pdf'))throw Error('Choose a .pdf file.');
    const bytes=await file.arrayBuffer();if(!new TextDecoder().decode(bytes.slice(0,1024)).includes('%PDF-'))throw Error('The selected file is not a readable PDF.');
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
    const doc=await parse(bytes);let pages=[],layouts=[],total=0;
    try{
      if(doc.numPages>100)throw Error('This prototype accepts at most 100 pages. Upload an article-sized PDF.');
      for(let n=1;n<=doc.numPages;n++){
        onProgress(`Reading page ${n} of ${doc.numPages}…`);
        const page=await timeout(doc.getPage(n),10000,()=>doc.destroy());
        const text=await timeout(page.getTextContent(),15000,()=>doc.destroy());
        // Keep whitespace stable for offsets. This is extraction order, not guaranteed visual reading order.
        const lib=await library(),viewport=page.getViewport({scale:1});let value='';const segments=[];
        for(const item of text.items.filter(x=>typeof x.str==='string')){
          const start=value.length;value+=item.str+(item.hasEOL?'\n':' ');
          const t=lib.Util.transform(viewport.transform,item.transform),h=Math.hypot(t[2],t[3]),angle=Math.atan2(t[1],t[0]);
          const ascent=text.styles[item.fontName]?.ascent??0.8,dx=Math.cos(angle),dy=Math.sin(angle),w=item.width*viewport.scale;
          const x=t[4]+h*ascent*dy,y=t[5]-h*ascent*dx;
          const corners=[[x,y],[x+w*dx,y+w*dy],[x-h*dy,y+h*dx],[x+w*dx-h*dy,y+w*dy+h*dx]];
          const xs=corners.map(p=>p[0]),ys=corners.map(p=>p[1]);
          segments.push({start,end:start+item.str.length,text:item.str,box:[Math.min(...xs)/viewport.width,Math.min(...ys)/viewport.height,(Math.max(...xs)-Math.min(...xs))/viewport.width,(Math.max(...ys)-Math.min(...ys))/viewport.height]});
        }
        layouts.push({width:viewport.width,height:viewport.height,segments});
        total+=value.length;if(total>300000)throw Error('Extracted text exceeds the 300,000-character prototype limit. Use a shorter article PDF.');pages.push(value);page.cleanup();
      }
      if(!options.allowImageOnly&&pages.every(p=>p.trim().length<30))throw Error('No usable text layer found. This PDF appears scanned or image-only; OCR is required before extraction.');
      const emptyPages=pages.map((p,i)=>p.trim().length<30?i+1:null).filter(Boolean);
      const meta=await doc.getMetadata().catch(()=>({info:{}}));
      const found=PdfEvidence.suggestions(pages);
      const result={hash,name:file.name,title:meta.info?.Title||file.name.replace(/\.pdf$/i,''),size:file.size,pageCount:doc.numPages,pages,layouts,candidates:found.candidates,extractor:'PDF.js 5.6.205 + passage finder v1',warnings:[...(emptyPages.length?[`Pages ${emptyPages.join(', ')} have little or no readable text. Scan text and figure/table content may be missing.`]:[]),...(found.capped?[`Showing 80 of ${found.total} matching passages. Search the full extracted pages to add others.`]:[]),'Passages are keyword suggestions, not a complete or clinically validated study extraction. Multi-column layouts and tables can be misordered; inspect the original page.'],createdAt:new Date().toISOString()};
      await put({hash,bytes,name:file.name});const previous=loaded.get(hash);if(previous&&previous!==doc)await previous.destroy();loaded.set(hash,doc);return result;
    }catch(error){await doc.destroy();throw error;}
  }
  async function page(hash,n,canvas){let doc=loaded.get(hash);if(!doc){const saved=await get(hash);if(!saved)throw Error('Original PDF unavailable in this browser. Re-upload the identical file to restore it before reviewing sources.');doc=await parse(saved.bytes);loaded.set(hash,doc);}
    const p=await doc.getPage(n);const view=p.getViewport({scale:1});const scale=Math.min(1.6,1000/view.width);const vp=p.getViewport({scale});canvas.width=vp.width;canvas.height=vp.height;await p.render({canvasContext:canvas.getContext('2d'),viewport:vp}).promise;return true;
  }
  root.PdfReader={upload,page,get};
})(globalThis);
