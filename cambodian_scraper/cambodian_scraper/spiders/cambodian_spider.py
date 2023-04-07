import scrapy
from scrapy.loader import ItemLoader
from parsel import Selector
from cambodian_scraper.items import CambodianCompanyItem
from scrapy_playwright.page import PageMethod
from bs4 import BeautifulSoup
from lxml import etree


class CambodianSpiderSpider(scrapy.Spider):
    name = "cambodian_spider"
    allowed_domains = ["www.businessregistration.moc.gov.kh"]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    def start_requests(self):
        for link in range(1, int(2)):
            url = "https://www.businessregistration.moc.gov.kh/cambodia-master/relay.html?url=https%3A%2F%2Fwww.businessregistration.moc.gov.kh%2Fcambodia-master%2Fservice%2Fcreate.html%3FtargetAppCode%3Dcambodia-master%26targetRegisterAppCode%3Dcambodia-br-companies%26service%3DregisterItemSearch&target=cambodia-master"
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "//h1[@class='appPageTitle']"),
                        PageMethod(
                            "fill", value="000", selector="//input[@id='QueryString']"
                        ),
                        PageMethod(
                            "click",
                            selector="//a[contains (@class, 'registerItemSearch-tabs-criteriaAndButtons-buttonPad-search appSearchButton')]",
                        ),
                        PageMethod(
                            "wait_for_selector",
                            "//div[@class='appRepeaterRowContent appRowOdd appRowFirst']",
                        ),
                        PageMethod(
                            "click",
                            selector="//div[@class='appSearchPageSize']/select",
                        ),
                        PageMethod(
                            "press",
                            key="ArrowDown+ArrowDown+ArrowDown+ArrowDown",
                            selector="//div[@class='appSearchPageSize']/select",
                        ),
                        PageMethod(
                            "press",
                            key="Enter",
                            selector="//div[@class='appSearchPageSize']/select",
                        ),
                        PageMethod(
                            "wait_for_selector",
                            "//div[contains (@class, 'appRepeaterRowContent')][200]",
                        ),
                    ],
                    errback=self.errback,
                    link=link,
                ),
                dont_filter=True,
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        company = response.meta["link"]
        if company / 200 > 1:
            for _ in range(int(company / 200)):
                await page.click(
                    f"//div[@class='appPagerContainer appPagerContainerFooter appPagerCount11']//div[@class='appNext appNextEnabled']/a"
                )
                await page.wait_for_selector(
                    "//div[@class='appRepeaterRowContent appRowOdd appRowFirst']"
                )

        remainder = company % 200
        if remainder == 0:
            remainder = 200

        # l = ItemLoader(item=CambodianCompanyItem(), response=response)
        # word = l.get_xpath(
        #     "//*[@id='cambodia-master_registerItemSearch']/span/text()",
        # )
        # print("===============================")
        # print(word)
        # print("===============================")

        await page.click(
            f"//div[contains (@class, 'appRepeaterRowContent')][{remainder}]//a"
        )
        await page.wait_for_selector(
            "//*[@id='cambodia-br-companies_brViewLocalCompany']/span"
        )
        # name = await page.evaluate(
        #     "document.querySelector('#nodeW1026 > div.appAttrValue');"
        # )
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        dom = etree.HTML(str(soup))
        l = ItemLoader(item=CambodianCompanyItem())
        await self.scrape_general(dom, l)
        return l.load_item()
        # print("==========================")
        # print(
        #     dom.xpath(
        #         "//div[@class='appTabSelected']//div[@class='appAttrLabelBox appCompanyName']/../div[2]"
        #     )[0].text
        # )
        # print("==========================")

    #     await page.close()
    #     # return l.load_item()

    async def scrape_general(self, dom, l):
        company_name_in_english = dom.xpath(
            "//div[@class='appTabSelected']//div[@class='appAttrLabelBox appCompanyName']/../div[2]"
        )[0].text
        l.add_value("company_name_in_english", company_name_in_english)
        # await self.scrape_addresses(response)

    # async def scrape_addresses(self, response):
    #     print("___________________")
    #     print("scraped addresses")
    #     print("___________________")
    #     await self.scrape_directors(response)

    # async def scrape_directors(self, response):
    #     print("___________________")
    #     print("scraped directors")
    #     print("___________________")

    async def errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
