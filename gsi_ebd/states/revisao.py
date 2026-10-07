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
    # apoio da IA (parecer preliminar — o instrutor decide)
    sugerindo: bool = False
    sugestao_aderencia: str = ""
    sugestao_comentario: str = ""
    sugestao_sugestao: str = ""
    sugestao_disponivel: bool = False
    sugestao_erro: str = ""
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

    def pedir_sugestao(self):
        """Pede à IA um parecer preliminar. O instrutor decide o que fazer com ele."""
        if not self.resposta_aberta_id:
            return
        try:
            rid = int(self.resposta_aberta_id)
        except (TypeError, ValueError):
            return
        self.sugerindo = True
        self.sugestao_erro = ""
        try:
            r = ReviewService.sugerir_parecer(
                response_id=rid,
                instrutor_id=self.current_user_id,
                role=self.current_user_role,
            )
        except Exception as e:
            r = {"ok": False, "erro": f"Falha ao consultar a IA: {e}"}
        self.sugerindo = False
        if not r.get("ok"):
            self.sugestao_erro = r.get("erro", "Não foi possível gerar a sugestão")
            return
        self.sugestao_disponivel = bool(r.get("disponivel"))
        self.sugestao_aderencia = r.get("aderencia", "")
        self.sugestao_comentario = r.get("comentario", "")
        self.sugestao_sugestao = r.get("sugestao", "")
        self.sugestao_erro = r.get("erro", "")
        if self.sugestao_disponivel:
            # preenche o campo para o instrutor EDITAR (ele pode trocar tudo)
            base = self.sugestao_comentario
            if self.sugestao_sugestao:
                base += f"\n\n{self.sugestao_sugestao}"
            if not self.parecer_texto.strip():
                self.parecer_texto = base
            self.considerou_correto = bool(r.get("correto_sugerido"))

    def usar_sugestao(self):
        base = self.sugestao_comentario
        if self.sugestao_sugestao:
            base += f"\n\n{self.sugestao_sugestao}"
        self.parecer_texto = base

    def descartar_sugestao(self):
        self.sugestao_disponivel = False
        self.sugestao_comentario = ""
        self.sugestao_sugestao = ""
        self.sugestao_aderencia = ""

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
