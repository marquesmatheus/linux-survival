# ☣ LINUX SURVIVAL — Faculdade Serra Dourada • Semana Acadêmica 2026 • Prof. Me. Matheus Marques

Simulador de terminal Linux tema zumbi para uma aula de 2h. Flask + HTML/CSS/JS + JSON. **Sem banco de dados.**

## Rodar local
```bash
cd LinuxSurvival
pip install -r requirements.txt
python app.py
```
Acesse http://127.0.0.1:5000

## Publicar no PythonAnywhere (grátis)
1. Suba a pasta `LinuxSurvival` para `/home/SEU_USUARIO/LinuxSurvival`
2. Crie um app Flask manual com Python 3.10+
3. No arquivo WSGI, cole o conteúdo de `pythonanywhere_wsgi.py` (troque SEU_USUARIO)
4. `pip install flask` no console + Reload

## Estrutura
- `app.py` — terminal simulado em Python (pwd, ls, cd, mkdir, touch, echo, cat, head/tail/wc/sort/uniq, cp -r, mv, rm, chmod, sudo, nano/vim, alias, ln, less, file, ps, kill -9, top, find, grep, pipes, `&`, tar, df/du/free, id/who, systemctl/journalctl, ip/ping/ssh/scp/curl/wget, apt/dnf, chown, man, history...) + missões + desafios + quiz + ranking
- `conteudo.json` — 15 missões + 8 desafios (99 atividades, roteiro 2h em 7 atos) + quiz final com 60 questões pt-BR sorteadas (anti-cola, alternativas balanceadas)
- `results.json` — ranking do Quiz Final (nome, acertos, %, data)
- `templates/` + `static/` — front zumbi tema claro + terminal CRT (fotos: Wikimedia Commons)

## Resetar ranking
Deixe `results.json` com `[]`.
