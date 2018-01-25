from django.db import models


class Commission(models.Model):
    """
    A commissions (verv) in KSG. A commissions can be shared by many users (e.g. Personal),
    or created specifically for this internal group (e.g. Hybelbarsjef)
    """

    name = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return "Commission %s" % (self.name,)

    def __repr__(self):
        return "Commission(name=%s)" % (self.name,)
