from django.contrib import admin
from .models import PurchaseTransactionLogEntry, BlacklistedSong


class BlacklistedSongAdmin(admin.ModelAdmin):
    list_display = ["name", "spotify_song_id", "blacklisted_until", "blacklisted_by"]


admin.site.register(PurchaseTransactionLogEntry)
admin.site.register(BlacklistedSong, BlacklistedSongAdmin)
