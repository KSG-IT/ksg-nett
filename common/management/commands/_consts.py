from organization.models import InternalGroup

SUMMARY_CONTENT = """
# Lorem ipsum dolor

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec pulvinar dui vel felis finibus tempus. Suspendisse finibus vehicula velit, eu suscipit augue mollis vehicula. Curabitur blandit aliquam eros ut accumsan. Maecenas sed diam hendrerit, fermentum lacus vitae, blandit felis. Nulla vitae ex auctor libero suscipit rhoncus eget et diam. Cras at aliquet libero. Nullam est velit, suscipit quis consectetur in, accumsan nec metus. Mauris dictum orci vel viverra eleifend. Nam in mattis ligula, sed ultrices magna. Morbi interdum convallis ex, eu semper sem blandit ut. Curabitur ac diam fringilla, iaculis neque quis, molestie magna. Sed id facilisis sem.

## Lorem ipsum dolor

Nam id mauris id massa porttitor mattis. Nunc a tortor turpis. Quisque mollis mattis dolor, non posuere mauris. Integer eget volutpat magna. Nunc odio velit, tempor vel mauris et, pulvinar faucibus nisl. In non orci nibh. Integer lacus orci, faucibus eget ornare non, sagittis nec augue. Curabitur eget accumsan ex. In viverra, arcu nec tincidunt egestas, urna justo feugiat risus, vitae posuere ipsum quam non ex. Mauris quis neque velit. In suscipit nulla sit amet nibh placerat vulputate. Nunc vestibulum, sem id ultricies cursus, ligula lectus dapibus nibh, et ullamcorper ipsum lorem eu arcu. Vivamus sagittis laoreet tempor.

### Lorem ipsum dolor

Cras lacinia, nulla sed dignissim interdum, velit nulla pretium risus, semper fringilla metus magna sit amet velit. In quis venenatis felis, quis commodo nunc. Cras aliquam velit ipsum, quis tristique purus sodales sit amet. Duis arcu lectus, finibus ut ligula non, fringilla porta elit. Maecenas non orci nibh. Pellentesque egestas, neque a auctor ultricies, mi elit faucibus nibh, vel sollicitudin massa enim eu diam. In consequat metus in pharetra hendrerit.
- Lorem
- Ipsum
- Dolor
- Sit
- Amet


### Lorem ipsum dolor

Cras lacinia, nulla sed dignissim interdum, velit nulla pretium risus, semper fringilla metus magna sit amet velit. In quis venenatis felis, quis commodo nunc. Cras aliquam velit ipsum, quis tristique purus sodales sit amet. Duis arcu lectus, finibus ut ligula non, fringilla porta elit. Maecenas non orci nibh. Pellentesque egestas, neque a auctor ultricies, mi elit faucibus nibh, vel sollicitudin massa enim eu diam. In consequat metus in pharetra hendrerit.

"""

QUOTE_CHOICES = [
    {
        "text": "Jeg liker det ikke, men det er jævlig hyggelig!",
        "context": "Mona om å bli tatt i 2ern",
    },
    {"text": "Er søstra di singel?", "context": None},
    {
        "text": "Hvis du er overtrøtt og har lyst på en psykotisk homoopplevelse…",
        "context": "Jan i ferd med å anbefale YouTube-serie",
    },
    {
        "text": "Jeg prøvde å løse et problem med regex, nå har jeg to problemer",
        "context": None,
    },
    {"text": "Det er siling, kan du dra hjem?", "context": None},
    {"text": "Er jeg ubrukelig", "context": None},
    {
        "text": "Sprit er sprit",
        "context": "Herman svarer på hvorfor de stakkars gjengisene må drikke Sirafan på Soci",
    },
    {
        "text": "Jeg prøvde å flame på nyttårsaften, men mamma var lame",
        "context": None,
    },
]

INTERNAL_GROUP_DATA = [
    {
        "name": "Edgar",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Barista", "available_externally": True},
            {"name": "Kaféansvarlig", "available_externally": False},
        ],
    },
    {
        "name": "Bargjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Bartender", "available_externally": True},
            {"name": "Barsjef", "available_externally": False},
        ],
    },
    {
        "name": "Spritgjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Spritbartender", "available_externally": True},
            {"name": "Spritbarsjef", "available_externally": False},
        ],
    },
    {
        "name": "Arrangement",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Arrangementbartender", "available_externally": True},
            {"name": "Arrangementansvarlig", "available_externally": False},
        ],
    },
    {
        "name": "Daglighallen bar",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Daglighallenbartender", "available_externally": True},
            {"name": "Daglighallenansvarlig", "available_externally": False},
        ],
    },
    {
        "name": "Daglighallen bryggeri",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Brygger", "available_externally": True},
            {"name": "Bryggansvarlig", "available_externally": False},
        ],
    },
    {
        "name": "KSG-IT",
        "type": InternalGroup.Type.INTEREST_GROUP.value,
        "positions": [
            {"name": "Utvikler", "available_externally": False},
        ],
    },
    {
        "name": "Pafyll",
        "type": InternalGroup.Type.INTEREST_GROUP.value,
        "positions": [
            {"name": "Medlem", "available_externally": False},
        ],
    },
    {
        "name": "Lyche bar",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Barservitør", "available_externally": True},
            {"name": "Hovmester", "available_externally": False},
        ],
    },
    {
        "name": "Lyche kjøkken",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Kokk", "available_externally": True},
            {"name": "Souschef", "available_externally": False},
        ],
    },
    {
        "name": "Økonomigjengen",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Økonomiansvarlig", "available_externally": True},
        ],
    },
    {
        "name": "Styret",
        "type": InternalGroup.Type.INTERNAL_GROUP.value,
        "positions": [
            {"name": "Styremedlem", "available_externally": False},
        ],
    },
]

BANK_ACCOUNT_BALANCE_CHOICES = [
    -500,
    -87,
    0,
    50,
    100,
    150,
    200,
    300,
    500,
    800,
    1500,
    3000,
]
