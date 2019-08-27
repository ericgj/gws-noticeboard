import hypothesis.strategies as hyp

SAMPLE_URLS = [
    "https://www.history.com/news/american-slavery-before-jamestown-1619",
    "https://www.motherjones.com/politics/2019/08/anti-immigration-white-supremacy-has-deep-roots-in-the-environmental-movement/",
    "https://www.commondreams.org/views/2019/08/19/public-charge-rule-trumps-latest-attack-immigrants?utm_campaign=shareaholic&utm_medium=referral&utm_source=email_this",
    "https://www.nytimes.com/2019/08/20/us/california-police-use-of-force-law.html",
    "https://www.bloomberg.com/news/articles/2019-08-19/oil-companies-persuade-states-to-make-pipeline-protests-a-felony",
    "https://medium.com/brepairers/10-statistics-worse-than-the-trade-deficit-3a0352d3090d"
]

def fetch_article_data_examples():
    return hyp.fixed_dictionaries({
        '$type': hyp.always("FetchArticle"),
        'url': hyp.sampled_from(SAMPLE_URLS)
    })
