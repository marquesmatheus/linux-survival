"""LINUX SURVIVAL — Apocalipse Terminal | Flask + JSON (sem banco) | pt-BR."""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os, random, shlex, unicodedata, difflib
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "linux-survival-apocalipse-2026")

BASE = os.path.dirname(os.path.abspath(__file__))
CONTEUDO_FILE = os.path.join(BASE, "conteudo.json")
RESULTS_FILE = os.path.join(BASE, "results.json")

def load_conteudo():
    with open(CONTEUDO_FILE, encoding="utf-8") as f:
        return json.load(f)

def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    try:
        with open(RESULTS_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []

def save_results(r):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)

# ---------------- FILESYSTEM VIRTUAL ----------------

def fs_inicial():
    return {"type": "dir", "children": {
        "home": {"type": "dir", "children": {
            "sobrevivente": {"type": "dir", "children": {
                "diario.txt": {"type": "file", "content": "Dia 1: o mundo caiu. Se eu morrer, meu pwd é /home/sobrevivente.\nDica: use ls -a para ver o que escondi de você.\n"},
                ".escondido": {"type": "file", "content": "Você achou! Arquivos com ponto são ocultos. Os infectados nunca olham aqui. Guarde munição em .nomes assim.\n"},
                "resgate.sh": {"type": "file", "content": "#!/bin/bash\necho 'Sinal de resgate enviado!'\n"},
            }}}},
        "cidade": {"type": "dir", "children": {
            "hospital": {"type": "dir", "children": {
                "mapa.txt": {"type": "file", "content": "MAPA DO ABRIGO\n1. Volte para casa: cd ~\n2. Crie seu abrigo: mkdir abrigo\n3. Crie o inventário: touch suprimentos.txt\n4. Registre: echo agua > suprimentos.txt\nO helicóptero só pousa para quem termina as 10 missões.\n"},
                "remedios.txt": {"type": "file", "content": "paracetamol\nbandagem\nagua oxigenada\n"},
            }},
            "escola": {"type": "dir", "children": {
                "livros.txt": {"type": "file", "content": "Manual de sobrevivência Linux, cap. 1: nunca rode rm -rf / ...\n"},
            }},
        }},
        "base": {"type": "dir", "children": {
            "comunicado.txt": {"type": "file", "content": "Frequência de resgate: canal 443. Ping resgate para testar.\n"},
        }},
        "var": {"type": "dir", "children": {
            "log": {"type": "dir", "children": {
                "syslog": {"type": "file", "content": "08:00 abrigo iniciado: turno da manhã\n08:01 kernel: zumbi pid 666 devorando CPU\n08:02 radio: resgate escutando na porta 443\n08:03 nginx: servindo o mapa em /cidade/hospital\n08:04 aviso: disco em 40% — ainda cabe suprimento\n"},
            }}}},
    }}

def norm(path, cwd):
    if not path or path == "~":
        return "/home/sobrevivente"
    if path.startswith("~/"):
        path = "/home/sobrevivente/" + path[2:]
    if not path.startswith("/"):
        path = cwd.rstrip("/") + "/" + path
    parts = []
    for p in path.split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if parts:
                parts.pop()
        else:
            parts.append(p)
    return "/" + "/".join(parts)

def get_node(fs, path):
    if path == "/":
        return fs
    node = fs
    for p in [x for x in path.split("/") if x]:
        if node.get("type") != "dir" or p not in node["children"]:
            return None
        node = node["children"][p]
    return node

def parent_of(fs, path):
    path = path.rstrip("/") or "/"
    if path == "/":
        return None, None
    idx = path.rfind("/")
    pname = path[:idx] or "/"
    nome = path[idx+1:]
    pnode = get_node(fs, pname)
    return pnode, nome

ESSENCIAIS = {
    "/home/sobrevivente/diario.txt": "Dia 1: o mundo caiu. Se eu morrer, meu pwd é /home/sobrevivente.\nDica: use ls -a para ver o que escondi de você.\n",
    "/home/sobrevivente/.escondido": "Você achou! Arquivos com ponto são ocultos. Os infectados nunca olham aqui. Guarde munição em .nomes assim.\n",
    "/home/sobrevivente/resgate.sh": "#!/bin/bash\necho 'Sinal de resgate enviado!'\n",
    "/cidade/hospital/mapa.txt": "MAPA DO ABRIGO\n1. Volte para casa: cd ~\n2. Crie seu abrigo: mkdir abrigo\n3. Crie o inventário: touch suprimentos.txt\n4. Registre: echo agua > suprimentos.txt\nO helicóptero só pousa para quem termina as 10 missões.\n",
    "/cidade/hospital/remedios.txt": "paracetamol\nbandagem\nagua oxigenada\n",
    "/cidade/escola/livros.txt": "Manual de sobrevivência Linux, cap. 1: nunca rode rm -rf / ...\n",
    "/base/comunicado.txt": "Frequência de resgate: canal 443. Ping resgate para testar.\n",
    "/var/log/syslog": "08:00 abrigo iniciado: turno da manhã\n08:01 kernel: zumbi pid 666 devorando CPU\n08:02 radio: resgate escutando na porta 443\n08:03 nginx: servindo o mapa em /cidade/hospital\n08:04 aviso: disco em 40% — ainda cabe suprimento\n",
}

def garantir_essenciais(fs):
    """Restaura arquivos do jogo se sumirem (apagados sem querer, sessão antiga...).

    Só repõe o que está FALTANDO; nunca apaga nem sobrescreve nada do aluno.
    """
    for caminho, conteudo in ESSENCIAIS.items():
        if get_node(fs, caminho) is not None:
            continue
        partes = [p for p in caminho.split("/") if p]
        node = fs
        for parte in partes[:-1]:
            nxt = node.get("children", {}).get(parte)
            if nxt is None or nxt.get("type") != "dir":
                nxt = {"type": "dir", "children": {}}
                node["children"][parte] = nxt
            node = nxt
        if partes[-1] not in node.get("children", {}):
            node["children"][partes[-1]] = {"type": "file", "content": conteudo}

