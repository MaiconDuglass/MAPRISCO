from rest_framework.pagination import PageNumberPagination


class PaginacaoPadrao(PageNumberPagination):
    """100 itens por página; o cliente pode pedir outro tamanho com ?page_size= (máximo 1000)."""

    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000
