from rest_framework.pagination import PageNumberPagination


class AlbumPagination(PageNumberPagination):
	page_size = 24
	page_query_param = 'page'
	max_page_size = 50


class AlbumRatingsPagination(PageNumberPagination):
	page_size = 10
	page_query_param = 'album_page'
	max_page_size = 50


class SongRatingsPagination(PageNumberPagination):
	page_size = 10
	page_query_param = 'song_page'
	max_page_size = 50


class WantToListenPagination(PageNumberPagination):
	page_size = 10
	page_query_param = 'page'
	max_page_size = 50