def ensure_session_fs():
    if "fs" not in session:
        session["fs"] = fs_inicial()
    if "cwd" not in session:
        session["cwd"] = "/home/sobrevivente"
    if "history" not in session:
        session["history"] = []
    if "executados" not in session:
        session["executados"] = []
    if "visitados" not in session:
        session["visitados"] = [session.get("cwd", "/home/sobrevivente")]
    garantir_essenciais(session["fs"])
    session["fs"] = session["fs"]

PROCESSOS_FAKE = [
    ("1", "root", "init apocalipse"),
    ("42", "sobrevivente", "bash --sobreviver"),
    ("666", "zumbi", "infectado devorando CPU"),
    ("777", "zumbi", "infectado farejando RAM"),
    ("1024", "sobrevivente", "radio --frequencia 443"),
]

def cmd_ls(fs, cwd, flags, alvo, stdin=None):
    target = norm(alvo or ".", cwd)
    node = get_node(fs, target)
    if node is None:
        return f"ls: não foi possível acessar '{alvo}': Arquivo ou diretório inexistente 💀\n"
    if node["type"] == "file":
        return alvo + "\n"
    mostra_oculto = "a" in flags
    detalhado = "l" in flags
    items = sorted(node["children"].items())
    if not detalhado:
        nomes = [n for n, _ in items if mostra_oculto or not n.startswith(".")]
        if not nomes:
            return ""
        return "  ".join(nomes) + "\n"
    out = []
    for nome, n in items:
        if not mostra_oculto and nome.startswith("."):
            continue
        if n["type"] == "dir":
            out.append(f"drwxr-xr-x  2 sobrevivente grupo  4096 {nome}/")
        else:
            tam = len(n.get("content", ""))
            out.append(f"-rw-r--r--  1 sobrevivente grupo  {tam:>5} {nome}")
    return ("\n".join(out) + "\n") if out else ""

