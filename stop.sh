#!/bin/bash

# Script para parar os serviços - MAGO TRADER

echo "================================================"
echo "  MAGO TRADER - Parando Serviços"
echo "================================================"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo "✗ Por favor, execute como root (use sudo)"
    exit 1
fi

echo "→ Parando serviços..."

# Parar serviços via Supervisor
supervisorctl stop mago-backend
supervisorctl stop mago-frontend

echo ""
echo "✓ Todos os serviços foram parados!"
echo ""
echo "Status dos serviços:"
supervisorctl status
echo ""