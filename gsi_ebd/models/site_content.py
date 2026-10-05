from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Testemunho(SQLModel, table=True):
    """Depoimentos exibidos na landing page — gerenciados pelo Admin."""
    id: Optional[int] = Field(default=None, primary_key=True)

    nome: str
    cidade: str = Field(default="")
    estado: str = Field(default="")
    profissao_fe: str = Field(default="")   # ex: "Adventista", "Batista"
    texto: str                               # o depoimento em si
    foto_url: str = Field(default="")

    is_active: bool = Field(default=True)
    ordem: int = Field(default=0)            # ordenação exibição

    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class SiteConfig(SQLModel, table=True):
    """
    Armazena textos dinâmicos da landing page como pares chave-valor.
    Gerenciado pelo Admin via painel.

    Chaves padrão:
        hero_titulo, hero_subtitulo, hero_cta_texto
        sobre_titulo, sobre_texto
        missao_texto, visao_texto
        planos_descricao
        rodape_contato, rodape_email, rodape_telefone
        redes_instagram, redes_youtube, redes_whatsapp, redes_facebook
        niveis_basico_desc, niveis_medio_desc, niveis_avancado_desc, niveis_master_desc
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    chave: str = Field(unique=True, index=True)  # identificador único
    valor: str = Field(default="")               # conteúdo (texto, URL, etc.)
    descricao: str = Field(default="")           # dica para o Admin no painel
    updated_at: Optional[datetime] = Field(default=None)
    updated_by: Optional[int] = Field(default=None)  # FK → User (Admin)