def exec_simples(fs, cwd, tokens, stdin):
    """Executa UM comando (sem pipe). Retorna (saida, novo_cwd, mudou_fs)."""
    if not tokens:
        return "", cwd, False
    c, args = tokens[0], tokens[1:]
    flags = "".join(a[1:] for a in args if a.startswith("-") and len(a) > 1)
    paths = [a for a in args if not a.startswith("-")]

    if c in ("help", "ajuda"):
        return ("COMANDOS DE SOBREVIVÊNCIA 🧟\n"
                "  pwd · whoami · hostname · ls [-la] · cd · mkdir · touch · echo · cat · head · tail\n"
                "  cp · mv · rm · rmdir · chmod · sudo · ps · kill · find · grep · history · tree\n"
                "  tar · ping · ssh · curl · apt · df · free · uname · clear · help\n"
                "Digite `missao` para ver seu objetivo atual. TAB não funciona aqui — digite com calma.\n", cwd, False)
    if c == "missao":
        return "Abra o painel da missão ao lado 👉 complete as tarefas marcadas e volte aqui para praticar.\n", cwd, False
    if c == "pwd":
        return cwd + "\n", cwd, False
    if c == "whoami":
        return "sobrevivente\n", cwd, False
    if c == "hostname":
        return "abrigo-apocalipse\n", cwd, False
    if c in ("date", "data"):
        return datetime.now().strftime("%a %d %b %Y %H:%M:%S 🧟 horário de Brasília (horário do apocalipse)\n"), cwd, False
    if c == "uname":
        return "Linux abrigo-apocalipse 6.8.0-survival x86_64 GNU/Linux\n", cwd, False
    if c == "history":
        h = session.get("history", [])
        return "".join(f"  {i+1}  {x}\n" for i, x in enumerate(h[-30:])) or "(vazio — você ainda não lutou)\n", cwd, False
    if c == "tree":
        alvo = norm(paths[0] if paths else ".", cwd)
        node = get_node(fs, alvo)
        if not node or node["type"] != "dir":
            return "tree: pasta inexistente\n", cwd, False
        linhas = ["."]
        def walk(n, pref):
            for i, (nome, f) in enumerate(sorted(n["children"].items())):
                if nome.startswith("."):
                    continue
                last = i == len(n["children"]) - 1
                linhas.append(pref + ("└── " if last else "├── ") + nome)
                if f["type"] == "dir":
                    walk(f, pref + ("    " if last else "│   "))
        walk(node, "")
        return "\n".join(linhas) + "\n", cwd, False
    if c == "ls":
        return cmd_ls(fs, cwd, flags, paths[0] if paths else None), cwd, False
    if c == "cd":
        dest = paths[0] if paths else "~"
        t = norm(dest, cwd)
        n = get_node(fs, t)
        if n is None and not dest.startswith(("/", "~")):
            # ajuda didática: tenta a partir da raiz (ex: cd cidade/hospital -> /cidade/hospital)
            t2 = norm("/" + dest, cwd)
            n2 = get_node(fs, t2)
            if n2 is not None:
                t, n = t2, n2
        if n is None:
            return f"bash: cd: {dest}: Arquivo ou diretório inexistente 💀\nDica: use `pwd` para ver onde está e `ls /` para ver a raiz.\n", cwd, False
        if n["type"] != "dir":
            return f"bash: cd: {dest}: Não é um diretório\n", cwd, False
        return "", t, False
    if c == "mkdir":
        if not paths:
            return "mkdir: falta o nome da pasta. Ex: mkdir abrigo\n", cwd, False
        for p in paths:
            t = norm(p, cwd)
            if get_node(fs, t):
                return f"mkdir: '{p}' já existe — os infectados já moram aí 🧟\n", cwd, False
            par, nome = parent_of(fs, t)
            if par is None or par["type"] != "dir":
                return f"mkdir: não foi possível criar '{p}': caminho inválido (tente mkdir -p)\n", cwd, False
            par["children"][nome] = {"type": "dir", "children": {}}
        return "", cwd, True
    if c == "touch":
        if not paths:
            return "touch: falta o nome. Ex: touch suprimentos.txt\n", cwd, False
        for p in paths:
            t = norm(p, cwd)
            ex = get_node(fs, t)
            if ex and ex["type"] == "file":
                continue
            if ex:
                return f"touch: '{p}' já existe como pasta\n", cwd, False
            par, nome = parent_of(fs, t)
            if par is None or par["type"] != "dir":
                return f"touch: '{p}': diretório inexistente\n", cwd, False
            par["children"][nome] = {"type": "file", "content": ""}
        return "", cwd, True
    if c == "cat":
        if not paths:
            if stdin is not None:
                return stdin, cwd, False
            return "cat: informe o arquivo. Ex: cat mapa.txt\n", cwd, False
        out = ""
        for p in paths:
            n = get_node(fs, norm(p, cwd))
            if n is None:
                out += f"cat: {p}: Arquivo ou diretório inexistente 💀\n" + dica_typo(fs, cwd, p)
            elif n["type"] == "dir":
                out += f"cat: {p}: É um diretório\n"
            else:
                out += n.get("content", "")
                if not out.endswith("\n"):
                    out += "\n"
        return out, cwd, False
    if c in ("head", "tail", "wc", "sort"):
        alvo = paths[-1] if paths and not paths[-1].startswith("-") else None
        texto = stdin or ""
        if alvo:
            n = get_node(fs, norm(alvo, cwd))
            if not n or n["type"] != "file":
                return f"{c}: arquivo inexistente\n", cwd, False
            texto = n.get("content", "")
        linhas = texto.splitlines()
        if c == "head":
            return "\n".join(linhas[:10]) + ("\n" if linhas else ""), cwd, False
        if c == "tail":
            return "\n".join(linhas[-10:]) + ("\n" if linhas else ""), cwd, False
        if c == "wc":
            return f"  {len(linhas)}  {sum(len(l.split()) for l in linhas)}  {len(texto)} {alvo or ''}\n", cwd, False
        return "\n".join(sorted(linhas)) + ("\n" if linhas else ""), cwd, False
    if c == "grep":
        pats = [a for a in args if not a.startswith("-")]
        if not pats and stdin is None:
            return "grep: uso: grep 'texto' arquivo  |  comando | grep texto\n", cwd, False
        pat = pats[0] if pats else ""
        pat = pat.strip("'\"")
        fontes = []
        if len(pats) > 1:
            for p in pats[1:]:
                n = get_node(fs, norm(p, cwd))
                if n and n["type"] == "file":
                    fontes.append(n.get("content", ""))
                else:
                    return f"grep: {p}: Arquivo inexistente\n", cwd, False
        elif stdin is not None:
            fontes.append(stdin)
        else:
            return "grep: informe o arquivo ou use pipe. Ex: ps aux | grep zumbi\n", cwd, False
        achadas = [l for f in fontes for l in f.splitlines() if normaliza(pat) in normaliza(l)]
        if not achadas and "zumbi" in pat.lower() and stdin:
            return "(nenhum zumbi aqui... por enquanto 🧟)\n", cwd, False
        return ("\n".join(achadas) + "\n") if achadas else "", cwd, False
    if c == "find":
        alvo = norm(paths[0] if paths and not paths[0].startswith("-") else ".", cwd)
        nome_pat = ""
        if "-name" in args:
            i = args.index("-name")
            if i + 1 < len(args):
                nome_pat = args[i+1].strip("'\"*")
        base = get_node(fs, alvo)
        if not base or base["type"] != "dir":
            return "find: caminho inválido\n", cwd, False
        ach = []
        def walk(n, p):
            for nome, f in n["children"].items():
                fp = (p.rstrip("/") + "/" + nome)
                rel = fp if cwd == "/" else fp.replace(cwd, ".", 1) if fp.startswith(cwd) else fp
                if not nome_pat or nome_pat.replace("*", "") in nome:
                    ach.append(rel)
                if f["type"] == "dir":
                    walk(f, fp)
        walk(base, alvo)
        return ("\n".join(sorted(ach)) + "\n") if ach else "(nada encontrado... continue procurando 🔦)\n", cwd, False
    if c == "cp":
        if len(paths) < 2:
            return "cp: uso: cp origem destino. Ex: cp a.txt abrigo/\n", cwd, False
        src = get_node(fs, norm(paths[0], cwd))
        if src is None:
            return f"cp: '{paths[0]}': inexistente\n" + dica_typo(fs, cwd, paths[0]), cwd, False
        dt = norm(paths[1], cwd)
        dn = get_node(fs, dt)
        if dn and dn["type"] == "dir":
            nome_src = paths[0].rstrip("/").split("/")[-1]
            dn["children"][nome_src] = json.loads(json.dumps(src))
        else:
            par, nome = parent_of(fs, dt)
            if par is None or par["type"] != "dir":
                return "cp: destino inválido\n", cwd, False
            par["children"][nome] = json.loads(json.dumps(src))
        return "", cwd, True
    if c == "mv":
        if len(paths) < 2:
            return "mv: uso: mv origem destino\n", cwd, False
        st = norm(paths[0], cwd)
        src = get_node(fs, st)
        if src is None:
            return f"mv: '{paths[0]}': inexistente 💀\n" + dica_typo(fs, cwd, paths[0]), cwd, False
        dt = norm(paths[1], cwd)
        dn = get_node(fs, dt)
        spar, snome = parent_of(fs, st)
        if dn and dn["type"] == "dir":
            dn["children"][snome] = src
        else:
            dpar, dnome = parent_of(fs, dt)
            if dpar is None or dpar["type"] != "dir":
                return "mv: destino inválido\n", cwd, False
            dpar["children"][dnome] = src
        del spar["children"][snome]
        return "", cwd, True
    if c == "rm":
        if not paths:
            return "rm: informe o que apagar. Ex: rm lixo.txt (sem lixeira! ⚠️)\n", cwd, False
        rec = "r" in flags or "R" in flags
        out = ""
        for p in paths:
            t = norm(p, cwd)
            n = get_node(fs, t)
            if n is None:
                if "f" in flags:
                    continue
                out += f"rm: '{p}': inexistente\n" + dica_typo(fs, cwd, p)
                continue
            if n["type"] == "dir" and not rec:
                out += f"rm: '{p}' é uma pasta — use rm -r (com cuidado!)\n"
                continue
            if t in ("/", "/home", "/home/sobrevivente") and "f" in flags:
                return "⛔ O sistema te impediu de destruir o abrigo! `rm -rf /` mataria todo mundo. LIÇÃO APRENDIDA.\n", cwd, False
            par, nome = parent_of(fs, t)
            del par["children"][nome]
        return out, cwd, True
    if c == "rmdir":
        if not paths:
            return "rmdir: informe a pasta vazia\n", cwd, False
        t = norm(paths[0], cwd)
        n = get_node(fs, t)
        if not n or n["type"] != "dir":
            return "rmdir: pasta inexistente\n", cwd, False
        if n["children"]:
            return "rmdir: pasta não está vazia — use rm -r (com cuidado)\n", cwd, False
        par, nome = parent_of(fs, t)
        del par["children"][nome]
        return "", cwd, True
    if c == "chmod":
        if len(paths) < 2:
            return "chmod: uso: chmod 700 diario.txt  (r=4 w=2 x=1: dono/grupo/outros)\n", cwd, False
        n = get_node(fs, norm(paths[-1], cwd))
        if not n:
            return "chmod: arquivo inexistente\n", cwd, False
        return f"Permissões de '{paths[-1]}' ajustadas para {paths[0]} 🔒 (abrigo trancado!)\n", cwd, False
    if c == "ps":
        return ("USER         PID COMANDO\n" + "\n".join(f"{u:<12} {p:<4} {cm}" for p, u, cm in PROCESSOS_FAKE) + "\n"), cwd, False
    if c == "top":
        return "🧟 MONITOR DE INFECTADOS (top simulado)\nCPU: zumbi:666 98% | MEM: zumbi:777 61%\nDica: mate com `kill 666`.\n", cwd, False
    if c == "kill":
        alvos = [p for p in paths if not p.startswith("-")]
        forcado = any(p in ("-9", "-KILL") for p in paths)
        if not alvos:
            return "kill: informe o PID. Ex: kill 666 (liste com ps aux)\n", cwd, False
        if alvos[0] in ("666", "777"):
            extra = " sem conversa (-9 respected 🫡)" if forcado else " (-9 seria força total: kill -9)"
            return f"💥 Infectado {alvos[0]} eliminado! A base agradece.{extra}\n", cwd, False
        return f"kill: processo {alvos[0]} inexistente ou já era zumbi...\n", cwd, False
    if c == "tar":
        if "c" in flags or "czf" in flags or any("c" in a for a in args if a.startswith("-")):
            return "📦 Backup compactado! (backup.tar.gz criado no abrigo — helicóptero aprovado)\n", cwd, True
        if "x" in flags:
            return "📂 Backup extraído!\n", cwd, False
        return "tar: uso: tar -czf backup.tar.gz pasta  |  tar -xzf backup.tar.gz\n", cwd, False
    if c == "ping":
        dest = paths[0] if paths else "8.8.8.8"
        return (f"PING {dest} (apocalipse): 64 bytes — tempo=12ms ttl=64\n"
                f"64 bytes — tempo=9ms\n64 bytes — tempo=11ms\n--- {dest}: 3 pacotes, 0% perda. SINAL VIVO! 📡\n"), cwd, False
    if c == "ssh":
        return "🔐 Conectando via SSH... (simulado) Bem-vindo à BASE! Canal seguro. Profissionais vivem no ssh user@servidor.\n", cwd, False
    if c in ("curl", "wget"):
        return "⬇️  Baixando suprimentos da rede... 100% (simulado). Na vida real: curl -O https://... / wget url\n", cwd, False
    if c == "apt":
        if not paths:
            return "apt: uso: sudo apt update | sudo apt install htop\n", cwd, False
        if "update" in args:
            return "📦 Lendo lista de pacotes... Tudo atualizado. (Na prova: update ≠ upgrade)\n", cwd, False
        if "install" in args:
            return f"✅ Pacote instalado (simulado): {' '.join(paths[1:] if paths[0]=='install' else paths)} — sem sudo não vai em produção!\n", cwd, False
        return "apt: comando simulado com sucesso.\n", cwd, False
    if c in ("systemctl", "service"):
        return "⚙️  Serviço verificado (simulado). Real: systemctl status nginx | restart app | enable app\n", cwd, False
    if c in ("df", "du", "free", "ip", "ifconfig"):
        mapa = {
            "df": "Sist. Arq.  Tam  Usado Disp  Uso% /\n/dev/sda1   20G   8G   12G   40% (espaço de sobra para suprimentos)\n",
            "du": "4,0K  ./abrigo\n8,0K  .\n(dica real: du -sh * | sort -h)\n",
            "free": "Mem: 4G total, 1G livre — mate zumbis para liberar RAM 🧟\n",
            "ip": "eth0: 192.168.0.100/24 (abrigo-apocalipse na rede)\n",
            "ifconfig": "eth0: 192.168.0.100  Másc:255.255.255.0  UP\n",
        }
        return mapa[c], cwd, False
    if c == "man":
        return "📖 Manual: man <comando> mostra ajuda completa. Aqui use `help`. Na vida real, `man ls` é ouro.\n", cwd, False
    if c == "echo":
        return " ".join(args) + "\n", cwd, False
    if c == "nano":
        alvo = paths[0] if paths else "diario.txt"
        return (f"📝 nano {alvo} aberto! (simulado)\nEscreva à vontade: Ctrl+O salva, Ctrl+X sai.\nÉ o editor mais manso do terminal.\n", cwd, False)
    if c in ("vim", "vi"):
        alvo = paths[0] if paths else "diario.txt"
        return (f"📝 vim {alvo} aberto! (simulado)\nAperte i para EDITAR, ESC para sair do modo edição.\nPara sair sem salvar, digite :q! e Enter.\n", cwd, False)
    if c in (":q!", ":q"):
        return "💾 Saído sem salvar (:q!). O vim perdoa os apressados.\n", cwd, False
    if c in (":wq", ":x", ":w"):
        return "💾 Salvo! (:wq salva e sai. Digno de veterano.)\n", cwd, False
    if c == "uniq":
        alvo = paths[-1] if paths and not paths[-1].startswith("-") else None
        texto = stdin or ""
        if alvo:
            n = get_node(fs, norm(alvo, cwd))
            if not n or n["type"] != "file":
                return "uniq: arquivo inexistente\n", cwd, False
            texto = n.get("content", "")
        out, prev = [], None
        for l in texto.splitlines():
            if l != prev:
                out.append(l)
            prev = l
        return ("\n".join(out) + "\n") if out else "", cwd, False
    if c == "alias":
        if any("=" in a for a in args):
            return f"✅ Atalho criado! (simulado — grave no ~/.bashrc para valer sempre)\n", cwd, False
        return "alias ll='ls -la'  (seus atalhos)\nDica: alias nome='comando longo' + ~/.bashrc = para sempre.\n", cwd, False
    if c == "id":
        return "uid=1000(sobrevivente) gid=1000(sobrevivente) grupos=1000(sobrevivente),27(sudo)\n", cwd, False
    if c == "groups":
        return "sobrevivente sudo\n", cwd, False
    if c == "who":
        return "sobrevivente tty1   2026-09-23 08:00\nbase        pts/0  2026-09-23 08:05 (resgate)\n", cwd, False
    if c in ("adduser", "useradd"):
        nome = paths[-1] if paths else None
        if not nome or nome.startswith("-"):
            return "adduser: uso: sudo adduser nome (na real exige sudo)\n", cwd, False
        return f"✅ Usuário '{nome}' criado com pasta e senha! (simulado)\n", cwd, False
    if c == "passwd":
        return "🔑 Nova senha: ********\nSenha atualizada! (simulado — a senha nunca aparece na tela)\n", cwd, False
    if c == "journalctl":
        return ("📜 -- diário do sistema (journalctl simulado) --\n"
                "[ok] abrigo iniciado\n[zumbi] pid 666 devorando CPU\n"
                "[ok] resgate escutando na porta 443\n"
                "Real: journalctl -u nginx -f acompanha o serviço ao vivo.\n"), cwd, False
    if c == "scp":
        if len(paths) < 2:
            return "scp: uso: scp arquivo ana@servidor:/destino\n", cwd, False
        return "🔐 Copiando via SSH... 100% (simulado). Criptografado de ponta a ponta.\n", cwd, False
    if c == "file":
        if not paths:
            return "file: uso: file foto.jpg (descobre o tipo real)\n", cwd, False
        n = get_node(fs, norm(paths[0], cwd))
        if n is None:
            return f"file: {paths[0]}: inexistente\n", cwd, False
        if n["type"] == "dir":
            return f"{paths[0]}: diretório\n", cwd, False
        nome = paths[0].lower()
        tipo = "texto ASCII"
        if nome.endswith(".sh"):
            tipo = "script shell"
        elif nome.endswith((".jpg", ".png")):
            tipo = "imagem JPEG/PNG"
        elif nome.endswith(".gz"):
            tipo = "compactado gzip"
        return f"{paths[0]}: {tipo} (o conteúdo não mente; a extensão às vezes sim)\n", cwd, False
    if c in ("dnf", "yum"):
        return "📦 Gerenciador Fedora/RHEL (simulado). Real: sudo dnf install htop\nDebian/Ubuntu = apt | Fedora = dnf | Arch = pacman.\n", cwd, False
    if c == "ln":
        if len(paths) < 2:
            return "ln: uso: ln -s origem destino (cria um atalho)\n", cwd, False
        origem, dest = paths[-2], paths[-1]
        if get_node(fs, norm(origem, cwd)) is None:
            return f"ln: '{origem}': inexistente\n", cwd, False
        t = norm(dest, cwd)
        if get_node(fs, t):
            return f"ln: '{dest}' já existe\n", cwd, False
        par, nome = parent_of(fs, t)
        if par is None or par["type"] != "dir":
            return "ln: destino inválido\n", cwd, False
        par["children"][nome] = {"type": "file", "content": f"[atalho simbólico -> {origem}]\n"}
        return f"🔗 Atalho criado: {dest} -> {origem}\n", cwd, True
    if c in ("less", "more"):
        if not paths:
            return "less: uso: less arquivo (navega com setas, q sai)\n", cwd, False
        n = get_node(fs, norm(paths[0], cwd))
        if not n or n["type"] != "file":
            return "less: arquivo inexistente\n", cwd, False
        return n.get("content", "") + "\n--- (less: fim; no terminal real, q sai) ---\n", cwd, False
    if c in ("chown", "chgrp"):
        if len(paths) < 2:
            return f"{c}: uso: {c} dono arquivo (na real exige sudo/root)\n", cwd, False
        return f"👑 Dono de '{paths[-1]}' ajustado para '{paths[0]}'! (simulado)\n", cwd, False
    if c in ("exit", "sair", "logout"):
        return "__SAIR__", cwd, False
    return f"bash: {c}: comando não encontrado... os zumbis riram de você 🧟 (tente `help`)\n", cwd, False

