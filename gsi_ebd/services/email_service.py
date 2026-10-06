"""
Serviço de Email do GSI-EBD.

Envia emails transacionais usando SMTP (configurável via .env).
Para produção, trocar SMTP_HOST por SendGrid, Amazon SES, etc.

Variáveis de ambiente necessárias (.env):
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=seuemail@gmail.com
    SMTP_PASSWORD=sua_senha_de_app
    EMAIL_FROM=noreply@gsi-ebd.com.br
    EMAIL_FROM_NAME=GSI-EBD
    APP_BASE_URL=http://localhost:3000
"""
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@gsi-ebd.com.br")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "GSI-EBD Estudos Bíblicos")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")

# Desabilitar email em dev se credenciais não configuradas
EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASSWORD)


def _send_async(msg: MIMEMultipart):
    """Envia email em thread separada para não bloquear a UI."""
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[EMAIL ERROR] Falha ao enviar: {e}")


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
    async_send: bool = True,
) -> bool:
    """
    Envia um email HTML.

    Args:
        to_email: destinatário
        subject: assunto
        html_body: corpo em HTML
        plain_body: fallback texto simples (gerado automaticamente se None)
        async_send: True = envia em background sem bloquear

    Returns:
        True se enviado (ou enfileirado), False se email desabilitado
    """
    if not EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] Para: {to_email} | Assunto: {subject}")
        print(f"[EMAIL BODY] {plain_body or html_body[:200]}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    msg["To"] = to_email

    if plain_body is None:
        # Remove tags HTML básicas para fallback
        import re
        plain_body = re.sub(r"<[^>]+>", "", html_body)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if async_send:
        thread = threading.Thread(target=_send_async, args=(msg,), daemon=True)
        thread.start()
    else:
        _send_async(msg)

    return True


# ──────────────────────────────────────────────
# Templates de Email por Evento
# ──────────────────────────────────────────────

def _base_template(titulo: str, corpo: str, cta_url: str = "", cta_texto: str = "") -> str:
    """Template HTML base para todos os emails."""
    cta_btn = ""
    if cta_url and cta_texto:
        cta_btn = f"""
        <div style="text-align:center; margin:32px 0;">
            <a href="{cta_url}"
               style="background:#4f46e5;color:#fff;padding:14px 32px;border-radius:8px;
                      text-decoration:none;font-weight:bold;font-size:16px;">
                {cta_texto}
            </a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" style="background:#fff;border-radius:12px;overflow:hidden;
                                 box-shadow:0 4px 24px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
                     padding:32px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:24px;letter-spacing:1px;">
              ✝ GSI-EBD
            </h1>
            <p style="color:#c7d2fe;margin:8px 0 0;font-size:13px;">
              Estudos Bíblicos Dirigidos
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px 48px;">
            <h2 style="color:#1e1b4b;margin:0 0 16px;">{titulo}</h2>
            {corpo}
            {cta_btn}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:24px 48px;text-align:center;
                     color:#94a3b8;font-size:12px;border-top:1px solid #e2e8f0;">
            <p style="margin:0;">GSI-EBD — Estudos Bíblicos Dirigidos</p>
            <p style="margin:4px 0 0;">Este é um email automático, não responda diretamente.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_confirmacao_conta(nome: str, email: str, token: str) -> bool:
    """Email enviado ao criar conta — usuário começa SUSPENSO até confirmar."""
    url = f"{APP_BASE_URL}/confirmar/{token}"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Sua conta na plataforma GSI-EBD foi criada com sucesso.<br>
        Para ativar seu acesso, clique no botão abaixo e confirme seu email.
    </p>
    <p style="color:#6b7280;font-size:13px;">
        Este link expira em <strong>24 horas</strong>.
    </p>"""
    return send_email(
        to_email=email,
        subject="✅ Confirme sua conta — GSI-EBD",
        html_body=_base_template("Confirmação de Conta", corpo, url, "Confirmar Minha Conta"),
    )


def send_troca_senha(nome: str, email: str, token: str) -> bool:
    """Email enviado ao trocar senha — conta fica SUSPENSA até reconfirmar."""
    url = f"{APP_BASE_URL}/confirmar/{token}"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Uma alteração de senha foi solicitada para sua conta.<br>
        Sua conta foi temporariamente <strong>suspensa</strong> por segurança.<br>
        Clique no botão abaixo para reativar seu acesso.
    </p>
    <p style="color:#ef4444;font-size:13px;">
        ⚠️ Se você não solicitou esta alteração, entre em contato imediatamente.
    </p>"""
    return send_email(
        to_email=email,
        subject="🔐 Confirme a alteração de senha — GSI-EBD",
        html_body=_base_template("Alteração de Senha", corpo, url, "Confirmar e Reativar Acesso"),
    )


def send_conta_suspensa_tentativas(nome: str, email: str, token: str) -> bool:
    """Email enviado ao atingir N tentativas de login com senha errada."""
    url = f"{APP_BASE_URL}/confirmar/{token}"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Detectamos <strong>múltiplas tentativas de login com senha incorreta</strong>
        na sua conta GSI-EBD.<br>
        Por segurança, sua conta foi <strong>suspensa</strong> temporariamente.
    </p>
    <p style="color:#374151;line-height:1.7;">
        Para reativar, confirme que é você clicando abaixo.
    </p>
    <p style="color:#6b7280;font-size:13px;">
        Se não foi você, entre em contato com o administrador.
    </p>"""
    return send_email(
        to_email=email,
        subject="⚠️ Conta suspensa por segurança — GSI-EBD",
        html_body=_base_template("Conta Suspensa", corpo, url, "Confirmar e Reativar"),
    )


def send_reativacao_inativo(nome: str, email: str, token: str) -> bool:
    """Email enviado ao usuário INATIVO que tentou acessar e pediu reativação."""
    url = f"{APP_BASE_URL}/confirmar/{token}"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Ficamos felizes que você quer retornar aos seus estudos bíblicos! 🙏<br>
        Sua conta estava <strong>inativa</strong> por um período sem acesso.
    </p>
    <p style="color:#374151;line-height:1.7;">
        Clique no botão abaixo para reativar seu acesso e retomar de onde parou.
    </p>"""
    return send_email(
        to_email=email,
        subject="🙏 Reative sua conta — GSI-EBD",
        html_body=_base_template("Bem-vindo de Volta!", corpo, url, "Reativar Minha Conta"),
    )


def send_conta_cancelada(nome: str, email: str) -> bool:
    """Email informativo ao usuário cujo acesso foi CANCELADO."""
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Informamos que sua conta na plataforma GSI-EBD foi
        <strong>cancelada</strong>.
    </p>
    <p style="color:#374151;line-height:1.7;">
        Caso deseje reativar seu acesso no futuro, entre em contato com
        seu <strong>Gestor</strong> ou com o <strong>Administrador</strong>
        da plataforma por email.
    </p>"""
    return send_email(
        to_email=email,
        subject="ℹ️ Conta cancelada — GSI-EBD",
        html_body=_base_template("Conta Cancelada", corpo),
    )


def send_novo_lead_admin(admin_email: str, lead_nome: str, lead_email: str) -> bool:
    """Notifica o Admin sobre novo formulário de interesse recebido."""
    url = f"{APP_BASE_URL}/admin"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">
        Um novo formulário de interesse foi recebido na landing page.
    </p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <tr>
            <td style="padding:8px 12px;background:#f8fafc;font-weight:bold;width:40%;">Nome</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{lead_nome}</td>
        </tr>
        <tr>
            <td style="padding:8px 12px;background:#f8fafc;font-weight:bold;">Email</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;">{lead_email}</td>
        </tr>
    </table>
    <p style="color:#374151;line-height:1.7;">
        Acesse o painel para ver todos os detalhes e dar continuidade.
    </p>"""
    return send_email(
        to_email=admin_email,
        subject=f"📩 Novo interesse: {lead_nome} — GSI-EBD",
        html_body=_base_template("Novo Formulário de Interesse", corpo, url, "Ver no Painel"),
    )


def send_assinatura_vencendo(nome: str, email: str, dias: int, valor: float) -> bool:
    """Avisa o usuário que a assinatura vence em X dias."""
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Sua assinatura da plataforma GSI-EBD vence em
        <strong>{dias} dia(s)</strong>.
    </p>
    <p style="color:#374151;line-height:1.7;">
        Valor: <strong>R$ {valor:.2f}</strong><br>
        Entre em contato com seu gestor para regularizar o pagamento
        e manter seu acesso ativo.
    </p>"""
    return send_email(
        to_email=email,
        subject=f"⏰ Assinatura vence em {dias} dia(s) — GSI-EBD",
        html_body=_base_template("Aviso de Vencimento", corpo),
    )


def send_estudo_aprovado(gestor_nome: str, gestor_email: str, estudo_titulo: str) -> bool:
    """Notifica Gestor que seu estudo proposto foi aprovado pelo Admin."""
    url = f"{APP_BASE_URL}/coordenador"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{gestor_nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Ótima notícia! Seu estudo <strong>"{estudo_titulo}"</strong>
        foi <span style="color:#16a34a;font-weight:bold;">aprovado</span>
        pelo Administrador da plataforma. 🎉
    </p>
    <p style="color:#374151;line-height:1.7;">
        Agora ele está disponível para ser atribuído aos alunos pelos Coordenadores.
    </p>"""
    return send_email(
        to_email=gestor_email,
        subject=f"✅ Estudo aprovado: {estudo_titulo} — GSI-EBD",
        html_body=_base_template("Estudo Aprovado!", corpo, url, "Ver no Painel"),
    )


def send_estudo_rejeitado(
    gestor_nome: str, gestor_email: str, estudo_titulo: str, feedback: str
) -> bool:
    """Notifica Gestor que seu estudo foi rejeitado, com feedback do Admin."""
    url = f"{APP_BASE_URL}/coordenador"
    corpo = f"""
    <p style="color:#374151;line-height:1.7;">Olá, <strong>{gestor_nome}</strong>!</p>
    <p style="color:#374151;line-height:1.7;">
        Seu estudo <strong>"{estudo_titulo}"</strong> foi analisado pelo Administrador
        e precisa de ajustes antes de ser publicado.
    </p>
    <div style="background:#fef2f2;border-left:4px solid #ef4444;padding:16px;
                border-radius:4px;margin:16px 0;">
        <p style="color:#374151;margin:0;font-weight:bold;">Feedback do Admin:</p>
        <p style="color:#374151;margin:8px 0 0;">{feedback}</p>
    </div>
    <p style="color:#374151;line-height:1.7;">
        Faça os ajustes necessários e reenvie para aprovação.
    </p>"""
    return send_email(
        to_email=gestor_email,
        subject=f"📝 Estudo para revisão: {estudo_titulo} — GSI-EBD",
        html_body=_base_template("Estudo para Revisão", corpo, url, "Ver no Painel"),
    )
