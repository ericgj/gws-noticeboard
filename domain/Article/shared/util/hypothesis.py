import hypothesis.strategies as hyp


def text(alphabet, min_size=0, max_size=None):
    """ 
    A more user-friendly hypothesis.strategies.text for typical UTF8 
    cases. Pass in a literal string of valid characters.
    """
    return hyp.lists(characters(alphabet), min_size=min_size, max_size=max_size).map(
        lambda cs: "".join(cs)
    )


def characters(alphabet):
    """ 
    A more user-friendly hypothesis.strategies.characters for typical UTF8
    cases. Pass in a literal string of valid characters.
    """
    return hyp.sampled_from(range(0, len(alphabet))).map(lambda i: alphabet[i])
