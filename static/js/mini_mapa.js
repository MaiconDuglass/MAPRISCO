/*
 * Mini mapas do MAPRISCO (mesmo comportamento do mini mapa do cadastro de área).
 * Requer o Leaflet (static/leaflet/leaflet.js) carregado antes.
 */

const MINI_MAPA_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}';

/*
 * Mini mapa para escolher um ponto com um clique.
 * aoMarcar({lat, lng}) recebe as coordenadas com 6 casas; aoSemInternet() é chamado se o fundo não carregar.
 * Retorna { limpar(), atualizarTamanho() }.
 */
function criarMapaSelecao(elementId, centro, { aoMarcar, aoSemInternet } = {}) {
    const mapa = L.map(elementId).setView(centro, 13);
    let marcador = null;
    let falhas = 0;
    L.tileLayer(MINI_MAPA_TILES, { attribution: '&copy; Esri', maxZoom: 19 })
        .on('tileerror', () => { falhas += 1; if (falhas === 3 && aoSemInternet) aoSemInternet(); })
        .addTo(mapa);

    mapa.on('click', (event) => {
        if (marcador) marcador.setLatLng(event.latlng);
        else marcador = L.marker(event.latlng).addTo(mapa);
        if (aoMarcar) aoMarcar({ lat: event.latlng.lat.toFixed(6), lng: event.latlng.lng.toFixed(6) });
    });

    return {
        limpar() {
            if (marcador) {
                mapa.removeLayer(marcador);
                marcador = null;
            }
        },
        atualizarTamanho() { mapa.invalidateSize(); },
    };
}

/* Mini mapa só para mostrar um ponto (sem arrastar nem dar zoom). */
function criarMapaPonto(elementId, lat, lng) {
    const mapa = L.map(elementId, {
        zoomControl: false, dragging: false, scrollWheelZoom: false,
        doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false,
        attributionControl: false,
    }).setView([lat, lng], 15);
    L.tileLayer(MINI_MAPA_TILES, { maxZoom: 19 }).addTo(mapa);
    L.circleMarker([lat, lng], { radius: 8, color: '#7c3aed', fillColor: '#8b5cf6', fillOpacity: 0.9, weight: 2 }).addTo(mapa);
    return mapa;
}
