from datetime import timedelta
import hypothesis.strategies as hyp

SAMPLE_URLS = [
    "https://www.theatlantic.com/magazine/archive/2019/04/adam-serwer-madison-grant-white-nationalism/583258/",
    "https://jlc.org/news/advocates-encouraged-governors-new-reform-effort",
    "https://lawatthemargins.com/selfcareforactivists-08072019",
    "https://foodfirst.org/publication/the-people-went-walking-how-rufino-dominguez-revolutionized-the-way-we-think-about-migration-part-i/",
    "https://www.greatfallstribune.com/story/news/local/2015/04/16/grandparents-protest-child-protective-services/25904331",
    "https://theintercept.com/2019/08/07/el-paso-border-war-terror/",
    "https://www.washingtonpost.com/lifestyle/2019/08/09/caught-between-young-kids-parent-with-alzheimers-i-found-lifeline-playground/",
    "https://www.nytimes.com/2019/08/20/us/california-police-use-of-force-law.html",
    "https://www.bloomberg.com/news/articles/2019-08-19/oil-companies-persuade-states-to-make-pipeline-protests-a-felony",
    "https://medium.com/brepairers/10-statistics-worse-than-the-trade-deficit-3a0352d3090d",
]


def url_examples(urls=SAMPLE_URLS):
    return hyp.sampled_from(urls)


def article_data_examples(dates_near=None, dates_range=(7, 7)):
    if dates_near is None:
        date_gen = hyp.dates().map(lambda d: d.strftime("%Y-%m-%d"))
    else:
        min_value = dates_near - timedelta(days=dates_range[0])
        max_value = dates_near + timedelta(days=dates_range[1])
        date_gen = hyp.dates(min_value=min_value, max_value=max_value).map(
            lambda d: d.strftime("%Y-%m-%d")
        )

    return hyp.fixed_dictionaries(
        {
            "$type": hyp.just("Article"),
            "title": hyp.text(),
            "authors": hyp.lists(hyp.text()),
            "encoding": hyp.just("utf8"),
            "raw_html": hyp.text(),
            "text": hyp.text(),
            "html": hyp.text(),
            "publish_date": hyp.none() | date_gen,
            "summary": hyp.none() | hyp.text(),
            "site_name": hyp.none() | hyp.text(),
        }
    )
