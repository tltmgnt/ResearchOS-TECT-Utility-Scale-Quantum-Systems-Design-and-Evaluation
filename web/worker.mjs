import{analyze}from'./model.mjs';
self.onmessage=e=>{try{self.postMessage({result:analyze(e.data)})}catch(error){self.postMessage({error:error.message})}};