def executar_linha(fs, cwd, linha):
    linha = linha.strip()
    if not linha:
        return "", cwd, False
    # redirecionamento echo ... > / >> arquivo
    redir = None
    if ">>" in linha and not linha.startswith("grep"):
        partes = linha.split(">>", 1)
        linha, redir = partes[0].strip(), ("append", partes[1].strip())
    elif ">" in linha and "|" not in linha:
        # cuidado com comparações; aqui só suportamos echo ... > arq
        partes = linha.split(">", 1)
        if len(partes) == 2 and partes[0].strip().startswith("echo"):
            linha, redir = partes[0].strip(), ("over", partes[1].strip())
    # sudo: remove e executa
    usa_sudo = linha.startswith("sudo ")
    if usa_sudo:
        linha = linha[5:].strip()
    # segundo plano: comando &
    fundo = False
    if linha.endswith("&") and not linha.endswith("&&"):
        fundo = True
        linha = linha[:-1].strip()
    # pipe
    etapas = [e.strip() for e in linha.split("|")]
    entrada = None
    out = ""
    mudou = False
    for et in etapas:
        try:
            toks = shlex.split(et)
        except Exception:
            toks = et.split()
        if toks and toks[0] == "echo" and len(etapas) == 1 and not redir:
            out, cwd, m = exec_simples(fs, cwd, toks, entrada)
        else:
            out, cwd, m = exec_simples(fs, cwd, toks, entrada)
        entrada = out
        mudou = mudou or m
        if out == "__SAIR__":
            return "__SAIR__", cwd, mudou
    if redir:
        modo, alvo = redir
        t = norm(alvo.strip("'\""), cwd)
        n = get_node(fs, t)
        if n and n["type"] == "dir":
            return f"bash: {alvo}: É um diretório\n", cwd, False
        if n is None:
            par, nome = parent_of(fs, t)
            if par is None or par["type"] != "dir":
                return f"bash: {alvo}: diretório inexistente\n", cwd, False
            par["children"][nome] = {"type": "file", "content": ""}
            n = par["children"][nome]
        texto = entrada if entrada is not None else ""
        if modo == "over":
            n["content"] = texto
        else:
            n["content"] = n.get("content", "") + texto
        mudou = True
        return "", cwd, mudou
    if usa_sudo and out:
        out = out.rstrip("\n") + "  [sudo: poder de root usado 👑]\n"
    if usa_sudo and not out:
        out = "(sudo executado como root 👑)\n"
    if fundo and out and out != "__SAIR__":
        out = out.rstrip("\n") + "\n[job em 2º plano — terminal livre para continuar 😎]\n"
    return out, cwd, mudou

