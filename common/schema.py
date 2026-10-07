import logging
import secrets
from smtplib import SMTPException

import graphene
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id

from admissions.models import Admission
from common.decorators import (
    gql_feature_flag_required,
    gql_has_permissions,
    gql_login_required,
)
from common.exceptions import IllegalOperation
from common.models import FeatureFlag
from common.util import check_feature_flag, send_email
from django.core.cache import cache
from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
from schedules.schemas.schedules import ShiftSlotNode
from summaries.schema import SummaryNode
from summaries.models import Summary
from quotes.schema import QuoteNode
from quotes.models import Quote
from users.schema import UserNode
from economy.models import SociBankAccount, Deposit
from django.conf import settings


class FeatureFlagNode(DjangoObjectType):
    class Meta:
        model = FeatureFlag
        interfaces = (graphene.relay.Node,)


class DashboardData(graphene.ObjectType):
    last_quotes = graphene.NonNull(graphene.List(graphene.NonNull(QuoteNode)))
    last_summaries = graphene.NonNull(graphene.List(graphene.NonNull(SummaryNode)))
    wanted_list = graphene.NonNull(graphene.List(graphene.NonNull(UserNode)))
    my_upcoming_shifts = graphene.NonNull(
        graphene.List(graphene.NonNull(ShiftSlotNode))
    )
    soci_order_session = graphene.Field("economy.schema.SociOrderSessionNode")
    show_newbies = graphene.Boolean()
    show_stock_market_shortcut = graphene.Boolean()
    show_feedback = graphene.Boolean()


class SidebarData(graphene.ObjectType):
    pending_quotes = graphene.Int()
    pending_deposits = graphene.Int()


class SidebarQuery(graphene.ObjectType):
    sidebar_data = graphene.Field(SidebarData)

    def resolve_sidebar_data(self, info, *args, **kwargs):
        pending_quotes = Quote.get_pending_quotes().count()
        pending_deposits = Deposit.get_pending_deposits().count()
        return SidebarData(
            pending_quotes=pending_quotes, pending_deposits=pending_deposits
        )


class DashboardQuery(graphene.ObjectType):
    dashboard_data = graphene.Field(graphene.NonNull(DashboardData))

    @gql_login_required()
    def resolve_dashboard_data(self, info, *args, **kwargs):
        me = info.context.user
        quotes = Quote.objects.filter(approved=True).order_by("-created_at")[:5]
        summaries = Summary.objects.all().order_by("-date")[:6]
        wanted = SociBankAccount.get_wanted_list()
        upcoming_shifts = me.future_shifts
        soci_order_session = me.get_invited_soci_order_session

        admission = Admission.get_last_closed_admission()
        if not admission:
            show_newbies = False
        elif not admission.closed_at:
            show_newbies = False
        else:
            delta_since_closed = timezone.now() - admission.closed_at
            show_newbies = delta_since_closed.days < 30

        show_stock_market_shortcut = check_feature_flag(
            settings.X_APP_STOCK_MARKET_MODE, fail_silently=True
        )
        show_feedback = check_feature_flag(
            settings.FEEDBACK_FEATURE_FLAG, fail_silently=True
        )
        return DashboardData(
            last_quotes=quotes,
            last_summaries=summaries,
            wanted_list=wanted,
            my_upcoming_shifts=upcoming_shifts,
            soci_order_session=soci_order_session,
            show_newbies=show_newbies,
            show_stock_market_shortcut=show_stock_market_shortcut,
            show_feedback=show_feedback,
        )


class FeatureFlagQuery(graphene.ObjectType):
    all_feature_flags = graphene.List(graphene.NonNull(FeatureFlagNode))
    get_feature_flag_by_key = graphene.Field(
        FeatureFlagNode, key=graphene.String(required=True)
    )
    truth_or_drink_enabled = graphene.NonNull(graphene.Boolean)

    def resolve_all_feature_flags(self, info, *args, **kwargs):
        return FeatureFlag.objects.all()

    def resolve_get_feature_flag_by_key(self, info, key, *args, **kwargs):
        flag, _ = FeatureFlag.objects.get_or_create(name=key)
        return flag

    @gql_login_required()
    def resolve_truth_or_drink_enabled(self, info, *args, **kwargs):
        return check_feature_flag(
            settings.TRUTH_OR_DRINK_FEATURE_FLAG, fail_silently=True
        )


