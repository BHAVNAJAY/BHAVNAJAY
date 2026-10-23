import http from 'http';import fs from 'fs';import path from 'path';import puppeteer from 'puppeteer-core';
const [,, glb, out, W, H, N, AMP] = process.argv;
fs.mkdirSync(out,{recursive:true});
const srv=http.createServer((q,res)=>{const u=q.url.split('?')[0];
 const f=u==='/model.glb'?glb:u==='/'?'page.html':'.'+u; if(u==='/favicon.ico'){res.statusCode=204;return res.end()}
 try{const d=fs.readFileSync(f);res.setHeader('content-type',f.endsWith('.js')||f.endsWith('.mjs')?'text/javascript':f.endsWith('.html')?'text/html':'application/octet-stream');res.end(d)}catch{res.statusCode=404;res.end()}}).listen(8123);
const b=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:'new',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage();p.on('console',m=>console.log('page:',m.text()));p.on('pageerror',e=>console.log('err',e.message));
await p.setViewport({width:+W,height:+H});
await p.goto(`http://localhost:8123/?w=${W}&h=${H}`);
await p.waitForFunction('window.ready',{timeout:180000});
console.log(JSON.stringify(await p.evaluate('window.info')));
for(let i=0;i<+N;i++){
  const deg=+AMP*Math.sin(2*Math.PI*i/+N);
  const d=await p.evaluate(`window.draw(${deg})`);
  fs.writeFileSync(path.join(out,`m${String(i).padStart(3,'0')}.png`),Buffer.from(d.split(',')[1],'base64'));
}
await b.close();srv.close();
