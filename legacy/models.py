# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Arrangementer(models.Model):
    # MIGRATE to shift
    dato = models.DateField()
    bar = models.ForeignKey("Barer", models.DO_NOTHING, db_column="bar")
    tittel = models.TextField(blank=True, null=True)
    beskrivelse = models.TextField(blank=True, null=True)
    bestillernavn = models.TextField(blank=True, null=True)
    bestillertelefon = models.TextField(blank=True, null=True)
    starttid = models.IntegerField(blank=True, null=True)
    stopptid = models.IntegerField(blank=True, null=True)
    booker = models.ForeignKey("Personer", models.DO_NOTHING, db_column="booker")
    aapningstid = models.TimeField(blank=True, null=True)
    stengetid = models.TimeField(blank=True, null=True)
    oppmote = models.DurationField(blank=True, null=True)
    omsetning = models.IntegerField(blank=True, null=True)
    erfaringer = models.TextField(blank=True, null=True)
    stengetid_synlig = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Arrangementer"
        unique_together = (("bar", "dato"),)


class Bsf(models.Model):
    registrert = models.DateTimeField()
    beskrivelse = models.TextField()
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    publisert = models.BooleanField()
    stengt = models.BooleanField()

    class Meta:
        managed = False
        db_table = "BSF"


class Bsfgjenger(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    gjengnavn = models.TextField()
    hybelnavn = models.TextField()
    beskrivelse = models.TextField(blank=True, null=True)
    saldo = models.FloatField()

    class Meta:
        managed = False
        db_table = "BSFGjenger"


class Bsfkryssborte(models.Model):
    bsf = models.ForeignKey(Bsf, models.DO_NOTHING, db_column="bsf")
    gjeng = models.ForeignKey(Bsfgjenger, models.DO_NOTHING, db_column="gjeng")
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    belop = models.FloatField()
    registrert = models.DateTimeField(blank=True, null=True)
    kommentar = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "BSFKryssBorte"


class Bsfkrysshjemme(models.Model):
    bsf = models.ForeignKey(Bsf, models.DO_NOTHING, db_column="bsf")
    gjeng = models.ForeignKey(Bsfgjenger, models.DO_NOTHING, db_column="gjeng")
    person = models.TextField()
    belop = models.FloatField()
    registrert = models.DateTimeField(blank=True, null=True)
    kommentar = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "BSFKryssHjemme"


class Bsfoverforinger(models.Model):
    gjeng = models.ForeignKey(Bsfgjenger, models.DO_NOTHING, db_column="gjeng")
    belop = models.FloatField()
    registrert = models.DateTimeField()
    kommentar = models.TextField()

    class Meta:
        managed = False
        db_table = "BSFOverforinger"


class Barer(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    navn = models.TextField(blank=True, null=True)
    kortnavn = models.TextField(blank=True, null=True)
    rekkefolge = models.IntegerField(blank=True, null=True)
    robokopid = models.IntegerField(blank=True, null=True)
    limid = models.IntegerField(blank=True, null=True)
    oppmote = models.DurationField()
    type = models.ForeignKey("Bartyper", models.DO_NOTHING, db_column="type")

    class Meta:
        managed = False
        db_table = "Barer"


class Bartyper(models.Model):
    id = models.TextField(primary_key=True)
    navn = models.TextField()

    class Meta:
        managed = False
        db_table = "Bartyper"


class Bartypervakttyper(models.Model):
    bartype = models.OneToOneField(
        Bartyper, models.DO_NOTHING, db_column="bartype", primary_key=True
    )
    vakttype = models.ForeignKey("Vakttyper", models.DO_NOTHING, db_column="vakttype")

    class Meta:
        managed = False
        db_table = "BartyperVakttyper"
        unique_together = (("bartype", "vakttype"),)


class Bildefavoritter(models.Model):
    album = models.TextField()
    bilde = models.TextField()
    person = models.IntegerField()

    class Meta:
        managed = False
        db_table = "Bildefavoritter"


class Bildekommentarer(models.Model):
    album = models.CharField(max_length=40)
    bilde = models.CharField(max_length=100)
    tekst = models.TextField()
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    registrert = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "Bildekommentarer"


class Bilderpersoner(models.Model):
    album = models.CharField(max_length=40)
    bilde = models.CharField(max_length=100)
    person = models.IntegerField()

    class Meta:
        managed = False
        db_table = "BilderPersoner"


class Chat(models.Model):
    tid = models.DateTimeField(primary_key=True)
    person = models.IntegerField()
    melding = models.CharField(max_length=300)

    class Meta:
        managed = False
        db_table = "Chat"


class Galleri(models.Model):
    id = models.CharField(primary_key=True, max_length=40)
    tittel = models.TextField()
    tekst = models.TextField()
    fotograf = models.ForeignKey("Personer", models.DO_NOTHING, db_column="fotograf")
    tid = models.DateTimeField(blank=True, null=True)
    knipsetid = models.DateField(blank=True, null=True)
    publisert = models.BooleanField()
    godkjent = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Galleri"


class Grupper(models.Model):
    navn = models.TextField(blank=True, null=True)
    beskrivelse = models.TextField(blank=True, null=True)
    historikk = models.BooleanField()
    aktiv = models.BooleanField()
    stillingsnavn = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Grupper"


class Grupperhistorikk(models.Model):
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    gruppe = models.ForeignKey(Grupper, models.DO_NOTHING, db_column="gruppe")
    fradato = models.DateField()
    tildato = models.DateField(blank=True, null=True)
    merknad = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "GrupperHistorikk"


class Innkryssinger(models.Model):
    # MIGRATE
    registrert = models.DateTimeField()
    kryssetid = models.DateTimeField()
    kommentar = models.TextField(blank=True, null=True)
    lukket = models.BooleanField()
    innkrysser = models.ForeignKey(
        "Personer", models.DO_NOTHING, db_column="innkrysser", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "Innkryssinger"


class Innskudd(models.Model):
    # MIGRATE
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    registrert = models.DateTimeField()
    penger = models.FloatField()
    type = models.CharField(max_length=1)
    godkjent = models.BooleanField()
    kommentar = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Innskudd"


class Intervjuer(models.Model):
    semester = models.ForeignKey("Opptak", models.DO_NOTHING, db_column="semester")
    navn = models.TextField()
    adresse = models.TextField()
    hjemadresse = models.TextField()
    studie = models.TextField()
    fodselsdato = models.DateField()
    tattopp = models.BooleanField()
    telefon = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    by = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Intervjuer"
        unique_together = (("semester", "email"),)


class Kryss(models.Model):
    # MIGRATE
    innkryssing = models.ForeignKey(
        Innkryssinger, models.DO_NOTHING, db_column="innkryssing"
    )
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    vare = models.ForeignKey("Varer", models.DO_NOTHING, db_column="vare")
    kryssetid = models.DateTimeField(blank=True, null=True)
    antall = models.FloatField()
    pris = models.FloatField()

    class Meta:
        managed = False
        db_table = "Kryss"


class Lister(models.Model):
    tittel = models.TextField(blank=True, null=True)
    beskrivelse = models.TextField(blank=True, null=True)
    sql = models.TextField(blank=True, null=True)
    tommefelter = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    tekst = models.TextField(blank=True, null=True)
    synlig = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Lister"


class Opptak(models.Model):
    id = models.CharField(primary_key=True, max_length=6)
    lukket = models.BooleanField()
    kommentar = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Opptak"


class Overforinger(models.Model):
    # MIGRATE

    fra = models.ForeignKey(
        "Personer", models.DO_NOTHING, db_column="fra", related_name="overfort_fra"
    )
    til = models.ForeignKey(
        "Personer", models.DO_NOTHING, db_column="til", related_name="overfort_til"
    )
    belop = models.IntegerField()
    kommentar = models.TextField(blank=True, null=True)
    registrert = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Overforinger"


class Paameldinger(models.Model):
    tittel = models.TextField()
    tekst = models.TextField()
    maksantall = models.IntegerField(blank=True, null=True)
    startdato = models.DateTimeField()
    sluttdato = models.DateTimeField()
    stengt = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Paameldinger"


class Paameldingergrupper(models.Model):
    paameldingid = models.ForeignKey(
        Paameldinger, models.DO_NOTHING, db_column="paameldingid"
    )
    gruppeid = models.ForeignKey(Grupper, models.DO_NOTHING, db_column="gruppeid")

    class Meta:
        managed = False
        db_table = "PaameldingerGrupper"


class Paameldingerpersoner(models.Model):
    paameldingid = models.ForeignKey(
        Paameldinger, models.DO_NOTHING, db_column="paameldingid"
    )
    personid = models.ForeignKey("Personer", models.DO_NOTHING, db_column="personid")

    class Meta:
        managed = False
        db_table = "PaameldingerPersoner"


class Paameldingerstatus(models.Model):
    paameldingid = models.ForeignKey(
        Paameldinger, models.DO_NOTHING, db_column="paameldingid"
    )
    statusid = models.ForeignKey("Status", models.DO_NOTHING, db_column="statusid")

    class Meta:
        managed = False
        db_table = "PaameldingerStatus"


class Pengekasseoverforinger(models.Model):
    kasse = models.ForeignKey("Pengekasser", models.DO_NOTHING, db_column="kasse")
    belop = models.IntegerField()
    person = models.ForeignKey("Personer", models.DO_NOTHING, db_column="person")
    beskrivelse = models.TextField(blank=True, null=True)
    tid = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "PengekasseOverforinger"


class Pengekasser(models.Model):
    navn = models.TextField()
    beskrivelse = models.TextField(blank=True, null=True)
    saldo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "Pengekasser"


class Personer(models.Model):
    # MIGRATE
    email = models.TextField(unique=True, blank=True, null=True)
    passord = models.CharField(max_length=32)
    kortnummer = models.CharField(max_length=10, blank=True, null=True)
    status = models.ForeignKey("Status", models.DO_NOTHING, db_column="status")
    navn = models.TextField(blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    hjemstedsadresse = models.TextField(blank=True, null=True)
    studie = models.TextField(blank=True, null=True)
    fodselsdato = models.DateField(blank=True, null=True)
    telefon = models.TextField(blank=True, null=True)
    begynte = models.CharField(max_length=6, blank=True, null=True)
    saldo = models.FloatField()
    sistonline = models.DateTimeField(blank=True, null=True)
    login = models.TextField(blank=True, null=True)
    by = models.TextField(blank=True, null=True)
    stilling = models.ForeignKey(
        Grupper, models.DO_NOTHING, db_column="stilling", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "Personer"


class Personergrupper(models.Model):
    personid = models.OneToOneField(
        Personer, models.DO_NOTHING, db_column="personid", primary_key=True
    )
    gruppeid = models.ForeignKey(Grupper, models.DO_NOTHING, db_column="gruppeid")

    class Meta:
        managed = False
        db_table = "PersonerGrupper"
        unique_together = (("personid", "gruppeid"),)


class Quizfolk(models.Model):
    person = models.ForeignKey(Personer, models.DO_NOTHING, db_column="person")
    treff = models.BooleanField()

    class Meta:
        managed = False
        db_table = "QuizFolk"


class Quizresultater(models.Model):
    type = models.TextField()
    person = models.ForeignKey(Personer, models.DO_NOTHING, db_column="person")
    resultat = models.FloatField()
    tid = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "QuizResultater"


class Referater(models.Model):
    # MIGRATE
    dato = models.DateField()
    tittel = models.TextField()
    tilstede = models.TextField()
    innhold = models.TextField()
    referent = models.ForeignKey(Personer, models.DO_NOTHING, db_column="referent")
    registrert = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "Referater"


class Sider(models.Model):
    kategori = models.CharField(max_length=30)
    navn = models.CharField(primary_key=True, max_length=30)
    tittel = models.CharField(max_length=100, blank=True, null=True)
    tekst = models.TextField(blank=True, null=True)
    html = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Sider"


class Sitater(models.Model):
    # MIGRATE

    tid = models.DateTimeField()
    tekst = models.TextField()
    godkjent = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Sitater"


class Socisanger(models.Model):
    tid = models.DateTimeField(unique=True)
    url = models.TextField()
    tittel = models.TextField()

    class Meta:
        managed = False
        db_table = "Socisanger"


class Soknader(models.Model):
    semester = models.ForeignKey(Opptak, models.DO_NOTHING, db_column="semester")
    navn = models.TextField()
    telefon = models.TextField()
    email = models.TextField()

    class Meta:
        managed = False
        db_table = "Soknader"


class Status(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    navn = models.TextField(blank=True, null=True)
    beskrivelse = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Status"


class Statushistorikk(models.Model):
    person = models.ForeignKey(Personer, models.DO_NOTHING, db_column="person")
    status = models.ForeignKey(Status, models.DO_NOTHING, db_column="status")
    fradato = models.DateField()
    tildato = models.DateField(blank=True, null=True)
    merknad = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "StatusHistorikk"


class Tilganger(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    tittel = models.TextField()
    beskrivelse = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Tilganger"


class Tilgangergrupper(models.Model):
    tilgang = models.OneToOneField(
        Tilganger, models.DO_NOTHING, db_column="tilgang", primary_key=True
    )
    gruppe = models.ForeignKey(Grupper, models.DO_NOTHING, db_column="gruppe")

    class Meta:
        managed = False
        db_table = "TilgangerGrupper"
        unique_together = (("tilgang", "gruppe"),)


class Tilgangerstatus(models.Model):
    tilgang = models.OneToOneField(
        Tilganger, models.DO_NOTHING, db_column="tilgang", primary_key=True
    )
    status = models.ForeignKey(Status, models.DO_NOTHING, db_column="status")

    class Meta:
        managed = False
        db_table = "TilgangerStatus"
        unique_together = (("tilgang", "status"),)


class Vakter(models.Model):
    # MIGRATE

    arrangement = models.ForeignKey(
        Arrangementer, models.DO_NOTHING, db_column="arrangement"
    )
    type = models.ForeignKey("Vakttyper", models.DO_NOTHING, db_column="type")
    person = models.ForeignKey(
        Personer, models.DO_NOTHING, db_column="person", blank=True, null=True
    )
    notified = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Vakter"


class Vaktonske(models.Model):
    arrangement_id = models.IntegerField()
    person_id = models.IntegerField()
    status = models.CharField(max_length=20, blank=True, null=True)
    type = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Vaktonske"


class VaktonskeArrangement(models.Model):
    aapn_dato = models.DateField(blank=True, null=True)
    onskbar = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Vaktonske_arrangement"


class Vakttyper(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    navn = models.TextField()
    kortnavn = models.TextField()
    color = models.CharField(max_length=6, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Vakttyper"


class Varer(models.Model):
    # MIGRATE
    navn = models.TextField(blank=True, null=True)
    beskrivelse = models.TextField(blank=True, null=True)
    pris = models.FloatField()
    andrepris = models.FloatField()
    bokstav = models.CharField(max_length=1, blank=True, null=True)
    bildenavn = models.CharField(max_length=30, blank=True, null=True)
    liter = models.FloatField(blank=True, null=True)
    volumprosent = models.FloatField(blank=True, null=True)
    synlig = models.BooleanField()
    pricelist = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Varer"


class Verv(models.Model):
    navn = models.TextField()
    status = models.ForeignKey(Status, models.DO_NOTHING, db_column="status")
    person = models.ForeignKey(
        Personer, models.DO_NOTHING, db_column="person", blank=True, null=True
    )
    aktiv = models.BooleanField()

    class Meta:
        managed = False
        db_table = "Verv"


class Vervhistorikk(models.Model):
    verv = models.ForeignKey(Verv, models.DO_NOTHING, db_column="verv")
    person = models.ForeignKey(Personer, models.DO_NOTHING, db_column="person")
    fradato = models.DateField()
    tildato = models.DateField(blank=True, null=True)
    merknad = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "VervHistorikk"


class Ekstern(models.Model):
    navn = models.CharField(primary_key=True, max_length=30)
    tittel = models.CharField(max_length=100, blank=True, null=True)
    tekst = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "_Ekstern"


class Gammelpersoner(models.Model):
    personid = models.IntegerField(
        db_column="PersonID", blank=True, null=True
    )  # Field name made lowercase.
    gjengid = models.IntegerField(
        db_column="GjengID", blank=True, null=True
    )  # Field name made lowercase.
    navn = models.TextField(
        db_column="Navn", blank=True, null=True
    )  # Field name made lowercase.
    kortnr = models.TextField(
        db_column="Kortnr", blank=True, null=True
    )  # Field name made lowercase.
    saldo = models.FloatField(
        db_column="Saldo", blank=True, null=True
    )  # Field name made lowercase.
    saldodato = models.TextField(
        db_column="SaldoDato", blank=True, null=True
    )  # Field name made lowercase.
    email = models.TextField(
        db_column="Email", blank=True, null=True
    )  # Field name made lowercase.
    sistsjekket = models.TextField(
        db_column="SistSjekket", blank=True, null=True
    )  # Field name made lowercase.
    socikryss = models.IntegerField(
        db_column="SociKryss", blank=True, null=True
    )  # Field name made lowercase.
    uglekryss = models.IntegerField(
        db_column="UgleKryss", blank=True, null=True
    )  # Field name made lowercase.
    huskryss = models.IntegerField(
        db_column="HusKryss", blank=True, null=True
    )  # Field name made lowercase.
    stilletimekryss = models.IntegerField(
        db_column="StilleTimeKryss", blank=True, null=True
    )  # Field name made lowercase.
    kryssenavn = models.TextField(
        db_column="KrysseNavn", blank=True, null=True
    )  # Field name made lowercase.
    adminnivå = models.IntegerField(
        db_column="AdminNivå", blank=True, null=True
    )  # Field name made lowercase.
    passord = models.TextField(
        db_column="Passord", blank=True, null=True
    )  # Field name made lowercase.
    gammeltkryssenavn = models.TextField(
        db_column="GammeltKrysseNavn", blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = "_GammelPersoner"


class Sidetider(models.Model):
    side = models.TextField()
    tid = models.FloatField()

    class Meta:
        managed = False
        db_table = "_SideTider"


class Tempgammelny(models.Model):
    gammel = models.IntegerField()
    ny = models.IntegerField()

    class Meta:
        managed = False
        db_table = "_TempGammelNy"


class Jubileum(models.Model):
    navn = models.TextField(blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    telefon = models.TextField(blank=True, null=True)
    kontonummer = models.TextField(blank=True, null=True)
    begyntesg = models.TextField(blank=True, null=True)
    studie = models.TextField(blank=True, null=True)
    verv = models.TextField(blank=True, null=True)
    notater = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "_jubileum"


class AdodbLogsql(models.Model):
    created = models.DateTimeField()
    sql0 = models.CharField(max_length=250)
    sql1 = models.TextField()
    params = models.TextField()
    tracer = models.TextField()
    timer = models.DecimalField(max_digits=16, decimal_places=6)

    class Meta:
        managed = False
        db_table = "adodb_logsql"


class Logg(models.Model):
    person = models.ForeignKey(Personer, models.DO_NOTHING, db_column="person")
    starttid = models.DateTimeField()
    stopptid = models.DateTimeField()
    ip = models.TextField(blank=True, null=True)
    useragent = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "logg"


class LoggSider(models.Model):
    url = models.TextField(unique=True)
    tittel = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "logg_sider"


class LoggSiderTreff(models.Model):
    besok = models.ForeignKey(Logg, models.DO_NOTHING, db_column="besok")
    side = models.ForeignKey(LoggSider, models.DO_NOTHING, db_column="side")

    class Meta:
        managed = False
        db_table = "logg_sider_treff"
