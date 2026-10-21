from fastapi import APIRouter, Depends, Request

from gsi_ebd.models import User
from v1.auth import ambiente_atual, exigir, verificar_csrf, verificar_h14
from v1.views import NOMES_DE_PAPEL, render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])


@router.get("/")
def raiz(
    request: Request,
    usuario: User = Depends(exigir("rota:/")),
    ambiente=Depends(ambiente_atual),
):
    return render(
        request,
        "raiz.html",
        {
            "papel_nome": NOMES_DE_PAPEL.get(int(usuario.role), "Papel"),
            "ambiente": ambiente,
        },
    )
