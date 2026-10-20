NOMES_DE_PAPEL = {
    1: "Administrador",
    2: "Coordenador",
    3: "Instrutor",
    4: "Aluno",
    5: "Revisor",
}


def render(request, nome, contexto=None, status_code=200):
    dados = {
        "csrf": request.app.state.sessoes.obter(request)["csrf"],
        "usuario": getattr(request.state, "usuario", None),
    }
    if contexto:
        dados.update(contexto)
    return request.app.state.templates.TemplateResponse(
        request, nome, dados, status_code=status_code
    )
