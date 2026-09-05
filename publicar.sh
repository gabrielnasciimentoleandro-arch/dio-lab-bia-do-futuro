#!/usr/bin/env bash
#
# Prepara o projeto para publicação: troca o placeholder do badge de CI pelo
# seu usuário/repositório reais, roda as suítes e mostra os comandos de push.
#
#   ./publicar.sh SEU-USUARIO NOME-DO-REPO
#
# Exemplo:
#   ./publicar.sh joaosilva dio-lab-bia-do-futuro
#
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "uso: ./publicar.sh SEU-USUARIO NOME-DO-REPO"
  echo "ex:  ./publicar.sh joaosilva dio-lab-bia-do-futuro"
  exit 1
fi

USUARIO="$1"
REPO="$2"

echo "==> Ajustando o badge de CI para ${USUARIO}/${REPO}"
if grep -q "SEU-USUARIO/SEU-REPO" README.md; then
  sed -i "s|SEU-USUARIO/SEU-REPO|${USUARIO}/${REPO}|g" README.md
  echo "    badge atualizado"
else
  echo "    badge ja estava preenchido (nada a fazer)"
fi

echo
echo "==> Limpando arquivos de runtime"
rm -f data/diario_incidentes.json
find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo
echo "==> Rodando as suites (o CI vai rodar as mesmas)"
python3 eval/testar_calculos.py > /dev/null && echo "    unitarios: ok"
python3 eval/avaliar.py | grep "GERAL"
python3 examples/gerar_exemplos.py > /dev/null && echo "    exemplos regerados"
rm -f data/diario_incidentes.json

echo
echo "==> Conferindo se alguma chave de API vazou"
if git log -p 2>/dev/null | grep -oE "AIza[A-Za-z0-9_-]{30,}" | head -1; then
  echo "    ATENCAO: possivel chave encontrada acima. NAO faca o push."
  exit 1
else
  echo "    nenhuma chave no historico"
fi

echo
echo "==> Commitando o ajuste"
git add -A
if git diff --cached --quiet; then
  echo "    nada novo para commitar"
else
  git commit -q -m "Ajusta badge de CI para o repositorio publicado"
  echo "    commit criado"
fi

echo
echo "=============================================================="
echo " Tudo pronto. Agora rode:"
echo
echo "   git remote add origin https://github.com/${USUARIO}/${REPO}.git"
echo "   git push --force origin main"
echo
echo " Depois confira a aba Actions do GitHub: a suite roda sozinha."
echo "=============================================================="
