from django.contrib import admin

from .models import Album, Artist, Genre, Song


@admin.action(description='Approve selected items')
def approve_selected(modeladmin, request, queryset):
	queryset.update(is_approved=True)


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'genres')
	search_fields = ('name', 'slug', 'aliases')
	ordering = ('is_approved', '-created_at')
	actions = (approve_selected,)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
	list_display = ('title', 'artist', 'slug', 'release_date', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'genres', 'release_date')
	search_fields = ('title', 'slug', 'artist__name')
	ordering = ('is_approved', '-created_at')
	actions = (approve_selected,)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
	list_display = ('title', 'artist', 'album', 'track_number', 'slug', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'genres')
	search_fields = ('title', 'slug', 'artist__name', 'album__title')
	ordering = ('is_approved', '-created_at')
	actions = (approve_selected,)


admin.site.register(Genre)
