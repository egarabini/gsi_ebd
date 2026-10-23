(function () {
  document.body.addEventListener("htmx:configRequest", function (evento) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
      evento.detail.headers["X-CSRF-Token"] = meta.getAttribute("content");
    }
    var form = evento.detail.elt.closest("form");
    var campo = form && form.querySelector('[name="csrf_token"]');
    if (campo) {
      evento.detail.headers["X-CSRF-Token"] = campo.value;
    }
  });
  document.body.addEventListener("htmx:beforeSwap", function (evento) {
    if (evento.detail.xhr.status >= 400 && evento.detail.xhr.status < 500) {
      evento.detail.shouldSwap = true;
      evento.detail.isError = false;
    }
  });
  document.addEventListener("click", function (evento) {
    var botao = evento.target.closest("[data-adicionar]");
    if (!botao) {
      return;
    }
    var editor = botao.closest(".editor");
    var nome = botao.dataset.adicionar;
    var grupo = editor.querySelector('[data-grupo="' + nome + '"]');
    var fragmento = editor.querySelector('[data-modelo="' + nome + '"]').content.cloneNode(true);
    var ordem = fragmento.querySelector('[name="capitulo_ordem"]');
    if (ordem) {
      ordem.value = grupo.querySelectorAll("fieldset").length + 1;
    }
    grupo.appendChild(fragmento);
  });
})();