class ToggleFeatureFlagMutation(graphene.Mutation):
    class Arguments:
        feature_flag_id = graphene.ID(required=True)

    feature_flag = graphene.Field(FeatureFlagNode)

    @gql_has_permissions("common.change_featureflag")
    def mutate(self, info, feature_flag_id, *args, **kwargs):
        feature_flag_id = disambiguate_id(feature_flag_id)
        feature_flag = FeatureFlag.objects.get(id=feature_flag_id)
        feature_flag.enabled = not feature_flag.enabled
        feature_flag.save()

        return ToggleFeatureFlagMutation(feature_flag=feature_flag)


logger = logging.getLogger(__name__)

FEEDBACK_MAX_LENGTH = 500
FEEDBACK_PER_HOUR = 5


class SendFeedbackMutation(graphene.Mutation):
    """
    Sends feedback from the dashboard as an email to settings.FEEDBACK_EMAIL.
    Off until the settings.FEEDBACK_FEATURE_FLAG feature flag is enabled.
    Without `anonymous`, the email has the name and email of the user, so
    KSG-IT can answer. There is no Reply-To header: with one, the samfundet.no
    spam filter rejected the email. The request log still has the user id
    (common.middleware.RequestLogMiddleware).
    """

    class Arguments:
        message = graphene.String(required=True)
        anonymous = graphene.Boolean(required=True)

    ok = graphene.Boolean()

    @gql_login_required()
    @gql_feature_flag_required(settings.FEEDBACK_FEATURE_FLAG)
    def mutate(self, info, message, anonymous):
        user = info.context.user
        message = message.strip()
        if not message:
            raise IllegalOperation("Tilbakemeldingen er tom")
        if len(message) > FEEDBACK_MAX_LENGTH:
            raise IllegalOperation(
                f"Tilbakemeldingen kan ha maks {FEEDBACK_MAX_LENGTH} tegn"
            )

        # The default cache is per process, so the limit is per uWSGI worker.
        # It stops a loop or a spammer, not a careful attacker.
        key = f"feedback:{user.pk}"
        sent = cache.get(key, 0)
        if sent >= FEEDBACK_PER_HOUR:
            raise IllegalOperation(
                "Du har sendt mange tilbakemeldinger. Prøv igjen senere."
            )

        if anonymous:
            sender = "Anonym"
        else:
            sender = f"{user.get_full_name()} <{user.email}>"

        # A reference per submission. A unique subject makes each feedback its
        # own thread in the mail client.
        reference = secrets.token_hex(3).upper()

        # An HTML version, as in the other emails from KSG-nett
        html_message = (
            f"<p><strong>Fra:</strong> {escape(sender)}</p>"
            f"<p>{linebreaksbr(message, autoescape=True)}</p>"
            '<hr><p style="color:#868e96;font-size:12px">'
            f"Sendt fra tilbakemeldingsskjemaet på KSG-nett. Referanse: {reference}."
            f"{'' if anonymous else ' Svar til e-postadressen over.'}"
            "</p>"
        )
        try:
            sent_ok = send_email(
                subject=f"Tilbakemelding fra KSG-nett #{reference}",
                message=f"Fra: {sender}\n\n{message}\n\nReferanse: {reference}\n",
                html_message=html_message,
                recipients=[settings.FEEDBACK_EMAIL],
                fail_silently=False,
            )
        except (SMTPException, OSError) as error:
            # Log the reason, not the message of the member
            logger.warning("Feedback email %s not sent: %r", reference, error)
            raise IllegalOperation(
                "Tilbakemeldingen kunne ikke sendes. Prøv igjen senere, "
                f"eller send en e-post til {settings.FEEDBACK_EMAIL}."
            )
        cache.set(key, sent + 1, timeout=60 * 60)
        return SendFeedbackMutation(ok=bool(sent_ok))


class CommonMutations(graphene.ObjectType):
    toggle_feature_flag = ToggleFeatureFlagMutation.Field()
    send_feedback = SendFeedbackMutation.Field()
