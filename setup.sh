#!/bin/bash

# Script de Setup - MAGO TRADER
# Configura o projeto após instalação das dependências

set -e

echo "================================================"
echo "  MAGO TRADER - Setup do Projeto"
echo "================================================"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

print_info "Diretório do projeto: $PROJECT_DIR"
echo ""

# 1. Setup Backend
print_info "[1/4] Configurando Backend..."
cd backend

# Instalar dependências Python
print_info "Instalando dependências Python..."
pip3 install -r requirements.txt --quiet

# Instalar navegadores do Playwright
print_info "Instalando navegadores do Playwright..."
python3 -m playwright install chromium --with-deps > /dev/null 2>&1

cd ..
print_success "Backend configurado"

# 2. Setup Frontend
print_info "[2/4] Configurando Frontend..."
cd frontend

# Instalar dependências
print_info "Instalando dependências Node.js (isso pode demorar)..."
yarn install --silent

cd ..
print_success "Frontend configurado"

# 3. Criar configuração do Supervisor
print_info "[3/4] Configurando Supervisor..."

cat > /etc/supervisor/conf.d/mago-trader.conf << EOF
[program:mago-backend]
command=python3 -m uvicorn server:app --host 0.0.0.0 --port 8001
directory=$PROJECT_DIR/backend
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/mago-backend.err.log
stdout_logfile=/var/log/supervisor/mago-backend.out.log
user=$SUDO_USER
environment=PYTHONUNBUFFERED="1"

[program:mago-frontend]
command=yarn start
directory=$PROJECT_DIR/frontend
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/mago-frontend.err.log
stdout_logfile=/var/log/supervisor/mago-frontend.out.log
user=$SUDO_USER
environment=PORT="3000",BROWSER="none"
EOF

print_success "Configuração do Supervisor criada"

# 4. Recarregar Supervisor
print_info "[4/4] Recarregando Supervisor..."
supervisorctl reread > /dev/null
supervisorctl update > /dev/null

print_success "Supervisor atualizado"

echo ""
print_success "============================================"
print_success "  Setup concluído com sucesso!"
print_success "============================================"
echo ""
print_info "Para iniciar os serviços, execute: ./start.sh"
print_info "Para ver os logs: ./logs.sh"
echo ""