#!/bin/bash

# Script para reiniciar os serviços - MAGO TRADER

echo "================================================"
echo "  MAGO TRADER - Reiniciando Serviços"
echo "================================================"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo "✗ Por favor, execute como root (use sudo)"
    exit 1
fi

echo "→ Reiniciando serviços..."

# Reiniciar serviços via Supervisor
supervisorctl restart mago-backend
supervisorctl restart mago-frontend

echo ""
echo "✓ Serviços reiniciados!"
echo ""
echo "Status dos serviços:"
supervisorctl status
echo ""