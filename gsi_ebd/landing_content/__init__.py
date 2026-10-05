# landing_content/__init__.py
"""
Pasta de componentes da Landing Page do GSI-EBD.

Cada seção da landing page é um arquivo Python independente em sections/.
O controlador principal (controller.py) os carrega e monta a página completa.

Estrutura:
    landing_content/
    ├── __init__.py          ← este arquivo
    ├── controller.py        ← monta a landing page completa
    └── sections/
        ├── hero.py          ← Seção Hero (topo)
        ├── sobre.py         ← Sobre a plataforma
        ├── niveis.py        ← Níveis de estudo
        ├── testemunhos.py   ← Depoimentos
        ├── planos.py        ← Planos e valores
        ├── formulario.py    ← Formulário de interesse
        └── rodape.py        ← Rodapé
"""
from .controller import landing_page_full

__all__ = ["landing_page_full"]
