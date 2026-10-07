from django.contrib import admin
from django.db.models import Count

from economy.models import (
    Deposit,
    DepositComment,
    SociBankAccount,
    SociProduct,
    SociSession,
    ProductOrder,
    Transfer,
    SociOrderSession,
    SociOrderSessionOrder,
    ExternalCharge,
    ProductGhostOrder,
    SociRankedSeason,
)


def _account_owner(account):
    # SociBankAccount.__str__ includes the balance, which is noise in list columns
    return account.user if account else None


@admin.register(SociBankAccount)
class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "card_uuid", "balance"]
    list_filter = ["user__is_active"]
    readonly_fields = ["balance"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "card_uuid",
    ]
    autocomplete_fields = ["user"]

    def get_queryset(self, request):
        # __str__ renders the user, also in autocomplete results. A
        # select_related() here makes the changelist ignore list_select_related.
        return super().get_queryset(request).select_related("user")


@admin.register(SociProduct)
class SociProductAdmin(admin.ModelAdmin):
    list_display = [
        "sku_number",
        "icon",
        "name",
        "price",
        "description",
        "start",
        "type",
    ]
    list_filter = [
        "type",
        "hide_from_api",
        "default_stilletime_product",
    ]
    search_fields = ["name", "sku_number"]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ["id", "source_user", "destination_user", "amount", "created_at"]
    list_select_related = ["source__user", "destination__user"]
    list_filter = ["created_at"]
    search_fields = [
        "source__user__first_name",
        "source__user__last_name",
        "destination__user__first_name",
        "destination__user__last_name",
    ]
    autocomplete_fields = ["source", "destination"]

    @admin.display(description="Source", ordering="source__user__first_name")
    def source_user(self, transfer):
        return _account_owner(transfer.source)

    @admin.display(description="Destination", ordering="destination__user__first_name")
    def destination_user(self, transfer):
        return _account_owner(transfer.destination)


class DepositCommentInline(admin.TabularInline):
    model = DepositComment
    extra = 0
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at"]


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "amount",
        "deposit_method",
        "has_receipt",
        "approved",
        "created_at",
    ]
    list_select_related = ["account__user"]
    list_filter = [
        "approved",
        "deposit_method",
        "stripe_payment_intent_status",
        "created_at",
    ]
    search_fields = [
        "account__user__username",
        "account__user__first_name",
        "account__user__last_name",
        "description",
        "stripe_payment_id",
    ]
    date_hierarchy = "created_at"
    autocomplete_fields = ["account", "approved_by"]
    inlines = [DepositCommentInline]

    @admin.display(ordering="account__user__first_name")
    def user(self, deposit: Deposit):
        return _account_owner(deposit.account)

    @admin.display(boolean=True)
    def has_receipt(self, deposit):
        return bool(deposit.receipt)


@admin.register(SociSession)
class SociSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "type",
        "creation_date",
        "created_at",
        "closed_at",
        "created_by",
        "client_user_agent",
        "product_order_count",
    ]
    list_select_related = ["created_by"]
    list_filter = ["type", "created_at"]
    search_fields = ["name"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["created_by"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(product_order_count=Count("product_orders"))
        )

    @admin.display(description="Product orders", ordering="product_order_count")
    def product_order_count(self, session):
        return session.product_order_count


@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "product",
        "order_size",
        "cost",
        "user",
        "session_display",
        "purchased_at",
    ]
    list_select_related = ["product", "source__user", "session"]
    list_filter = ["purchased_at", "session__type", "product"]
    search_fields = [
        "source__user__username",
        "source__user__first_name",
        "source__user__last_name",
    ]
    autocomplete_fields = ["product", "source", "session"]
    # Counting every product order on each page load is slow on a large table
    show_full_result_count = False

    @admin.display(ordering="source__user__first_name")
    def user(self, product_order: ProductOrder):
        return _account_owner(product_order.source)

    @admin.display(description="Session", ordering="session")
    def session_display(self, product_order: ProductOrder):
        # SociSession.__str__ runs a count query for each row
        session = product_order.session
        return f"{session.id}: {session.name or session.get_type_display()}"


class SociOrderSessionOrderInline(admin.TabularInline):
    model = SociOrderSessionOrder
    extra = 0
    autocomplete_fields = ["user", "product"]


@admin.register(SociOrderSession)
class SociOrderSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "created_at", "closed_at", "created_by"]
    list_select_related = ["created_by"]
    list_filter = ["status", "created_at"]
    filter_horizontal = ("invited_users",)
    autocomplete_fields = ["created_by", "closed_by"]
    inlines = [SociOrderSessionOrderInline]


@admin.register(SociOrderSessionOrder)
class UserSociOrderSessionCollectionAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "user", "product", "amount", "ordered_at"]
    list_select_related = ["session", "user", "product"]
    list_filter = ["session__status", "product"]
    search_fields = ["user__first_name", "user__last_name", "product__name"]
    autocomplete_fields = ["user", "product"]


@admin.register(ExternalCharge)
class ExternalChargeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "bar_tab_customer",
        "amount",
        "reference",
        "user",
        "created_at",
        "webhook_success",
        "webhook_attempts",
    ]
    list_select_related = ["bar_tab_customer", "bank_account__user"]
    list_filter = ["bar_tab_customer", "webhook_success", "created_at"]
    search_fields = [
        "reference",
        "bank_account__user__first_name",
        "bank_account__user__last_name",
    ]
    autocomplete_fields = ["bank_account"]

    @admin.display(ordering="bank_account__user__first_name")
    def user(self, external_charge: ExternalCharge):
        return _account_owner(external_charge.bank_account)


@admin.register(ProductGhostOrder)
class ProductGhostOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "timestamp"]
    list_select_related = ["product"]
    list_filter = ["timestamp", "product"]
    show_full_result_count = False


@admin.register(SociRankedSeason)
class SociRankedSeasonAdmin(admin.ModelAdmin):
    list_display = ["id", "participant_count", "season_start_date", "season_end_date"]
    filter_horizontal = ("participants",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(participant_count=Count("participants"))
        )

    @admin.display(description="Participants", ordering="participant_count")
    def participant_count(self, soci_ranked_season: SociRankedSeason):
        return soci_ranked_season.participant_count