# ---------------- PROGRESSO DAS MISSÕES ----------------

def normaliza(s):
    """Minúsculas sem acento: 'água' == 'AGUA'. O terminal perdoa o teclado."""
    s = unicodedata.normalize("NFD", s or "")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").casefold()

def buscar_no_mundo(fs, valor, cwd):
    """Acha nós em QUALQUER lugar da árvore: caminho exato ou nome relativo.

    O aluno pode ter criado o arquivo em outra pasta; o que importa é que existe.
    """
    valor = (valor or "").strip().strip("/")
    cands = {norm(valor, b) for b in [cwd, "/home/sobrevivente", "/"]}
    sufixo = "/" + valor
    achados = []

    def walk(node, path):
        if path in cands or (valor and path.endswith(sufixo)):
            achados.append(node)
        if node.get("type") == "dir":
            for nome, f in node.get("children", {}).items():
                walk(f, path + "/" + nome if path != "/" else "/" + nome)

    walk(fs, "/")
    return achados

def dica_typo(fs, cwd, alvo):
    """Sugere o nome parecido quando o aluno erra uma letra (kit.tx → kit.txt)."""
    if "/" in alvo:
        base, nome = alvo.rsplit("/", 1)
        base = norm(base or ".", cwd)
    else:
        base, nome = cwd, alvo
    d = get_node(fs, base)
    if not d or d.get("type") != "dir" or not nome:
        return ""
    perto = difflib.get_close_matches(nome, list(d.get("children", {}).keys()), n=2, cutoff=0.6)
    if perto:
        return "🤔 Quis dizer `" + "` ou `".join(perto) + "`? Confira com `ls`.\n"
    return ""

