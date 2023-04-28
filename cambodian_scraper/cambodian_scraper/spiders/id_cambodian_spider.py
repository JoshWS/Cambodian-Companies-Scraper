import scrapy
from scrapy.loader import ItemLoader
from parsel import Selector
from cambodian_scraper.items import CambodianCompanyIDItem
from scrapy_playwright.page import PageMethod
from bs4 import BeautifulSoup
from lxml import etree
import csv
import os.path
import math


class CambodianSpiderSpider(scrapy.Spider):
    name = "id_cambodian_spider"
    allowed_domains = ["www.businessregistration.moc.gov.kh"]
    custom_settings = {
        "ITEM_PIPELINES": None,
        "FEED_EXPORT_FIELDS": "company_ids",
    }
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
        url = "https://www.businessregistration.moc.gov.kh/cambodia-master/relay.html?url=https%3A%2F%2Fwww.businessregistration.moc.gov.kh%2Fcambodia-master%2Fservice%2Fcreate.html%3FtargetAppCode%3Dcambodia-master%26targetRegisterAppCode%3Dcambodia-br-companies%26service%3DregisterItemSearch&target=cambodia-master"
        yield scrapy.Request(
            url,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                playwright_page_methods=[
                    PageMethod("wait_for_selector", "//h1[@class='appPageTitle']"),
                    PageMethod(
                        "fill",
                        value="000",
                        selector="//input[@id='QueryString']",
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
                callback=self.parse,
                errback=self.errback,
            ),
            dont_filter=True,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        dom = etree.HTML(str(soup))

        l = ItemLoader(item=CambodianCompanyIDItem())

        await self.scrape_general(dom, l)
        current_page = 2
        while True:
            # for _ in range(1):
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            dom = etree.HTML(str(soup))

            next_page = dom.xpath(
                "//div[contains (@class, 'appPagerContainerHeader')]//div[@class='appNext appNextEnabled']/a"
            )
            if next_page:
                await page.click(
                    "//div[contains (@class, 'appPagerContainerHeader')]//div[@class='appNext appNextEnabled']/a"
                )
                await page.wait_for_selector(
                    f"//div[contains (@class, 'appPagerContainerHeader')]//div[@class='appPages']/span[text()='{current_page}']"
                )
                current_page += 1

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                dom = etree.HTML(str(soup))

                await self.scrape_general(dom, l)
            else:
                break

        await page.close()
        return l.load_item()

    async def scrape_general(self, dom, l):
        company_ids = dom.xpath(
            "//div[@class='appSearchResultsChildren']//span[@class='appReceiveFocus']"
        )
        for company_id in company_ids:
            company_id = company_id.text
            company_id = company_id.split("(")[-1].split(")")[0]
            l.add_value("company_ids", company_id)

    async def errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
