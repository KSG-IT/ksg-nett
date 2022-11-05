default_user_types = [
    {
        "name": "Administrator",
        "description": "En administrator har full tilgang utenom administrering av opptak",
        "requires_superuser": False,
        "requires_self": True,
        "permissions": [
            "users.add_user",
            "users.change_user",
            "users.view_user",
            "users.change_usertype",
            "users.view_usertype",
            "quotes.change_quote",
            "quotes.delete_quote",
            "quotes.view_quote",
            "quotes.add_quote",
            "admissions.view_admission",
            "admissions.view_applicant",
            "admissions.change_applicant",
            "admissions.view_applicant",
            "admissions.view_interview",
            "summaries.add_summary",
            "summaries.change_summary",
            "summaries.delete_summary",
            "summaries.view_summary",
            "schedules.view_schedule",
            "schedules.change_schedule",
            "schedules.add_schedule",
            "schedules.delete_schedule",
            "schedules.add_shift",
            "schedules.change_shift",
            "schedules.delete_shift",
            "schedules.view_shift",
            "schedules.view_shiftslot",
            "schedules.change_shiftslot",
            "schedules.delete_shiftslot",
            "schedules.add_shiftslot",
            "schedules.view_scheduletemplate",
            "schedules.change_scheduletemplate",
            "schedules.delete_scheduletemplate",
            "schedules.add_scheduletemplate",
            "schedules.view_shifttemplate",
            "schedules.change_shifttemplate",
            "schedules.delete_shifttemplate",
            "schedules.add_shifttemplate",
            "schedules.view_shiftslottemplate",
            "schedules.change_shiftslottemplate",
            "schedules.delete_shiftslottemplate",
            "schedules.add_shiftslottemplate",
            "schedules.view_shifttrade",
            "schedules.change_shifttrade",
            "schedules.delete_shifttrade",
            "schedules.add_shifttrade",
        ],
    },
    {
        "name": "Funksjonær",
        "description": "En funksjonær har tilgang intervjusystemet og oprretting/redigering av referater",
        "requires_superuser": False,
        "requires_self": False,
        "permissions": [
            "admissions.view_admission",
            "admissions.view_applicant",
            "admissions.change_applicant",
            "admissions.view_applicant",
            "admissions.view_interview",
            "summaries.add_summary",
            "summaries.change_summary",
            "summaries.view_summary",
        ],
    },
    {
        "name": "Personalansvarlig",
        "description": "En personalansvarlig har tilgang til vaktlistesystemet, endre personalopplysninger, og underkjenne sitater",
        "requires_superuser": False,
        "requires_self": False,
        "permissions": [
            "users.change_user",
            "users.view_user",
            "quotes.change_quote",
            "users.change_usertype",
            "users.view_usertype",
            "schedules.view_schedule",
            "schedules.change_schedule",
            "schedules.add_shift",
            "schedules.change_shift",
            "schedules.delete_shift",
            "schedules.view_shift",
            "schedules.view_shiftslot",
            "schedules.change_shiftslot",
            "schedules.delete_shiftslot",
            "schedules.add_shiftslot",
            "schedules.view_scheduletemplate",
            "schedules.change_scheduletemplate",
            "schedules.view_shifttemplate",
            "schedules.change_shifttemplate",
            "schedules.delete_shifttemplate",
            "schedules.add_shifttemplate",
            "schedules.view_shiftslottemplate",
            "schedules.change_shiftslottemplate",
            "schedules.delete_shiftslottemplate",
            "schedules.add_shiftslottemplate",
            "schedules.view_shifttrade",
            "schedules.change_shifttrade",
            "schedules.delete_shifttrade",
            "schedules.add_shifttrade",
        ],
    },
    {
        "name": "Økonomiansvarlig",
        "description": "En økonomiansvarlig har tilgang til BSF modulen og moderering av innskudd",
        "requires_superuser": False,
        "requires_self": True,
        "permissions": [
            "economy.view_deposit",
            "economy.change_deposit",
            "bar_tab.view_bartab",
            "bar_tab.change_bartab",
            "bar_tab.add_bartab",
            "economy.view_socisession",
            "economy.change_socisession",
            "economy.add_socisession",
        ],
    },
    {
        "name": "Opptaksadministrator",
        "requires_superuser": True,
        "requires_self": False,
        "description": "En opptaksadministrator har tilgang til opptaksmodulen og kan administrere brukere",
        "permissions": [
            "admissions.view_admission",
            "admissions.add_admission",
            "admissions.change_admission",
            "admissions.view_applicant",
            "admissions.change_applicant",
            "admissions.delete_applicant",
            "admissions.view_applicant",
            "admissions.view_interview",
        ],
    },
    {
        "name": "Velferdsansvarlig",
        "requires_superuser": False,
        "requires_self": False,
        "description": "En velferdsansvarlig har tilgang til velferdsmodulen og kan administrere brukere",
        "permissions": [
            "quotes.change_quote",
        ],
    },
    {
        "name": "Intervjuer",
        "description": "En intervjuer har tilgang til intervjumodulen, brukes for å gi tilgang til opptaket om man"
        "trenger hjelp med å holde intervjuer",
        "requires_superuser": False,
        "requires_self": False,
        "permissions": [
            "admissions.view_admission",
            "admissions.view_applicant",
            "admissions.change_applicant",
            "admissions.view_applicant",
            "admissions.view_interview",
        ],
    },
]

default_allergies = [
    "Laktose",
    "Gluten",
    "Melk",
    "Egg",
    "Sopp",
    "Nøtter: tåler spor",
    "Nøtter: literally dør",
    "Malt",
    "Scampi",
    "Kamskjell",
    "Appelsin",
    "Pecannøtter",
    "Mango",
    "Sitrus",
    "Rå epler",
    "Rå gulrøtter",
    "Rå fennikel",
    "Rå edamamebønner",
    "Sukkererter",
    "Kokos",
    "Avokado",
    "Solsikkekjerner",
    "Hasselnøtter",
    "Valnøtter",
    "Eple",
]
