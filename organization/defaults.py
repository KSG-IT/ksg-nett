from organization.models import InternalGroup

default_internal_group_data = [
    {
        "name": "Edgar",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Edgar er en kafé",
        "positions": [
            {
                "name": "Kaféansvarlig",
                "description": "Kaféansvarlige er skiftlederne i Edgar",
                "available_externally": False,
            },
            {
                "name": "Barista",
                "description": "Baristaene er ansvarlige for å lage kaffe",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Bargjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Bargjengen drifter 18-årsbarene i KSG",
        "positions": [
            {
                "name": "Barsjef",
                "description": "Barsjefene er skiftlederne i 18-årsbarene våre",
                "available_externally": False,
            },
            {
                "name": "Bartender",
                "description": "Bartenderne er ansvarlige for å tappe øl",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Spritgjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Spritgjengen drifter 20-årsbarene i KSG",
        "positions": [
            {
                "name": "Spritbarsjef",
                "description": "Spritbarsjefene er skiftlederne i 20-årsbarene våre",
                "available_externally": False,
            },
            {
                "name": "Spritbartender",
                "description": "Spritbartenderne er ansvarlige for å tappe sprit",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Lyche bar",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Lyche bar drifter baren i Lyche",
        "positions": [
            {
                "name": "Hovmester",
                "description": "Hovmesteren er skiftleder i Lyche bar",
                "available_externally": False,
            },
            {
                "name": "Barservitør",
                "description": "Barservitørene er ansvarlige for å tappe øl",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Lyche kjøkken",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Lyche kjøkken lager mat til Lyche",
        "positions": [
            {
                "name": "Souschef",
                "description": "Souschefen er ansvarlig for å lage mat",
                "available_externally": False,
            },
            {
                "name": "Kokk",
                "description": "Kokkene er ansvarlige for å lage mat",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Arrangement",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Arrangement er ansvarlig for å arrangere arrangementer",
        "positions": [
            {
                "name": "Arrangementsansvarlig",
                "description": "Arrangementsansvarlige er ansvarlige for å arrangere arrangementer",
                "available_externally": False,
            },
            {
                "name": "Arrangementbartender",
                "description": "Arrangementbartenderne er ansvarlige for å tappe øl på arrangementer",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Daglighallen bar",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Daglighallen bar drifter baren i Daglighallen",
        "positions": [
            {
                "name": "Daglighallenansvarlig",
                "description": "Daglighallenansvarlige er ansvarlige for å drifte baren i Daglighallen",
                "available_externally": False,
            },
            {
                "name": "Daglighallenbartender",
                "description": "Daglighallenbartenderne er ansvarlige for å tappe øl i Daglighallen",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Daglighallen mikrobryggeri",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Daglighallen mikrobryggeri lager øl i Daglighallen",
        "positions": [
            {
                "name": "Brygger",
                "description": "Bryggerne er ansvarlige for å lage øl i Daglighallen",
                "available_externally": True,
            },
        ],
    },
    {
        "name": "Økonomigjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Økonomigjengen er ansvarlig for økonomi i KSG",
        "positions": [
            {
                "name": "Økonomiansvarlig",
                "description": "Økonomiansvarlige er ansvarlige for økonomi i KSG",
                "available_externally": False,
            },
        ],
    },
    {
        "name": "Styret",
        "type": InternalGroup.Type.INTERNAL_GROUP,
        "description": "Styret har det overordnede ansvaret for KSG",
        "positions": [
            {
                "name": "Gjengsjef",
                "description": "Gjengsjefen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Styremedlem",
                "description": "Styremedlemmer er ansvarlige for KSG",
                "available_externally": False,
            },
            {
                "name": "Nestleder",
                "description": "Nestlederen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Prosjektleder",
                "description": "Prosjektlederen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Økonomisjef",
                "description": "Økonomisjefen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Lagersjef",
                "description": "Lagersjefen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Lycheansvarlig",
                "description": "Lycheansvarlige er ansvarlige for KSG",
                "available_externally": False,
            },
            {
                "name": "Daglighallenansvarlig",
                "description": "Daglighallenansvarlige er ansvarlige for KSG",
                "available_externally": False,
            },
            {
                "name": "Edgar- og Arrangementansvarlig",
                "description": "Edgar- og Arrangementansvarlige er ansvarlige for KSG",
                "available_externally": False,
            },
            {
                "name": "Bar- og Spritansvarlig",
                "description": "Bar- og Spritansvarlige er ansvarlige for KSG",
                "available_externally": False,
            },
            {
                "name": "Utstyrssjef",
                "description": "Utstyrssjefen er ansvarlig for KSG",
                "available_externally": False,
            },
            {
                "name": "Koordineringssjef",
                "description": "Koordineringssjefen er ansvarlig for KSG",
                "available_externally": False,
            },
        ],
    },
    {
        "name": "KSG-IT",
        "type": InternalGroup.Type.INTEREST_GROUP,
        "description": "KSG-IT er ansvarlig for IT i KSG",
        "positions": [
            {
                "name": "KSG-IT sjef",
                "description": "KSG-IT sjefen er ansvarlig for IT i KSG",
                "available_externally": False,
            },
            {
                "name": "Utvikler",
                "description": "Utviklerne er ansvarlige for IT i KSG",
                "available_externally": False,
            },
        ],
    },
    {
        "name": "Påfyll",
        "type": InternalGroup.Type.INTEREST_GROUP,
        "description": "Påfyll er fotballaget til KSG",
        "positions": [
            {
                "name": "Påfyll sjef",
                "description": "Påfyll sjefen er ansvarlig for fotballaget til KSG",
                "available_externally": False,
            },
            {
                "name": "Påfyll medlem",
                "description": "Møter opp på en kamp her og der",
                "available_externally": False,
            },
        ],
    },
]
