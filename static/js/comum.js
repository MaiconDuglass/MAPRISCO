/*
 * Funções compartilhadas pelas telas internas do MAPRISCO.
 * Carregado pelo templates/base.html antes dos scripts de cada página.
 */

// Aceita resposta paginada ({count, next, results}) ou lista simples
function parseApiList(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.results)) return payload.results;
    return [];
}

function getCookie(name) {
    const cookieValue = document.cookie
        .split('; ')
        .find((row) => row.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : '';
}

// Protege textos vindos do banco antes de inserir no HTML (evita XSS)
function esc(text) {
    return String(text ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m]);
}

function fmtDate(value) {
    if (!value) return '-';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return '-';
    return dt.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Nível de água no padrão brasileiro: 30,00 cm
function fmtNivel(value) {
    const n = Number(value);
    if (value === null || value === undefined || value === '' || Number.isNaN(n)) return '-';
    return `${n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} cm`;
}

// Rótulos dos níveis de alerta: os mesmos em todas as telas
const NIVEL_ALERTA_LABEL = { baixo: 'Baixo', medio: 'Médio', alto: 'Alto', critico: 'Crítico' };

function nivelAlertaLabel(nivel) {
    return NIVEL_ALERTA_LABEL[(nivel || '').toLowerCase()] || nivel || '-';
}

// Busca todas as páginas de um endpoint da API (a API devolve no máximo 1000 itens por página)
async function fetchAll(url) {
    const results = [];
    let next = url + (url.includes('?') ? '&' : '?') + 'page_size=1000';
    while (next) {
        const response = await fetch(next, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Falha ao carregar ${url}`);
        const data = await response.json();
        if (Array.isArray(data)) return data;
        results.push(...(data.results || []));
        next = data.next;
    }
    return results;
}

// Total de itens de um endpoint, sem baixar a lista inteira
async function fetchCount(url) {
    const response = await fetch(url + (url.includes('?') ? '&' : '?') + 'page_size=1', { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`Falha ao contar ${url}`);
    const data = await response.json();
    return Array.isArray(data) ? data.length : (data.count ?? 0);
}

// Aviso na própria tela (substitui o alert() do navegador)
function avisar(mensagem, tipo = 'erro') {
    let area = document.getElementById('avisos');
    if (!area) {
        area = document.createElement('div');
        area.id = 'avisos';
        area.setAttribute('aria-live', 'polite');
        document.body.appendChild(area);
    }
    const aviso = document.createElement('div');
    aviso.className = `aviso aviso-${tipo}`;
    const icone = tipo === 'sucesso' ? 'fa-circle-check' : 'fa-circle-exclamation';
    aviso.innerHTML = `<i class="fa-solid ${icone}"></i><span>${esc(mensagem)}</span>`;
    area.appendChild(aviso);
    setTimeout(() => aviso.classList.add('saindo'), 4000);
    setTimeout(() => aviso.remove(), 4400);
}

// Confirmação na própria tela (substitui o confirm() do navegador). Retorna Promise<boolean>.
function confirmar(mensagem, { titulo = 'Confirmar', botao = 'Confirmar' } = {}) {
    return new Promise((resolve) => {
        const fundo = document.createElement('div');
        fundo.className = 'confirmar-fundo';
        fundo.innerHTML = `
            <div class="confirmar-card" role="dialog" aria-modal="true" aria-labelledby="confirmarTitulo">
                <h3 id="confirmarTitulo">${esc(titulo)}</h3>
                <p>${esc(mensagem)}</p>
                <div class="confirmar-acoes">
                    <button type="button" class="btn-cancelar">Cancelar</button>
                    <button type="button" class="btn-perigo">${esc(botao)}</button>
                </div>
            </div>`;
        const fechar = (resposta) => {
            fundo.remove();
            document.removeEventListener('keydown', onKey);
            resolve(resposta);
        };
        const onKey = (event) => { if (event.key === 'Escape') fechar(false); };
        fundo.querySelector('.btn-cancelar').addEventListener('click', () => fechar(false));
        fundo.querySelector('.btn-perigo').addEventListener('click', () => fechar(true));
        fundo.addEventListener('click', (event) => { if (event.target === fundo) fechar(false); });
        document.addEventListener('keydown', onKey);
        document.body.appendChild(fundo);
        fundo.querySelector('.btn-cancelar').focus();
    });
}
