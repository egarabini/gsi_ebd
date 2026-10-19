document.addEventListener("click", function (event) {
  const button = event.target.closest("[data-adicionar]");
  if (!button) return;
  const editor = button.closest(".editor");
  const name = button.dataset.adicionar;
  const group = editor.querySelector('[data-grupo="' + name + '"]');
  const fragment = editor.querySelector('[data-modelo="' + name + '"]').content.cloneNode(true);
  const order = fragment.querySelector('[name="capitulo_ordem"]');
  if (order) order.value = group.querySelectorAll("fieldset").length + 1;
  group.appendChild(fragment);
});
document.addEventListener("htmx:configRequest", function (event) {
  const form = event.detail.elt.closest("form");
  const field = form && form.querySelector('[name="csrf_token"]');
  if (field) event.detail.headers["X-CSRF-Token"] = field.value;
});
document.addEventListener("htmx:beforeSwap", function (event) {
  if (event.detail.xhr.status >= 400 && event.detail.xhr.status < 500) {
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  }
});
