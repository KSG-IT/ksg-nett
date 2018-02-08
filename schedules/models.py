from django.db import models

from organization.models import InternalGroup
from users.models import User


class Schedule(models.Model):
    """
    The Schedule model contains the entire schedule for one type of shifts.
    I.e. all 'Bodega'-shifts have one schedule, all 'Lyche kjøkken'-shifts have one schedule,
    and so on.
    """
    name = models.CharField(max_length=100)

    def __str__(self):
        return "Schedule %s" % self.name

    def __repr__(self):
        return "Schedule(name=%s)" % self.name

    class Meta:
        verbose_name_plural = 'schedules'


class ShiftSlotGroup(models.Model):
    """
    The ShiftSlotGroup model represents a grouping of slots that are occurring at the same time.
    The reason this is interesting is that people who work at the same time might want to connect.
    And we also want to group them in presentational circumstances.
    """
    name = models.CharField(max_length=100)
    schedule = models.ForeignKey(Schedule, null=False, blank=False, on_delete=models.CASCADE)

    meet_time = models.DateTimeField(null=False, blank=False)
    start_time = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return "ShiftSlotGroup %s for schedule %s" % (self.name, self.schedule.name)

    def __repr__(self):
        return "ShiftSlotGroup(name=%s, schedule=%s)" % (self.name, self.schedule.name)

    class Meta:
        verbose_name_plural = 'shift slot groups'
        unique_together = (('name', 'schedule',),)


class ScheduleSlotType(models.Model):
    """
    This model represents a type of slot that can be employed in a schedules shifts.
    This would typically be values like "Hovmester", "Barsjef", etc.
    """
    name = models.CharField(max_length=100, null=False, blank=False)
    schedule = models.ForeignKey(Schedule, null=False, blank=False, on_delete=models.CASCADE)

    # This model describes what type of role is associated with
    # the slot type. For instance is Hovmester a "funkevakt", and Barservitør a "gjengisvakt".
    # TODO: Add choices when the new organization branch is merged
    role = models.CharField(max_length=32)

    # This fields represents which groups will be used in an automatic generation
    # of a schedule
    standard_groups = models.ManyToManyField(InternalGroup, blank=True)

    def __str__(self):
        return "ScheduleSlotType %s for schedule %s" % (self.name, self.schedule.name)

    def __repr__(self):
        return "ScheduleSlotType(name=%s, schedule=%s)" % (self.name, self.schedule.name)

    class Meta:
        verbose_name_plural = 'schedule slot types'
        unique_together = (('name', 'schedule',),)


class ShiftSlot(models.Model):
    """
    The ShiftSlot model represents a shift that is due to be or is filled by a person.
    """
    start = models.TimeField(blank=False, null=False)
    end = models.TimeField(blank=False, null=False)

    type = models.ForeignKey(ScheduleSlotType, null=False, blank=False, on_delete=models.CASCADE)
    group = models.ForeignKey(ShiftSlotGroup, null=False, blank=False, on_delete=models.CASCADE)

    def __str__(self):
        return "%s in %s from %s to %s" % (
            self.type.name,
            self.group.name,
            self.start.strftime("%H:%M"),
            self.end.strftime("%H:%M")
        )

    def __repr__(self):
        return "ShiftSlot(type=%s, group=%s, from=%s, to=%s)" % (
            self.type.name,
            self.group.name,
            self.start.strftime("%H:%M"),
            self.end.strftime("%H:%M")
        )

    class Meta:
        verbose_name_plural = 'Shift slots'


