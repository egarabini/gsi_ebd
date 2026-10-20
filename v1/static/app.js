(function () {
  document.body.addEventListener("htmx:configRequest", function (evento) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
      evento.detail.headers["X-CSRF-Token"] = meta.getAttribute("content");
    }
  });
})();
