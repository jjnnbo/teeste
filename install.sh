#!/bin/bash

# Script de Instalação - MAGO TRADER
# Para VPS Linux (Ubuntu/Debian)

set -e

echo "================================================"
echo "  MAGO TRADER - Instalação Automática"
echo "================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para print colorido
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    print_error "Por favor, execute como root (use sudo)"
    exit 1
fi

print_info "Iniciando instalação..."
echo ""

# 1. Atualizar sistema
print_info "[1/8] Atualizando sistema..."
apt-get update -qq
print_success "Sistema atualizado"

# 2. Instalar dependências básicas
print_info "[2/8] Instalando dependências básicas..."
apt-get install -y -qq curl wget git build-essential software-properties-common > /dev/null 2>&1
print_success "Dependências básicas instaladas"

# 3. Instalar Python 3.9+
print_info "[3/8] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    apt-get install -y python3 python3-pip python3-venv
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION instalado"

# 4. Instalar Node.js 18+
print_info "[4/8] Instalando Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
    apt-get install -y nodejs > /dev/null 2>&1
fi
NODE_VERSION=$(node --version)
print_success "Node.js $NODE_VERSION instalado"

# 5. Instalar Yarn
print_info "[5/8] Instalando Yarn..."
if ! command -v yarn &> /dev/null; then
    npm install -g yarn > /dev/null 2>&1
fi
YARN_VERSION=$(yarn --version)
print_success "Yarn $YARN_VERSION instalado"

# 6. Instalar MongoDB
print_info "[6/8] Instalando MongoDB..."
if ! command -v mongod &> /dev/null; then
    wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - > /dev/null 2>&1
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list > /dev/null
    apt-get update -qq
    apt-get install -y mongodb-org > /dev/null 2>&1
    systemctl start mongod
    systemctl enable mongod > /dev/null 2>&1
fi
print_success "MongoDB instalado e iniciado"

# 7. Instalar Supervisor
print_info "[7/8] Instalando Supervisor..."
if ! command -v supervisorctl &> /dev/null; then
    apt-get install -y supervisor > /dev/null 2>&1
    systemctl start supervisor
    systemctl enable supervisor > /dev/null 2>&1
fi
print_success "Supervisor instalado"

# 8. Instalar dependências do Playwright (Chromium)
print_info "[8/8] Instalando dependências do Playwright..."
apt-get install -y -qq \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 > /dev/null 2>&1
print_success "Dependências do Playwright instaladas"

echo ""
print_success "============================================"
print_success "  Instalação concluída com sucesso!"
print_success "============================================"
echo ""
print_info "Próximo passo: Execute ./setup.sh"
echo ""