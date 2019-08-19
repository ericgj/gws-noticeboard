import hypothesis.strategies as hyp

from model.article import Request

SAMPLE_URLS = [
    "https://www.theatlantic.com/magazine/archive/2019/04/adam-serwer-madison-grant-white-nationalism/583258/",
    "https://jlc.org/news/advocates-encouraged-governors-new-reform-effort",
    "https://lawatthemargins.com/selfcareforactivists-08072019",
    "https://foodfirst.org/publication/the-people-went-walking-how-rufino-dominguez-revolutionized-the-way-we-think-about-migration-part-i/",
    "https://www.greatfallstribune.com/story/news/local/2015/04/16/grandparents-protest-child-protective-services/25904331",
    "https://theintercept.com/2019/08/07/el-paso-border-war-terror/",
    "https://www.washingtonpost.com/lifestyle/2019/08/09/caught-between-young-kids-parent-with-alzheimers-i-found-lifeline-playground/",
]


def request_examples(urls=SAMPLE_URLS):
    return hyp.builds(Request, url=hyp.sampled_from(urls), note=hyp.none() | hyp.text())