def tarefa_ok(t, fs, cwd, executados):
    v = t.get("valida", {})
    tipo = v.get("tipo")
    if tipo == "comando":
        agulha = v.get("contem", "")
        if agulha.isalnum() and len(agulha) <= 3:
            # palavra curta: casa por token inteiro (evita 'mkdir' validar 'id')
            for e in executados:
                try:
                    toks = shlex.split(e)
                except Exception:
                    toks = e.split()
                if agulha in toks:
                    return True
            return False
        return any(agulha in e for e in executados)
    if tipo == "comando_seq":
        seq = v.get("contem", [])
        idx = 0
        for e in executados:
            if idx < len(seq) and seq[idx] in e:
                idx += 1
        return idx == len(seq)
    if tipo == "dir_atual":
        alvo = v.get("valor", "")
        visitados = session.get("visitados", [])
        return cwd == alvo or alvo in visitados
    if tipo == "dir_existe":
        return any(n.get("type") == "dir" for n in buscar_no_mundo(fs, v.get("valor", ""), cwd))
    if tipo == "arq_existe":
        return any(n.get("type") == "file" for n in buscar_no_mundo(fs, v.get("valor", ""), cwd))
    if tipo == "arq_contem":
        alvo = normaliza(v.get("contem", ""))
        return any(n.get("type") == "file" and alvo in normaliza(n.get("content", ""))
                   for n in buscar_no_mundo(fs, v.get("valor", ""), cwd))
    if tipo == "arq_com_texto":
        return any(n.get("type") == "file" and len(n.get("content", "").strip()) >= 4
                   for n in buscar_no_mundo(fs, v.get("valor", ""), cwd))
    return False

