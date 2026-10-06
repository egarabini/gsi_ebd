"""Estado da avaliacao humana — a fila de correcao do instrutor."""
from typing import Dict, List

import reflex as rx

from ..services.review_service import ReviewService
from .auth import AuthState


class RevisaoState(AuthState):
    pendentes: List[Dict] = []
    total_pendentes: int = 0
    resposta_aberta_id: str = ""
    parecer_texto: str = ""
    considerou_correto: bool = True
    mensagem: str = ""
    mensagem_tipo: str = "info"

    def load_fila(self):
        itens = ReviewService.fila_pendente(self.current_user_id, self.current_user_role)
        self.pendentes = itens
        self.total_pendentes = len(itens)

    @rx.var
    def tem_pendentes(self) -> bool:
        return self.total_pendentes > 0

    @rx.var
    def fila_label(self) -> str:
        if self.total_pendentes == 0:
            return "Nenhuma resposta aguardando correcao"
        if self.total_pendentes == 1:
            return "1 resposta aguardando sua correcao"
        return f"{self.total_pendentes} respostas aguardando sua correcao"

    def abrir_resposta(self, response_id: str):
        self.resposta_aberta_id = response_id
        self.parecer_texto = ""
        self.considerou_correto = True
        self.mensagem = ""

    def fechar_resposta(self):
        self.resposta_aberta_id = ""
        self.parecer_texto = ""

    def salvar_parecer(self):
        if not self.resposta_aberta_id:
            return
        try:
            rid = int(self.resposta_aberta_id)
        except (TypeError, ValueError):
            self.mensagem = "Resposta invalida"
            self.mensagem_tipo = "error"
            return
        erro = ReviewService.registrar_parecer(
            response_id=rid,
            instrutor_id=self.current_user_id,
            role=self.current_user_role,
            parecer=self.parecer_texto,
            considerou_correto=self.considerou_correto,
        )
        if erro:
            self.mensagem = erro
            self.mensagem_tipo = "error"
            return
        self.mensagem = "Parecer enviado ao aluno!"
        self.mensagem_tipo = "success"
        self.resposta_aberta_id = ""
        self.parecer_texto = ""
        self.load_fila()
