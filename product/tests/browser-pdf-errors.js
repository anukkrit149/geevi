(async()=>{
const results=[];
for(const [name,expected]of [['scan',/OCR is required/],['corrupt',/could not be read/],['encrypted',/Password-protected/]]){
 const response=await fetch('tests/fixtures/'+name+'.pdf');
 let message='';try{await PdfReader.upload(new File([await response.blob()],name+'.pdf',{type:'application/pdf'}));}catch(error){message=error.message;}
 if(!expected.test(message))throw Error(name+': unexpected result '+message);results.push({name,message});
}
let missing='';try{await PdfReader.page('b'.repeat(64),1,document.createElement('canvas'));}catch(error){missing=error.message;}
if(!missing.includes('Original PDF unavailable'))throw Error('Missing original must require restoration');results.push({name:'missing original',message:missing});
return {passed:results.length,results};
})()
