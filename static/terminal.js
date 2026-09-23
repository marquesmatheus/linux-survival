// Terminal Linux Survival — fala com o Python (/api/exec)
(function(){
  function initTerminal(bodyId, inputId, promptId){
    const body = document.getElementById(bodyId);
    const input = document.getElementById(inputId);
    const promptEl = document.getElementById(promptId);
    if(!body || !input) return;
    let cwd = "/home/sobrevivente";

    function print(html, cls){
      const div = document.createElement("div");
      if(cls) div.className = cls;
      div.innerHTML = html;
      body.appendChild(div);
      body.scrollTop = body.scrollHeight;
    }
    function esc(s){ return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

    async function run(cmd){
      print(`<span class="prompt">🧟 sobrevivente@abrigo:${esc(cwd)}$</span> <span class="cmd-line">${esc(cmd)}</span>`);
      if(cmd.trim() === "clear"){ body.innerHTML = ""; return; }
      try{
        const r = await fetch("/api/exec", {
          method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({cmd})
        });
        const d = await r.json();
        if(d.output === "__CLEAR__"){ body.innerHTML = ""; }
        else if(d.output){ print(`<pre>${esc(d.output)}</pre>`); }
        if(d.cwd){ cwd = d.cwd; if(promptEl) promptEl.textContent = `🧟 sobrevivente@abrigo:${cwd}$`; }
        if(typeof window.atualizarTarefas === "function" && d.prog) window.atualizarTarefas(d.prog);
      }catch(e){ print("☠️ Falha de rádio (rede). Tente de novo."); }
    }

    print("<pre>🧟 LINUX SURVIVAL v1.0 — terminal do abrigo\nDigite <b>help</b> para ver comandos. Digite <b>missao</b> para lembrar o objetivo.\nDica de pro: use pwd antes de rm. Sempre.</pre>");
    fetch("/api/estado").then(r=>r.json()).then(d=>{
      if(d.cwd){ cwd = d.cwd; if(promptEl) promptEl.textContent = `🧟 sobrevivente@abrigo:${cwd}$`; }
      if(typeof window.atualizarTarefas === "function" && d.prog) window.atualizarTarefas(d.prog);
    });

    input.addEventListener("keydown", e=>{
      if(e.key === "Enter"){
        const v = input.value;
        input.value = "";
        run(v);
      }
    });
    body.addEventListener("click", ()=> input.focus());
  }
  window.initTerminal = initTerminal;
})();