def progresso(fs, cwd, executados):
    c = load_conteudo()
    out = {}
    for m in c["missoes"] + c.get("desafios", []):
        feitos = [tarefa_ok(t, fs, cwd, executados) for t in m["tarefas"]]
        out[str(m["id"])] = {"feitos": feitos, "total": len(feitos), "prontos": sum(feitos)}
    return out

# ---------------- QUIZ ----------------
LETTERS = ["A", "B", "C", "D"]

def scoped_quiz():
    return load_conteudo()["quiz"]

def build_shuffle(qs, seed):
    rng = random.Random(seed)
    order = rng.sample(range(len(qs)), len(qs))
    perms = [rng.sample(range(len(q["opcoes"])), len(q["opcoes"])) for q in qs]
    return order, perms

def effective_quiz():
    qs = scoped_quiz()
    seed = session.get("seed")
    if seed is None:
        order = list(range(len(qs)))
        perms = [list(range(len(q["opcoes"]))) for q in qs]
    else:
        order, perms = build_shuffle(qs, seed)
    eff = []
    for qi in order:
        q = qs[qi]
        perm = perms[qi]
        eff.append({"id": q["id"], "tema": q["tema"], "titulo": q["titulo"],
                    "opcoes": [q["opcoes"][i] for i in perm],
                    "correta": perm.index(q["correta"]),
                    "explicacao": q["explicacao"]})
    return eff

# ---------------- ROTAS ----------------

@app.route("/", methods=["GET", "POST"])
def index():
    c = load_conteudo()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()[:30]
        if not nome:
            return render_template("index.html", c=c, erro="Escolha seu nickname para entrar! ⚡",
                                   top=[])
        session.clear()
        session["user"] = nome
        session["fs"] = fs_inicial()
        session["cwd"] = "/home/sobrevivente"
        session["history"] = []
        session["executados"] = []
        session["visitados"] = ["/home/sobrevivente"]
        session["seed"] = random.randrange(2 ** 31)
        session["quiz_index"] = 0
        session["answers"] = []
        session["saved"] = False
        return redirect(url_for("mapa"))
    res = load_results()
    rkey = lambda r: (-r.get("percentual", 0), -r.get("acertos", 0))
    top = sorted([x for x in res if x.get("modo", "quiz") == "quiz"], key=rkey)[:10]
    return render_template("index.html", c=c, top=top, erro=None)

@app.route("/mapa")
def mapa():
    if "user" not in session:
        return redirect(url_for("index"))
    c = load_conteudo()
    ensure_session_fs()
    prog = progresso(session["fs"], session["cwd"], session.get("executados", []))
    pm = [prog.get(str(m["id"]), {"prontos": 0, "total": len(m["tarefas"])}) for m in c["missoes"]]
    pd = [prog.get(str(d["id"]), {"prontos": 0, "total": len(d["tarefas"])}) for d in c.get("desafios", [])]
    total_ok = sum(v["prontos"] for v in pm) + sum(v["prontos"] for v in pd)
    total = sum(v["total"] for v in pm) + sum(v["total"] for v in pd)
    xp = sum(d.get("xp", 100) for d, v in zip(c.get("desafios", []), pd) if v["prontos"] == v["total"])
    return render_template("mapa.html", c=c, prog=prog, total_ok=total_ok, total=total,
                           xp=xp, user=session["user"])

@app.route("/missao/<int:mid>")
def missao(mid):
    if "user" not in session:
        return redirect(url_for("index"))
    c = load_conteudo()
    m = next((x for x in c["missoes"] if x["id"] == mid), None)
    if not m:
        return redirect(url_for("mapa"))
    ensure_session_fs()
    prog = progresso(session["fs"], session["cwd"], session.get("executados", []))
    ids = [x["id"] for x in c["missoes"]]
    i = ids.index(mid)
    anterior = ids[i-1] if i > 0 else None
    proxima = ids[i+1] if i < len(ids)-1 else None
    st = prog.get(str(mid), {"feitos": [False]*len(m["tarefas"])})
    return render_template("missao.html", m=m, st=st, anterior=anterior, proxima=proxima, user=session["user"])

@app.route("/terminal")
def terminal():
    if "user" not in session:
        return redirect(url_for("index"))
    ensure_session_fs()
    return render_template("terminal.html", user=session["user"])

@app.route("/api/exec", methods=["POST"])
def api_exec():
    if "user" not in session:
        return jsonify({"output": "Sessão expirada. Volte ao início.", "cwd": "/"}), 401
    ensure_session_fs()
    data = request.get_json(force=True, silent=True) or {}
    cmd = (data.get("cmd") or "")[:500]
    fs, cwd = session["fs"], session["cwd"]
    hist, ex = session.get("history", []), session.get("executados", [])
    if cmd.strip() == "clear":
        hist.append("clear"); session["history"] = hist[-200:]
        return jsonify({"output": "__CLEAR__", "cwd": cwd})
    if cmd.strip() in ("",):
        return jsonify({"output": "", "cwd": cwd})
    out, novo_cwd, mudou = executar_linha(fs, cwd, cmd)
    hist.append(cmd); ex.append(cmd)
    session["history"] = hist[-200:]
    session["executados"] = ex[-500:]
    session["cwd"] = novo_cwd
    vis = session.get("visitados", [])
    if novo_cwd not in vis:
        vis.append(novo_cwd)
        session["visitados"] = vis[-50:]
    if mudou:
        session["fs"] = fs
    if out == "__SAIR__":
        return jsonify({"output": "Saindo do abrigo... volte vivo! 🧟", "cwd": novo_cwd})
    c = load_conteudo()
    prog = progresso(session["fs"], session["cwd"], session.get("executados", []))
    return jsonify({"output": out, "cwd": novo_cwd, "prog": prog})

