# 🚀 GUIA DE INSTALAÇÃO - MAGO TRADER
## Sistema de Controle Remoto de Navegador para VPS Linux

---

## 📋 Índice
1. [Requisitos do Sistema](#requisitos-do-sistema)
2. [Instalação Rápida](#instalação-rápida)
3. [Instalação Passo-a-Passo](#instalação-passo-a-passo)
4. [Configuração](#configuração)
5. [Uso do Sistema](#uso-do-sistema)
6. [Comandos Úteis](#comandos-úteis)
7. [Troubleshooting](#troubleshooting)
8. [Portas Utilizadas](#portas-utilizadas)

---

## 📦 Requisitos do Sistema

### Sistema Operacional
- **Ubuntu 20.04+** ou **Debian 10+**
- Acesso root (sudo)
- Mínimo 2GB RAM
- Mínimo 10GB espaço em disco

### Portas Necessárias
- **3000** - Frontend (React)
- **8001** - Backend API (FastAPI)
- **27017** - MongoDB

### Software (será instalado automaticamente)
- Python 3.9+
- Node.js 18+
- Yarn
- MongoDB 6.0+
- Supervisor
- Playwright + Chromium

---

## ⚡ Instalação Rápida

### Passo 1: Fazer upload do projeto para o VPS

```bash
# Opção A: Via Git (se o repositório for privado, use token de acesso)
cd /home
git clone https://github.com/jjnnbo/teeste.git
cd teeste

# Opção B: Via SCP (do seu computador local)
scp -r /caminho/local/teeste usuario@ip-do-vps:/home/
```

### Passo 2: Executar instalação automática

```bash
cd /home/teeste

# Dar permissão de execução aos scripts
chmod +x *.sh

# Instalar dependências do sistema (como root)
sudo ./install.sh

# Configurar o projeto
sudo ./setup.sh

# Iniciar os serviços
sudo ./start.sh
```

### Passo 3: Configurar firewall (se necessário)

```bash
# Ubuntu/Debian com UFW
sudo ufw allow 3000/tcp
sudo ufw allow 8001/tcp
sudo ufw reload

# CentOS/RHEL com firewalld
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

### Passo 4: Acessar o sistema

Abra seu navegador e acesse:
```
http://SEU_IP_DO_VPS:3000
```

**Pronto! O sistema está funcionando! 🎉**

---

## 📝 Instalação Passo-a-Passo

### 1. Preparar o Ambiente

```bash
# Atualizar o sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Git (se necessário)
sudo apt-get install git -y

# Clonar o projeto
cd /home
git clone https://github.com/jjnnbo/teeste.git
cd teeste
```

### 2. Instalar Dependências do Sistema

O script `install.sh` instala tudo automaticamente:

```bash
sudo ./install.sh
```

**O que este script faz:**
- ✅ Atualiza o sistema
- ✅ Instala Python 3.9+
- ✅ Instala Node.js 18+
- ✅ Instala Yarn
- ✅ Instala MongoDB
- ✅ Instala Supervisor
- ✅ Instala dependências do Playwright/Chromium

**Tempo estimado:** 5-10 minutos

### 3. Configurar o Projeto

```bash
sudo ./setup.sh
```

**O que este script faz:**
- ✅ Instala dependências Python (backend)
- ✅ Instala navegador Chromium do Playwright
- ✅ Instala dependências Node.js (frontend)
- ✅ Configura o Supervisor para gerenciar os processos
- ✅ Cria arquivos de log

**Tempo estimado:** 5-15 minutos (depende da velocidade da internet)

### 4. Configurar Variáveis de Ambiente

#### Backend (.env)

Edite o arquivo `backend/.env`:

```bash
nano backend/.env
```

Conteúdo padrão (já está configurado):
```env
MONGO_URL=mongodb://localhost:27017/
DB_NAME=mago_trader
CORS_ORIGINS=*
HOST=0.0.0.0
PORT=8001
```

#### Frontend (.env)

**IMPORTANTE:** Você precisa configurar o IP do seu VPS!

```bash
nano frontend/.env
```

Altere para o IP/domínio do seu VPS:
```env
# Exemplo com IP
REACT_APP_BACKEND_URL=http://45.123.45.67:8001

# Exemplo com domínio
REACT_APP_BACKEND_URL=https://meusite.com
```

### 5. Iniciar os Serviços

```bash
sudo ./start.sh
```

Você verá algo como:
```
================================================
  MAGO TRADER - Iniciando Serviços
================================================

✓ MongoDB iniciado
✓ Backend iniciado
✓ Frontend iniciado

✓ Todos os serviços foram iniciados!

Status dos serviços:
mago-backend                     RUNNING   pid 1234, uptime 0:00:03
mago-frontend                    RUNNING   pid 1235, uptime 0:00:03

→ Acesse o sistema em: http://SEU_IP:3000
→ Backend API: http://SEU_IP:8001/api
```

---

## ⚙️ Configuração

### Configurar IP Público/Domínio

**Muito Importante:** Para o sistema funcionar corretamente, você precisa configurar o IP do seu VPS no frontend.

```bash
# 1. Descubra o IP do seu VPS
curl ifconfig.me

# 2. Edite o arquivo .env do frontend
nano frontend/.env

# 3. Altere a URL para seu IP
REACT_APP_BACKEND_URL=http://SEU_IP_AQUI:8001

# 4. Reinicie o frontend
sudo ./restart.sh
```

### Configurar com Domínio (Opcional)

Se você tem um domínio:

1. Configure um registro A no seu DNS apontando para o IP do VPS
2. Instale Nginx ou Caddy como reverse proxy
3. Configure SSL/HTTPS com Let's Encrypt

**Exemplo com Nginx:**

```bash
# Instalar Nginx
sudo apt-get install nginx -y

# Criar configuração
sudo nano /etc/nginx/sites-available/mago-trader

# Adicionar:
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ws {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}

# Ativar o site
sudo ln -s /etc/nginx/sites-available/mago-trader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Instalar SSL (Let's Encrypt)
sudo apt-get install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu-dominio.com
```

Depois, atualize o frontend/.env:
```env
REACT_APP_BACKEND_URL=https://seu-dominio.com
```

---

## 🎮 Uso do Sistema

### Iniciar os Serviços
```bash
sudo ./start.sh
```

### Parar os Serviços
```bash
sudo ./stop.sh
```

### Reiniciar os Serviços
```bash
sudo ./restart.sh
```

### Ver Logs em Tempo Real
```bash
sudo ./logs.sh
```

Você verá um menu:
```
Escolha qual log deseja visualizar:
1) Backend
2) Frontend
3) Ambos (split screen)
```

### Verificar Status dos Serviços
```bash
sudo supervisorctl status
```

### Comandos Individuais do Supervisor
```bash
# Reiniciar apenas o backend
sudo supervisorctl restart mago-backend

# Reiniciar apenas o frontend
sudo supervisorctl restart mago-frontend

# Ver logs do backend
sudo tail -f /var/log/supervisor/mago-backend.out.log

# Ver logs do frontend
sudo tail -f /var/log/supervisor/mago-frontend.out.log
```

---

## 🔧 Comandos Úteis

### Verificar se as portas estão abertas
```bash
# Verificar portas em uso
sudo netstat -tulpn | grep -E '3000|8001|27017'

# Ou com ss
sudo ss -tulpn | grep -E '3000|8001|27017'
```

### Testar a API do Backend
```bash
# Health check
curl http://localhost:8001/api/health

# Criar uma sessão
curl -X POST "http://localhost:8001/api/session/create?viewport_width=1280&viewport_height=720&start_url=https://www.google.com"

# Listar sessões ativas
curl http://localhost:8001/api/sessions
```

### Verificar MongoDB
```bash
# Status do MongoDB
sudo systemctl status mongod

# Acessar MongoDB shell
mongosh

# Dentro do MongoDB shell:
use mago_trader
show collections
db.stats()
```

### Limpar dados e reiniciar
```bash
# Parar serviços
sudo ./stop.sh

# Limpar banco de dados (CUIDADO!)
mongosh --eval "db.dropDatabase()" mago_trader

# Limpar logs
sudo rm -f /var/log/supervisor/mago-*.log

# Iniciar novamente
sudo ./start.sh
```

---

## 🐛 Troubleshooting

### Problema: Backend não inicia

**Sintomas:** Backend mostra status FATAL ou ERROR

**Solução:**
```bash
# Ver o erro específico
sudo tail -n 50 /var/log/supervisor/mago-backend.err.log

# Problemas comuns:

# 1. Playwright não instalado
cd backend
python3 -m playwright install chromium --with-deps

# 2. Porta 8001 em uso
sudo lsof -i :8001
# Mate o processo se necessário
sudo kill -9 PID

# 3. MongoDB não está rodando
sudo systemctl start mongod
sudo systemctl status mongod

# Reiniciar
sudo supervisorctl restart mago-backend
```

### Problema: Frontend não compila

**Sintomas:** Frontend mostra erros de compilação

**Solução:**
```bash
# Ver o erro
sudo tail -n 50 /var/log/supervisor/mago-frontend.err.log

# Limpar cache e reinstalar
cd frontend
rm -rf node_modules package-lock.json yarn.lock
yarn install
cd ..
sudo supervisorctl restart mago-frontend
```

### Problema: WebSocket não conecta

**Sintomas:** Frontend não mostra o navegador, fica "Conectando..."

**Solução:**
```bash
# 1. Verificar se o backend está rodando
curl http://localhost:8001/api/health

# 2. Verificar se a URL está correta no frontend
cat frontend/.env
# Deve ser: REACT_APP_BACKEND_URL=http://SEU_IP:8001

# 3. Verificar firewall
sudo ufw status
sudo ufw allow 8001/tcp

# 4. Testar WebSocket manualmente
# Instalar wscat
npm install -g wscat

# Criar sessão primeiro
SESSION_ID=$(curl -X POST "http://localhost:8001/api/session/create" | grep -oP 'session_id":"?\K[^"]+')

# Testar WebSocket
wscat -c ws://localhost:8001/api/ws/$SESSION_ID
```

### Problema: Permissões negadas

**Solução:**
```bash
# Dar permissões corretas aos scripts
chmod +x *.sh

# Dar permissão ao usuário para os arquivos do projeto
sudo chown -R $USER:$USER /home/teeste

# Executar com sudo quando necessário
sudo ./start.sh
```

### Problema: Erro "Cannot find module"

**Solução:**
```bash
# Backend
cd backend
pip3 install -r requirements.txt

# Frontend
cd frontend
yarn install
```

### Problema: Chromium não abre no VPS

**Sintomas:** Erro sobre display ou sandbox

**Solução:**
```bash
# Instalar dependências necessárias
sudo apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libatspi2.0-0 libxshmfence1

# Reinstalar Chromium
cd backend
python3 -m playwright install chromium --with-deps

# Reiniciar
sudo supervisorctl restart mago-backend
```

### Problema: Alta latência / FPS baixo

**Soluções:**
1. Usar VPS mais próximo dos usuários
2. Aumentar recursos do VPS (RAM/CPU)
3. Ajustar qualidade do screenshot no código:
   ```python
   # Em backend/server.py, linha ~293
   screenshot = await session.page.screenshot(
       type="jpeg",
       quality=30,  # Diminuir de 40 para 30
       full_page=False,
       timeout=5000
   )
   ```

### Problema: MongoDB crashando

**Solução:**
```bash
# Aumentar limite de arquivos abertos
sudo nano /etc/security/limits.conf
# Adicionar:
# * soft nofile 64000
# * hard nofile 64000

# Verificar espaço em disco
df -h

# Verificar logs do MongoDB
sudo journalctl -u mongod -n 100

# Reparar MongoDB se necessário
sudo systemctl stop mongod
sudo mongod --repair
sudo systemctl start mongod
```

---

## 🌐 Portas Utilizadas

| Porta  | Serviço           | Descrição                    |
|--------|-------------------|------------------------------|
| 3000   | Frontend (React)  | Interface web do usuário     |
| 8001   | Backend (FastAPI) | API REST                     |
| 8001   | WebSocket         | Streaming em tempo real      |
| 27017  | MongoDB           | Banco de dados               |

**Certifique-se de que essas portas estão abertas no firewall!**

---

## 📊 Monitoramento

### Ver uso de recursos
```bash
# CPU e RAM
htop

# Uso por processo
top -p $(pgrep -d',' -f "mago|uvicorn|node")

# Espaço em disco
df -h

# Uso de rede
iftop
```

### Estatísticas do MongoDB
```bash
mongosh --eval "db.serverStatus()" mago_trader
```

### Número de sessões ativas
```bash
curl http://localhost:8001/api/sessions | jq '.count'
```

---

## 🔄 Atualizar o Sistema

```bash
cd /home/teeste

# Parar serviços
sudo ./stop.sh

# Fazer backup (opcional)
cd ..
tar -czf teeste-backup-$(date +%Y%m%d).tar.gz teeste/

# Atualizar código
cd teeste
git pull

# Reinstalar dependências se necessário
cd backend && pip3 install -r requirements.txt && cd ..
cd frontend && yarn install && cd ..

# Iniciar novamente
sudo ./start.sh
```

---

## 🚀 Melhorias de Performance

### 1. Usar Redis para cache (opcional)
```bash
sudo apt-get install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. Configurar Nginx como load balancer
Para múltiplas instâncias do backend

### 3. Usar PM2 em vez de Supervisor (alternativa)
```bash
npm install -g pm2
pm2 start backend/server.py --interpreter python3 --name mago-backend
pm2 start "cd frontend && yarn start" --name mago-frontend
pm2 save
pm2 startup
```

---

## 📞 Suporte

### Logs importantes para debug:
```bash
# Backend
/var/log/supervisor/mago-backend.out.log
/var/log/supervisor/mago-backend.err.log

# Frontend
/var/log/supervisor/mago-frontend.out.log
/var/log/supervisor/mago-frontend.err.log

# MongoDB
sudo journalctl -u mongod

# Supervisor
sudo tail -f /var/log/supervisor/supervisord.log
```

### Informações do sistema:
```bash
# Versões instaladas
python3 --version
node --version
yarn --version
mongod --version

# Sistema operacional
lsb_release -a

# Memória disponível
free -h

# CPU
lscpu
```

---

## 🎯 Próximos Passos

Depois que o sistema estiver rodando:

1. ✅ **Testar o sistema** acessando http://SEU_IP:3000
2. ✅ **Configurar domínio e SSL** (opcional, mas recomendado)
3. ✅ **Configurar backup automático** do MongoDB
4. ✅ **Adicionar autenticação** se necessário
5. ✅ **Configurar limites** de sessões por IP
6. ✅ **Monitorar recursos** e ajustar conforme necessário

---

## ⚠️ Notas Importantes

1. **Pocketoption.com**: O site pode bloquear IPs de datacenter/VPS. Use VPS com IP residencial se necessário.

2. **Segurança**: Por padrão, não há autenticação. Adicione autenticação antes de usar em produção.

3. **Recursos**: Cada sessão de navegador consome ~200-300MB de RAM. Planeje seu VPS de acordo.

4. **Backup**: Configure backups regulares do MongoDB:
   ```bash
   mongodump --db mago_trader --out /backup/$(date +%Y%m%d)
   ```

5. **SSL**: Sempre use HTTPS em produção para proteger a comunicação.

---

## 📄 Licença

Este sistema foi desenvolvido para uso específico. Verifique os termos de uso do Playwright e dos sites acessados.

---

**Desenvolvido com ❤️ usando FastAPI, React e Playwright**

**Versão:** 1.0.0
**Última atualização:** Dezembro 2024

---

## 🆘 Precisa de Ajuda?

Se você encontrar problemas:

1. Verifique os logs: `sudo ./logs.sh`
2. Verifique o status: `sudo supervisorctl status`
3. Consulte a seção de Troubleshooting
4. Verifique se todas as portas estão abertas
5. Verifique se o IP está configurado corretamente no frontend/.env

**Boa sorte! 🚀**
