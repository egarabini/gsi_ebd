"""Escopo de ambiente (tenant) — fonte unica da fronteira de isolamento.

Decisao de arquitetura: cada tabela de dados carrega a FK `ambiente_id`, entao o
isolamento e estrutural. Este modulo e o unico lugar que resolve:
  - a qual ambiente um registro pertence (para GRAVAR)
  - qual ambiente o usuario logado pode ver (para LER)

Nenhuma query deve montar o filtro de ambiente por conta propria.
"""
from typing import Optional

import reflex as rx
from sqlmodel import select

from ..models import Role, User


class EscopoService:
    @staticmethod
    def ambiente_do_usuario(usuario_id: Optional[int]) -> Optional[int]:
        """Ambiente (tenant) a que um usuario pertence. None para ADMIN."""
        if not usuario_id:
            return None
        with rx.session() as session:
            u = session.exec(select(User).where(User.id == usuario_id)).first()
            return u.ambiente_id if u else None

    @staticmethod
    def ambiente_do_ator(ator_id: int, role: int) -> Optional[int]:
        """Ambiente que o ator enxerga.

        - ADMIN      -> None, que significa "todos os ambientes"
        - COORDENADOR-> o ambiente que ele possui
        - INSTRUTOR  -> o ambiente em que atua
        - ALUNO      -> o proprio ambiente
        """
        if role == Role.ADMIN:
            return None
        return EscopoService.ambiente_do_usuario(ator_id)

    @staticmethod
    def filtrar(statement, modelo, ambiente_id: Optional[int]):
        """Aplica o filtro de ambiente a um select. None = sem filtro (ADMIN).

        Uso: EscopoService.filtrar(select(X), X, amb)
        """
        if ambiente_id is None:
            return statement
        return statement.where(modelo.ambiente_id == ambiente_id)
