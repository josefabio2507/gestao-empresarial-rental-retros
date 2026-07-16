document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-confirm]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
            const mensagem = elemento.getAttribute("data-confirm");

            if (mensagem && !window.confirm(mensagem)) {
                evento.preventDefault();
            }
        });
    });

    const formulariosAutoSubmit = document.querySelectorAll("[data-auto-submit-delay]");

    if (!formulariosAutoSubmit.length) {
        sessionStorage.removeItem("holeritesAutoSyncCursor");
        sessionStorage.removeItem("holeritesAutoSyncCursorRepeat");
    }

    formulariosAutoSubmit.forEach((formulario) => {
        const delay = Number.parseInt(formulario.dataset.autoSubmitDelay, 10);
        const atraso = Number.isFinite(delay) && delay > 0 ? delay : 2000;
        const botaoSubmit = formulario.querySelector("button[type='submit']");
        const cursor = formulario.querySelector("input[name='cursor']")?.value || formulario.action;
        const ultimoCursor = sessionStorage.getItem("holeritesAutoSyncCursor");
        const repeticoes = Number.parseInt(
            sessionStorage.getItem("holeritesAutoSyncCursorRepeat") || "0",
            10,
        );

        if (ultimoCursor === cursor && repeticoes >= 1) {
            return;
        }

        formulario.addEventListener("submit", () => {
            if (botaoSubmit) {
                botaoSubmit.disabled = true;
                botaoSubmit.textContent = formulario.dataset.autoSubmitLabel || botaoSubmit.textContent;
            }
        });

        if (botaoSubmit) {
            botaoSubmit.disabled = true;
            botaoSubmit.textContent = formulario.dataset.autoSubmitLabel || botaoSubmit.textContent;
        }

        window.setTimeout(() => {
            if (ultimoCursor === cursor) {
                sessionStorage.setItem("holeritesAutoSyncCursorRepeat", String(repeticoes + 1));
            } else {
                sessionStorage.setItem("holeritesAutoSyncCursor", cursor);
                sessionStorage.setItem("holeritesAutoSyncCursorRepeat", "0");
            }

            formulario.submit();
        }, atraso);
    });
});

console.log("Gestão Empresarial Rental Retros iniciado.");
