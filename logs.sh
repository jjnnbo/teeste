#!/bin/bash

# Script para visualizar logs - MAGO TRADER

echo "================================================"
echo "  MAGO TRADER - Visualizar Logs"
echo "================================================"
echo ""
echo "Escolha qual log deseja visualizar:"
echo "1) Backend"
echo "2) Frontend"
echo "3) Ambos (split screen)"
echo ""
read -p "Opção [1-3]: " option

case $option in
    1)
        echo "→ Mostrando logs do Backend (Ctrl+C para sair)..."
        echo ""
        tail -f /var/log/supervisor/mago-backend.out.log
        ;;
    2)
        echo "→ Mostrando logs do Frontend (Ctrl+C para sair)..."
        echo ""
        tail -f /var/log/supervisor/mago-frontend.out.log
        ;;
    3)
        echo "→ Mostrando ambos os logs (Ctrl+C para sair)..."
        echo ""
        tail -f /var/log/supervisor/mago-backend.out.log -f /var/log/supervisor/mago-frontend.out.log
        ;;
    *)
        echo "✗ Opção inválida"
        exit 1
        ;;
esac