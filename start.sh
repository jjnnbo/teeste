#!/bin/bash

# Script para iniciar os serviços - MAGO TRADER

echo "================================================"
echo "  MAGO TRADER - Iniciando Serviços"
echo "================================================"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo "✗ Por favor, execute como root (use sudo)"
    exit 1
fi

echo "→ Iniciando serviços..."

# Iniciar MongoDB
systemctl start mongod
echo "✓ MongoDB iniciado"

# Iniciar serviços via Supervisor
supervisorctl start mago-backend
supervisorctl start mago-frontend
echo "✓ Backend iniciado"
echo "✓ Frontend iniciado"

echo ""
echo "✓ Todos os serviços foram iniciados!"
echo ""
echo "Status dos serviços:"
supervisorctl status
echo ""
echo "→ Acesse o sistema em: http://SEU_IP:3000"
echo "→ Backend API: http://SEU_IP:8001/api"
echo ""
echo "Para ver os logs em tempo real, execute: ./logs.sh"
echo ""