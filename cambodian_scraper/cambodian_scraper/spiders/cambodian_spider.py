import scrapy


class CambodianSpiderSpider(scrapy.Spider):
    name = 'cambodian_spider'
    allowed_domains = ['www.businessregistration.moc.gov.kh']
    start_urls = ['http://www.businessregistration.moc.gov.kh/']

    def parse(self, response):
        pass
