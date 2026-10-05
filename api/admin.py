from django.contrib import admin
from .models import PurchaseTransactionLogEntry, BlacklistedSong


class PurchaseTransactionLogEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "amount", "transaction_source", "timestamp"]
    list_select_related = ["user"]
    list_filter = ["transaction_source", "timestamp"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    autocomplete_fields = ["user"]
    # Counting every log entry on each page load is slow on a large table
    show_full_result_count = False


class BlacklistedSongAdmin(admin.ModelAdmin):
    list_display = ["name", "spotify_song_id", "blacklisted_until", "blacklisted_by"]
    list_select_related = ["blacklisted_by"]
    search_fields = ["name", "spotify_song_id"]
    autocomplete_fields = ["blacklisted_by"]


admin.site.register(PurchaseTransactionLogEntry, PurchaseTransactionLogEntryAdmin)
admin.site.register(BlacklistedSong, BlacklistedSongAdmin)