@app.route("/api/estado")
def api_estado():
    if "user" not in session:
        return jsonify({}), 401
    ensure_session_fs()
    c = load_conteudo()
    prog = progresso(session["fs"], session["cwd"], session.get("executados", []))
    return jsonify({"cwd": session["cwd"], "prog": prog, "history": session.get("history", [])[-10:]})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    session["fs"] = fs_inicial()
    session["cwd"] = "/home/sobrevivente"
    session["history"] = []
    session["executados"] = []
    session["visitados"] = ["/home/sobrevivente"]
    return jsonify({"ok": True, "cwd": session["cwd"]})

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user" not in session:
        return redirect(url_for("index"))
    qs = effective_quiz()
    idx = session.get("quiz_index", 0)
    ans = session.get("answers", [])
    if request.method == "POST":
        if idx >= len(qs):
            return redirect(url_for("resultado"))
        try:
            esc = int(request.form.get("escolha", -1))
        except ValueError:
            esc = -1
        ans.append(esc); session["answers"] = ans
        session["quiz_index"] = idx + 1
        session["last"] = {"pos": idx, "escolha": esc}
        return redirect(url_for("feedback"))
    if idx >= len(qs):
        return redirect(url_for("resultado"))
    q = qs[idx]
    return render_template("quiz.html", q=q, idx=idx, total=len(qs),
                           progresso=int(idx/len(qs)*100), letters=LETTERS,
                           user=session["user"], modo_nome="Quiz Final ⭐")

@app.route("/feedback")
def feedback():
    if "user" not in session or "last" not in session:
        return redirect(url_for("quiz"))
    eff = effective_quiz()
    pos = session["last"].get("pos", 0)
    if pos < 0 or pos >= len(eff):
        return redirect(url_for("quiz"))
    q = eff[pos]
    esc = session["last"].get("escolha", -1)
    last = {"n": pos+1, "tema": q["tema"], "titulo": q["titulo"], "opcoes": q["opcoes"],
            "correta": q["correta"], "escolha": esc, "acertou": esc == q["correta"], "explicacao": q["explicacao"]}
    idx = session.get("quiz_index", 0)
    return render_template("feedback.html", last=last, letters=LETTERS, user=session["user"],
                           idx=idx, total=len(eff), progresso=int(idx/len(eff)*100), ultima=idx >= len(eff),
                           url_proxima=url_for("quiz"), url_fim=url_for("resultado"))

@app.route("/resultado")
def resultado():
    if "user" not in session:
        return redirect(url_for("index"))
    qs = effective_quiz()
    ans = session.get("answers", [])
    if len(ans) < len(qs):
        return redirect(url_for("quiz"))
    ac = sum(1 for i, a in enumerate(ans) if a == qs[i]["correta"])
    total = len(qs)
    pct = round(ac/total*100, 1)
    revisao = [{"n": n+1, "tema": q["tema"], "titulo": q["titulo"], "opcoes": q["opcoes"],
                "correta": q["correta"], "escolha": a, "acertou": a == q["correta"],
                "explicacao": q["explicacao"]} for n, (q, a) in enumerate(zip(qs, ans))]
    if not session.get("saved"):
        r = load_results()
        r.append({"nome": session["user"], "acertos": ac, "total": total, "percentual": pct,
                  "modo": "quiz", "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
        save_results(r); session["saved"] = True
    if pct == 100: msg = "LENDÁRIO! 🏆 Você zerou o Quiz Final!"
    elif pct >= 80: msg = "NÍVEL SÊNIOR! 🚀 As empresas te querem!"
    elif pct >= 60: msg = "NÍVEL PLENO! 🔥 Mandou muito bem!"
    elif pct >= 40: msg = "BOM COMEÇO! 💪 Revise a trilha e jogue de novo!"
    else: msg = "NÃO DESISTA! 🌱 Revise a trilha e tente de novo!"
    rank = sorted([x for x in load_results() if x.get("modo", "quiz") == "quiz"],
                  key=lambda r: (-r.get("percentual", 0), -r.get("acertos", 0)))
    pos = next((i+1 for i, r in enumerate(rank) if r["nome"] == session["user"] and r["acertos"] == ac), "-")
    return render_template("result.html", acertos=ac, total=total, percentual=pct, revisao=revisao,
                           letters=LETTERS, user=session["user"], msg=msg, posicao=pos,
                           modo_nome="Quiz Final ⭐", url_rejogar=url_for("reiniciar_quiz"))

@app.route("/desafio/<did>")
def desafio(did):
    if "user" not in session:
        return redirect(url_for("index"))
    c = load_conteudo()
    d = next((x for x in c.get("desafios", []) if str(x["id"]) == str(did)), None)
    if not d:
        return redirect(url_for("mapa"))
    ensure_session_fs()
    prog = progresso(session["fs"], session["cwd"], session.get("executados", []))
    st = prog.get(str(did), {"feitos": [False] * len(d["tarefas"])})
    return render_template("desafio.html", d=d, st=st, user=session["user"])

@app.route("/ranking")
def ranking():
    r = load_results()
    key = lambda x: (-x.get("percentual", 0), -x.get("acertos", 0), x.get("data", ""))
    rank = sorted([x for x in r if x.get("modo", "quiz") == "quiz"], key=key)
    return render_template("ranking.html", ranking=rank, user=session.get("user"))

@app.route("/reiniciar-quiz")
def reiniciar_quiz():
    session["quiz_index"] = 0; session["answers"] = []
    session["saved"] = False; session["seed"] = random.randrange(2 ** 31)
    if "last" in session: del session["last"]
    return redirect(url_for("quiz"))

@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    print("\n🧟 LINUX SURVIVAL em http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
