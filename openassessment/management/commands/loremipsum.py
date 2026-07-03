"""
Stub for the old, unmaintained loremipsum package.
"""


def get_sentences(num: int) -> list[str]:
    """
    Returns up to 5 sentences.
    """
    sentences = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Donec commodo at dui dictum rutrum.",
        "Sed quis sodales nisl.",
        "Aenean at ultricies tortor. Nunc nec dictum diam.",
        "Integer suscipit, mi quis accumsan cursus, magna augue aliquam dui, in laoreet metus odio vitae nisl.",
    ]
    return sentences[:num]


def get_paragraphs(num: int) -> list[str]:
    """
    Returns up to 5 paragraphs.
    """
    paragraphs = [
        (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec commodo at dui dictum rutrum. Sed quis"
            "sodales nisl. Aenean at ultricies tortor. Nunc nec dictum diam. Integer suscipit, mi quis accumsan"
            "cursus, magna augue aliquam dui, in laoreet metus odio vitae nisl. Mauris eget sem ut magna egestas"
            "laoreet vitae quis purus. Aenean sodales tincidunt mi, vitae consequat quam eleifend sed. Suspendisse"
            "dictum dolor velit, id auctor turpis molestie eu. Suspendisse porta luctus dolor non tincidunt. In hac"
            "habitasse platea dictumst. Aenean semper lorem quis nisi blandit luctus. Nullam sed consequat tellus,"
            "et dapibus nisi. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus"
            "mus. Mauris aliquet mattis nulla non congue."
        ),
        (
            "Fusce laoreet sapien in pretium dictum. Aenean vel feugiat massa, at cursus nisi. Donec convallis"
            "consequat diam blandit tristique. Pellentesque egestas gravida gravida. Suspendisse ac volutpat nulla."
            "Duis at porta augue. Proin quis eleifend nisi."
        ),
        (
            "Vivamus volutpat, est id pretium commodo, ex risus condimentum nunc, et sodales dui nisi tempor enim."
            "Curabitur efficitur nec ipsum a commodo. Vivamus a dolor libero. Maecenas ipsum lorem, condimentum non"
            "gravida id, finibus vel orci. Interdum et malesuada fames ac ante ipsum primis in faucibus. Etiam"
            "dictum rhoncus accumsan. Mauris vel magna elit. Sed nec dui a felis dapibus faucibus. Fusce tincidunt"
            "est in leo semper, ac interdum dolor venenatis. Fusce in ultricies quam, in egestas nisi. Phasellus"
            "nec tellus magna. Curabitur eu orci ante. Proin non scelerisque lacus. Phasellus nec lobortis orci."
        ),
        (
            "Donec id quam ut arcu sodales imperdiet. Sed ullamcorper tellus dolor, quis sagittis mi hendrerit nec."
            "Nunc condimentum porta tellus vitae ornare. Fusce sit amet diam eros. Integer pretium sapien sit amet"
            "sodales congue. Vivamus mattis dui ac consectetur viverra. Duis blandit eu metus et accumsan. In in"
            "sem sed mauris varius sagittis a ac lectus."
        ),
        (
            "Vivamus tempor augue ut augue efficitur, nec fringilla sem bibendum. Aliquam rhoncus consequat metus"
            "nec gravida. Duis a suscipit turpis. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices"
            "posuere cubilia curae; Nunc convallis dui eget arcu sodales, a pretium nisl molestie. Pellentesque"
            "rhoncus eros ac tellus vestibulum faucibus ut ut neque. Vivamus eu fringilla velit. Suspendisse sed"
            "auctor felis. Suspendisse at orci lorem. Mauris lacinia ex egestas diam condimentum efficitur vel a"
            "est.  Quisque sed sem placerat, finibus libero in, iaculis nisl. Integer nulla urna, pulvinar sit amet"
            "malesuada in, vulputate sed quam."
        ),
    ]
    return paragraphs[:num]


def get_words(num: int) -> list[str]:
    """
    Returns up to 10 words.
    """
    words = get_sentence().split()
    return words[:num]


def get_sentence() -> str:
    """
    Returns a single sentence string.
    """
    return get_sentences(1)[0]
