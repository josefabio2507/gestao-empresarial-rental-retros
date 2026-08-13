document.addEventListener("DOMContentLoaded", () => {
    const apenasDigitos = (valor) => (valor || "").replace(/\D/g, "");

    const aplicarMascaraDocumento = (valor) => {
        const digitos = apenasDigitos(valor).slice(0, 14);

        if (digitos.length <= 11) {
            return digitos
                .replace(/(\d{3})(\d)/, "$1.$2")
                .replace(/(\d{3})(\d)/, "$1.$2")
                .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        }

        return digitos
            .replace(/^(\d{2})(\d)/, "$1.$2")
            .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
            .replace(/\.(\d{3})(\d)/, ".$1/$2")
            .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
    };

    const validarCpf = (cpf) => {
        cpf = apenasDigitos(cpf);

        if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) {
            return false;
        }

        let soma = 0;
        for (let i = 0; i < 9; i += 1) {
            soma += Number(cpf[i]) * (10 - i);
        }
        let digito = (soma * 10) % 11;
        digito = digito === 10 ? 0 : digito;

        if (digito !== Number(cpf[9])) {
            return false;
        }

        soma = 0;
        for (let i = 0; i < 10; i += 1) {
            soma += Number(cpf[i]) * (11 - i);
        }
        digito = (soma * 10) % 11;
        digito = digito === 10 ? 0 : digito;

        return digito === Number(cpf[10]);
    };

    const validarCnpj = (cnpj) => {
        cnpj = apenasDigitos(cnpj);

        if (cnpj.length !== 14 || /^(\d)\1+$/.test(cnpj)) {
            return false;
        }

        const calcular = (base, pesos) => {
            const soma = pesos.reduce((total, peso, indice) => total + Number(base[indice]) * peso, 0);
            const resto = soma % 11;
            return resto < 2 ? 0 : 11 - resto;
        };

        const primeiro = calcular(cnpj, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
        const segundo = calcular(cnpj, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);

        return primeiro === Number(cnpj[12]) && segundo === Number(cnpj[13]);
    };

    document.querySelectorAll("[data-uppercase]").forEach((campo) => {
        const converter = () => {
            campo.value = campo.value.toLocaleUpperCase("pt-BR");
        };

        converter();
        campo.addEventListener("input", converter);
        campo.addEventListener("blur", converter);
    });

    document.querySelectorAll("[data-datalist-target]").forEach((campoBusca) => {
        const campoId = document.getElementById(campoBusca.dataset.datalistTarget);
        const lista = document.getElementById(campoBusca.getAttribute("list"));

        if (!campoId || !lista) {
            return;
        }

        const opcoes = Array.from(lista.querySelectorAll("option"));
        const sincronizar = () => {
            const textoDigitado = campoBusca.value.trim();
            const opcao = opcoes.find((item) => item.value.trim() === textoDigitado);
            campoId.value = opcao ? opcao.dataset.value || "" : "";
            campoBusca.setCustomValidity(textoDigitado && !campoId.value ? "Selecione uma opcao da lista." : "");
        };

        campoBusca.addEventListener("input", sincronizar);
        campoBusca.addEventListener("change", sincronizar);
        campoBusca.addEventListener("blur", sincronizar);

        campoBusca.form?.addEventListener("submit", (evento) => {
            sincronizar();
            if (!campoBusca.checkValidity()) {
                evento.preventDefault();
                campoBusca.reportValidity();
            }
        });
    });

    document.querySelectorAll("[data-auto-code-preview]").forEach((campoCodigo) => {
        const campoDescricao = document.getElementById("descricao");
        if (!campoDescricao || campoCodigo.value) {
            return;
        }

        const atualizarCodigo = () => {
            campoCodigo.value = campoDescricao.value.trim() ? campoCodigo.dataset.autoCodePreview || "" : "";
        };

        campoDescricao.addEventListener("input", atualizarCodigo);
        atualizarCodigo();
    });

    document.querySelectorAll("[data-documento-br]").forEach((campo) => {
        const mascarar = () => {
            campo.value = aplicarMascaraDocumento(campo.value);
        };

        mascarar();
        campo.addEventListener("input", mascarar);
        campo.addEventListener("blur", () => {
            mascarar();

            const digitos = apenasDigitos(campo.value);

            if (!digitos) {
                campo.setCustomValidity("");
            } else if (digitos.length === 11 && validarCpf(digitos)) {
                campo.setCustomValidity("");
            } else if (digitos.length === 14 && validarCnpj(digitos)) {
                campo.setCustomValidity("");
            } else {
                campo.setCustomValidity("Informe um CPF ou CNPJ valido.");
            }
        });
    });

    const aplicarMascaraTelefone = (valor) => {
        let digitos = apenasDigitos(valor).slice(0, 13);

        if (digitos.startsWith("55") && digitos.length > 11) {
            digitos = digitos.slice(2);
        }

        digitos = digitos.slice(0, 11);

        if (digitos.length <= 10) {
            return digitos
                .replace(/^(\d{2})(\d)/, "($1) $2")
                .replace(/(\d{4})(\d{1,4})$/, "$1-$2");
        }

        return digitos
            .replace(/^(\d{2})(\d)/, "($1) $2")
            .replace(/(\d{5})(\d{1,4})$/, "$1-$2");
    };

    document.querySelectorAll("[data-telefone-br]").forEach((campo) => {
        const mascarar = () => {
            campo.value = aplicarMascaraTelefone(campo.value);
        };

        mascarar();
        campo.addEventListener("input", mascarar);
        campo.addEventListener("blur", () => {
            mascarar();
            const digitos = apenasDigitos(campo.value);
            campo.setCustomValidity(digitos.length === 10 || digitos.length === 11 ? "" : "Informe DDD e numero.");
        });
    });

    const botaoConsultaCnpj = document.querySelector("[data-cnpj-lookup]");

    if (botaoConsultaCnpj) {
        botaoConsultaCnpj.addEventListener("click", async () => {
            const campoDocumento = document.querySelector("[data-documento-br]");
            const status = document.querySelector("#cnpj_lookup_status");
            const cnpj = apenasDigitos(campoDocumento?.value || "");

            if (status) {
                status.textContent = "";
            }

            if (!validarCnpj(cnpj)) {
                if (status) {
                    status.textContent = "Informe um CNPJ valido para buscar os dados.";
                }
                return;
            }

            botaoConsultaCnpj.disabled = true;
            const textoOriginal = botaoConsultaCnpj.textContent;
            botaoConsultaCnpj.textContent = "Buscando...";

            try {
                const resposta = await fetch(`${botaoConsultaCnpj.dataset.url}?cnpj=${cnpj}`, {
                    headers: { Accept: "application/json" },
                });
                const payload = await resposta.json();

                if (!resposta.ok || !payload.sucesso) {
                    throw new Error(payload.mensagem || "Nao foi possivel consultar o CNPJ.");
                }

                const dados = payload.dados || {};
                const preencher = (id, valor) => {
                    const campo = document.getElementById(id);
                    if (campo && valor) {
                        campo.value = valor;
                        campo.dispatchEvent(new Event("input"));
                    }
                };

                preencher("razao_social", dados.razao_social);
                preencher("nome_fantasia", dados.nome_fantasia);
                preencher("email", dados.email);
                preencher("telefone", dados.telefone);
                preencher("endereco", dados.endereco);
                preencher("cidade", dados.cidade);
                preencher("uf", dados.uf);

                if (status) {
                    status.textContent = payload.mensagem || "Dados encontrados.";
                }
            } catch (erro) {
                if (status) {
                    status.textContent = erro.message;
                }
            } finally {
                botaoConsultaCnpj.disabled = false;
                botaoConsultaCnpj.textContent = textoOriginal;
            }
        });
    }

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