class Shift(models.Model):
    """
    The Shift model represents a shift-slot filled by
    a person.
    """
    user = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE)
    slot = models.OneToOneField(
        ShiftSlot,
        null=False,
        blank=False,
        related_name='filled_shift',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "Shift %s taken by %s" % (str(self.slot), self.user.first_name)

    def __repr__(self):
        return "Shift(slot=%d, user=%s)" % (self.slot.id, self.user.first_name)

    class Meta:
        verbose_name_plural = 'shifts'


class ScheduleTemplate(models.Model):
    """
    This model contains a template for a schedules standard week. A schedule may have
    several templates.
    """
    name = models.CharField(max_length=100)
    schedule = models.ForeignKey(Schedule, blank=False, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return "Template %s for schedule %s" % (self.name, self.schedule.name)

    def __repr__(self):
        return "ScheduleTemplate(name=%s, schedule=%s)" % (self.name, self.schedule.name)

    class Meta:
        verbose_name_plural = 'schedule templates'
        unique_together = (('name', 'schedule',),)


class ShiftSlotGroupTemplate(models.Model):
    """
    This model represents a template for a ShiftSlotGroup.

    The model contains some additional information over a ShiftSlot, namely the rules
    for when the shift slot is supposed to occur.
    """
    name = models.CharField(max_length=100)
    schedule_template = models.ForeignKey(ScheduleTemplate, blank=False, null=False, on_delete=models.CASCADE)

    meet_time = models.TimeField(blank=False, null=False)
    start_time = models.TimeField(blank=False, null=False)

    def __str__(self):
        return "Template for ShiftSlotGroup %s for schedule-template %s" % (self.name, self.schedule_template.name)

    def __repr__(self):
        return "ShiftSlotGroupTemplate(name=%s, schedule_template=%s" % (self.name, self.schedule_template.name)

    class Meta:
        verbose_name_plural = 'shift slot group templates'


class ShiftSlotDayRule(models.Model):
    """
    This model represents a rule for what days a ShiftSlotGroup can occur
    """
    DAY_RULES = (
        ('mo', 'Monday'),
        ('tu', 'Tuesday'),
        ('we', 'Wednesday'),
        ('th', 'Thursday'),
        ('fr', 'Friday'),
        ('sa', 'Saturday'),
        ('su', 'Sunday'),
        ('wk', 'Weekdays'),
        ('ed', 'Weekends'),  # Friday, Saturday
        ('fu', 'Full weekends'),  # Friday, Saturday, Sunday
    )
    rule = models.CharField(max_length=2, choices=DAY_RULES)
    shift_slot_template = models.ForeignKey(ShiftSlotGroupTemplate, related_name='day_rules', on_delete=models.CASCADE)

    def __str__(self):
        return "Rule %s for shift slot group %s" % (self.get_rule_display(), self.shift_slot_template.name)

    def __repr__(self):
        return "ShiftSlotDayRule(rule=%s, shift_slot_template=%s)" % (self.get_rule_display(), self.shift_slot_template)

    class Meta:
        verbose_name_plural = 'Shift slot day rules'
        unique_together = (('rule', 'shift_slot_template',),)


class ShiftSlotTemplate(models.Model):
    """
    This model represents a template for a ShiftSlot.
    """
    start = models.TimeField(blank=False, null=False)
    end = models.TimeField(blank=False, null=False)

    type = models.ForeignKey(ScheduleSlotType, null=False, blank=False, on_delete=models.CASCADE)
    group = models.ForeignKey(ShiftSlotGroupTemplate, null=False, blank=False, on_delete=models.CASCADE)

    def __str__(self):
        return "Template for shift slot with type %s in %s at %s to %s" % (
            self.type,
            self.group.name,
            self.start.strftime("%H:%M"),
            self.end.strftime("%H:%M")
        )

    def __repr__(self):
        return "ShiftSlotTemplate(type=%s,group=%s,start=%s,end=%s" % (
            self.type,
            self.group.name,
            self.start.strftime("%H:%M"),
            self.end.strftime("%H:%M")
        )

    class Meta:
        verbose_name_plural = 'Shift slot templates'


class ShiftTrade(models.Model):
    """
    This model represents a trade of shifts.

    If taker and shift_taker is none, the shift trade is still "open for business".
    When these variables are set, the shift is set as "committed". For the trade to
    be 'valid' we also introduce a variable signed_off_by, which states which user
    has signed off the shift-trade. When this variable is set, the trade is valid.
    """

    offeror = models.ForeignKey(
        User,
        blank=False,
        null=False,
        related_name='shifts_offered',
        on_delete=models.CASCADE
    )
    shift_offer = models.ForeignKey(
        Shift,
        blank=False,
        null=False,
        related_name='offered_in_trades',
        on_delete=models.CASCADE
    )

    taker = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='shifts_taken',
        on_delete=models.SET_NULL
    )
    shift_taker = models.ForeignKey(
        Shift,
        blank=True,
        null=True,
        related_name='taken_in_trades',
        on_delete=models.SET_NULL
    )
    signed_off_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        related_name='shift_trades_signed_off',
        on_delete=models.SET_NULL
    )

    @property
    def valid(self):
        return self.signed_off_by is not None and \
               self.taker is not None and \
               self.shift_taker is not None

    @property
    def committed(self):
        return self.taker is not None and self.shift_taker is not None

    def __str__(self):
        return "Shift trade offered by %s" % (self.offeror.first_name,)

    def __repr__(self):
        return "ShiftTrade(offeror=%s)" % (self.offeror.first_name,)

    class Meta:
        verbose_name_plural = 'Shift trade'


class ShiftTradeOffer(models.Model):
    """
    This model represents an offer to a ShiftTrade.

    When accepted, the offeror and shift_offer variables of this model will be
    transferred to the related ShiftTrade model.
    """

    shift_trade = models.ForeignKey(
        ShiftTrade,
        blank=False,
        null=False,
        related_name='counter_offers',
        on_delete=models.CASCADE
    )

    offeror = models.ForeignKey(
        User,
        blank=False,
        null=False,
        related_name='shift_offers',
        on_delete=models.CASCADE
    )
    shift_offer = models.ForeignKey(
        Shift,
        blank=False,
        null=False,
        related_name='offered_to_shifts',
        on_delete=models.CASCADE
    )

    accepted = models.BooleanField(default=False, null=False, blank=False)

    def __str__(self):
        return "Counter trade by %s to shift offered by %s" % (
            self.offeror.first_name,
            self.shift_trade.offeror.first_name
        )

    def __repr__(self):
        return "ShiftTradeOffer(from=%s, as_counter_to=%s)" % (
            self.offeror.first_name,
            self.shift_trade.offeror.first_name
        )

    class Meta:
        verbose_name_plural = 'Shift trade offer'


class ShiftSlotGroupInterest(models.Model):
    """
    This model represents an interest a user has in a specific shift group. This will
    ensure that the user is sent notifications when shifts are up for trade in the given
    group.
    """
    shift_group = models.ForeignKey(
        ShiftSlotGroup,
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name='shifts_interests',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "Interest in shift group %s by %s" % (
            self.shift_group.name,
            self.user.first_name
        )

    def __repr__(self):
        return "ShiftSlotGroupInterest(shift_group=%s, user=%s)" % (
            self.shift_group.name,
            self.user.first_name
        )

    class Meta:
        verbose_name_plural = 'Shift slot group interest'
        unique_together = (('shift_group', 'user'),)
