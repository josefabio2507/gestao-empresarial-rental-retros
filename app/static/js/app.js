document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-confirm]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            const mensagem = elemento.getAttribute("data-confirm");

            if (mensagem && !window.confirm(mensagem)) {
                evento.preventDefault();
            }
        });
    });
});

console.log("Gestão Empresarial Rental Retros iniciado.");
