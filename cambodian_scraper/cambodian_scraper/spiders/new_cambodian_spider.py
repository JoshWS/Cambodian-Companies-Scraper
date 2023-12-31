import scrapy
from scrapy.loader import ItemLoader
from cambodian_scraper.items import CambodianCompanyItem
from scrapy_playwright.page import PageMethod
from bs4 import BeautifulSoup
from lxml import etree
import csv
import sys

csv.field_size_limit(sys.maxsize)


class CambodianSpiderSpider(scrapy.Spider):
    name = "new_cambodian_spider"
    allowed_domains = ["www.businessregistration.moc.gov.kh"]
    custom_settings = {
        "ITEM_PIPELINES": None,
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
        ids = []
        scraped_ids = []
        with open("id.csv", "r") as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            for id in csvreader:
                for x in id:
                    ids.append(x)
        ids = ids[0].split(",")

        with open("scraped_ids.csv", "r") as file:
            csvreader = csv.reader(file)
            for id in csvreader:
                for x in id:
                    scraped_ids.append(x)
        for x in ids:
            if not x in scraped_ids:
                url = "https://www.businessregistration.moc.gov.kh/cambodia-master/relay.html?url=https%3A%2F%2Fwww.businessregistration.moc.gov.kh%2Fcambodia-master%2Fservice%2Fcreate.html%3FtargetAppCode%3Dcambodia-master%26targetRegisterAppCode%3Dcambodia-br-companies%26service%3DregisterItemSearch&target=cambodia-master"
                yield scrapy.Request(
                    url,
                    meta=dict(
                        playwright=True,
                        playwright_include_page=True,
                        playwright_page_methods=[
                            PageMethod(
                                "wait_for_selector", "//h1[@class='appPageTitle']"
                            ),
                            PageMethod(
                                "fill",
                                value=f"{x}",
                                selector="//input[@id='QueryString']",
                            ),
                            PageMethod(
                                "click",
                                selector="//a[contains (@class, 'registerItemSearch-tabs-criteriaAndButtons-buttonPad-search appSearchButton')]",
                            ),
                            PageMethod(
                                "wait_for_selector",
                                "//div[contains (@class, 'appRepeaterRowContent appRowOdd appRowFirst')]//a[contains (@class, 'appItemSearchResult')]",
                            ),
                            PageMethod(
                                "click",
                                selector="//div[contains (@class, 'appRepeaterRowContent appRowOdd appRowFirst')]//a[contains (@class, 'appItemSearchResult')]",
                            ),
                            PageMethod(
                                "wait_for_selector",
                                "//div[contains (@class, 'NameInKhmer')]/div[2]",
                            ),
                        ],
                        callback=self.parse,
                        errback=self.errback,
                        id=x,
                    ),
                    dont_filter=True,
                )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        company_id = response.meta["id"]

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        dom = etree.HTML(str(soup))
        l = ItemLoader(item=CambodianCompanyItem())

        # Scrapes general company info from first tab.
        await self.scrape_general(dom, l, company_id)

        foreign_company = dom.xpath(
            "//div[contains (@class, 'brViewOverseasCompany-tabsBox')]/ul/li[2]/a/span"
        )
        if foreign_company:
            if foreign_company[0].text == "Parent Company":
                # Clicks on parent company tab and waits for it to load.
                await page.click(
                    "//ul[@class='appTabs']//span[contains (text(), 'Parent Company')]/.."
                )
                await page.wait_for_selector(
                    "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentCompanyName')]/div[2]"
                )

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                dom = etree.HTML(str(soup))

                await self.scrape_parent_company(dom, l)

        # Clicks on addresses tab and waits for it to load.
        await page.click(
            "//ul[@class='appTabs']//span[contains (text(), 'Addresses')]/.."
        )
        await page.wait_for_selector(
            "//div[contains (@class, 'Current')]//div[contains (@class, 'appPhysicalAddress')]//div[contains (@class, 'appAttribute address')]/div[2]"
        )

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        dom = etree.HTML(str(soup))

        # Scrapes address information.
        await self.scrape_addresses(dom, l)

        # Clicks on directors tab and wait for it to load.
        await page.click(
            "//ul[@class='appTabs']//span[contains (text(), 'Directors')]/.."
        )
        await page.wait_for_selector(
            "//div[@class='appTabSelected']//div[contains (@class, 'individualNameEnglish')]/div[2]"
        )

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        dom = etree.HTML(str(soup))

        # Scrapes directors.
        await self.scrape_directors(dom, l)

        # Keeps track of scraped companies.
        csvfile = open("scraped_ids.csv", "a", newline="")
        obj = csv.writer(csvfile)
        id = response.meta["id"]

        csvfileread = open("scraped_ids.csv", "r")
        read = csv.reader(csvfileread)
        numbers = []
        for row in read:
            for x in row:
                numbers.append(x)
        if not str(id) in numbers:
            id = str(id)
            current_number_fixed = [id]
            obj.writerow(current_number_fixed)

        csvfile.close()
        csvfileread.close()

        await page.close()
        return l.load_item()

    async def scrape_general(self, dom, l, company_id):
        # Scrapes company ID.
        l.add_value("company_id", company_id)

        # Scrapes company name in khmer.
        company_name_in_khmer = dom.xpath(
            "//div[contains (@class, 'NameInKhmer')]/div[2]"
        )
        if company_name_in_khmer:
            if not company_name_in_khmer[0].text == "\u00a0":
                l.add_value(
                    "company_name_in_khmer",
                    company_name_in_khmer[0].text,
                )

        # Scrapes company name in english.
        company_name_in_english = dom.xpath(
            "//div[@class='appTabSelected']//div[@class='appAttrLabelBox appCompanyName']/../div[2]"
        )
        if company_name_in_english:
            if not company_name_in_english[0].text == "\u00a0":
                l.add_value(
                    "company_name_in_english",
                    company_name_in_english[0].text,
                )

        # Scrapes original entity identifier.
        original_entity_identifier = dom.xpath(
            "//div[contains (@class, 'OriginalVersionIdentifier')]/div[2]"
        )
        if original_entity_identifier:
            if not (original_entity_identifier[0].text == "\u00a0"):
                l.add_value(
                    "original_entity_identifier",
                    original_entity_identifier[0].text,
                )

        # Scrapes company status.
        company_status = dom.xpath(
            "//div[contains (@class, 'Attribute-Status')]/div[2]"
        )
        if company_status:
            if not company_status[0].text == "\u00a0":
                l.add_value(
                    "company_status",
                    company_status[0].text,
                )

        # Scrapes incorporation date.
        incorporation_date = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-hideAttributesBox-RegistrationDate')]/div[2]"
        )
        if incorporation_date:
            if not incorporation_date[0].text == "\u00a0":
                l.add_value(
                    "incorporation_date",
                    incorporation_date[0].text,
                )

        # Scrapes re registration date.
        re_registration_date = dom.xpath(
            "//div[contains (@class, 'ReregistrationDate')]/div[2]"
        )
        if re_registration_date:
            if not re_registration_date[0].text == "\u00a0":
                l.add_value(
                    "re_registration_date",
                    re_registration_date[0].text,
                )

        # Scrapes tax identification number tin.
        tax_identification_number_tin = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-tinBox-taxIdentificationNumber-TIN appAttribute')]/div[2]"
        )
        if tax_identification_number_tin:
            if not (tax_identification_number_tin[0].text == "\u00a0"):
                l.add_value(
                    "tax_identification_number_tin",
                    tax_identification_number_tin[0].text,
                )

        # Scrapes tax registration date.
        tax_registration_date = dom.xpath(
            "//div[contains (@class, 'TINRegistrationDate')]/div[2]"
        )
        if tax_registration_date:
            if not (tax_registration_date[0].text == "\u00a0"):
                l.add_value(
                    "tax_registration_date",
                    tax_registration_date[0].text,
                )

        # Scrapes annual return last filed on date.
        annual_return_last_filed_on = dom.xpath(
            "//div[contains (@class, 'LatestAnnualFiling')]/div[2]"
        )
        if annual_return_last_filed_on:
            if not (annual_return_last_filed_on[0].text == "\u00a0"):
                l.add_value(
                    "annual_return_last_filed_on",
                    annual_return_last_filed_on[0].text,
                )

        # Scrapes business activities.
        business_activities = {}
        activities = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-localDetailsBox-companyDetails-localBusinessActivitiesBox-businessActivitiesBox-categorizerBoxBusinessActivities')]//div[contains (@class, 'appRepeaterRowContent')]"
        )
        for count in range(len(activities)):
            objective = dom.xpath(
                f"(//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-localDetailsBox-companyDetails-localBusinessActivitiesBox-businessActivitiesBox-categorizerBoxBusinessActivities')]//div[contains (@class, 'appRepeaterRowContent')][{count + 1}]//div[@class='appAttrValue'])[1]"
            )[0].text
            main_business_activities = dom.xpath(
                f"(//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-localDetailsBox-companyDetails-localBusinessActivitiesBox-businessActivitiesBox-categorizerBoxBusinessActivities')]//div[contains (@class, 'appRepeaterRowContent')][{count + 1}]//div[@class='appAttrValue'])[2]"
            )[0].text
            entry = {
                "objective": objective,
                "main_business_activities": main_business_activities,
            }
            business_activities[str(count)] = entry
        l.add_value("business_activities", business_activities)

        # Scrapes number of employees.
        number_of_employees = {}

        # Scrapes male employees.
        male = dom.xpath("//div[contains (@class, 'TotalEmployeesMale')]/div[2]")
        if male:
            if not (male[0].text == "\u00a0"):
                if not (male[0].text == "0"):
                    number_of_employees["male"] = male[0].text

        # Scrapes female employees.
        female = dom.xpath("//div[contains (@class, 'TotalEmployeesFemale')]/div[2]")
        if female:
            if not (female[0].text == "\u00a0"):
                if not (female[0].text == "0"):
                    number_of_employees["female"] = female[0].text

        # Scrapes number of cambodian employees.
        number_of_cambodian_employees = dom.xpath(
            "//div[contains (@class, 'TotalCambodianEmployees')]/div[2]"
        )
        if number_of_cambodian_employees:
            if not (number_of_cambodian_employees[0].text == "\u00a0"):
                if not (number_of_cambodian_employees[0].text == "0"):
                    number_of_employees[
                        "number_of_cambodian_employees"
                    ] = number_of_cambodian_employees[0].text

        # Scrapes number of foreign employees.
        number_of_foreign_employees = dom.xpath(
            "//div[contains (@class, 'TotalForeignEmployees')]/div[2]"
        )
        if number_of_foreign_employees:
            if not (number_of_foreign_employees[0].text == "\u00a0"):
                if not (number_of_foreign_employees[0].text == "0"):
                    number_of_employees[
                        "number_of_foreign_employees"
                    ] = number_of_foreign_employees[0].text
        if number_of_employees:
            l.add_value("number_of_employees", number_of_employees)

        # Scrapes previous company names.
        names = {}
        previous_names = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-historicalInformationBox-nameHistoryBox-previousEntityNames-previousEntityName')]//div[contains (@class, 'appAttrText')]"
        )
        if previous_names:
            for count in range(len(previous_names)):
                name = dom.xpath(
                    f"(//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-historicalInformationBox-nameHistoryBox-previousEntityNames-previousEntityName')]//div[contains (@class, 'appAttrText')]/div[2])[{count + 1}]"
                )
                names[str(count)] = name[0].text
            start_date = dom.xpath(
                f"//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-historicalInformationBox-nameHistoryBox-previousEntityNames-previousEntityName')]//div[contains (@class, 'StartDate')]/div[2]"
            )[0].text
            end_date = dom.xpath(
                f"//div[contains (@class, 'brViewLocalCompany-tabsBox-detailsTab-details-historicalInformationBox-nameHistoryBox-previousEntityNames-previousEntityName')]//div[contains (@class, 'EndDate')]/div[2]"
            )[0].text
            entry = {"names": names, "start_date": start_date, "end_date": end_date}
            l.add_value("previous_names", entry)

    async def scrape_parent_company(self, dom, l):
        # Scrapes parent company tab.
        full_name_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentCompanyName')]/div[2]"
        )[0].text
        address_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'postalAddressRoot')]/div[2]"
        )[0].text
        start_date = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'StartDate')]/div[2]"
        )[0].text
        commercial_registration_number_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentRegistrationNumber')]/div[2]"
        )[0].text
        date_of_registration_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentRegistrationDate')]/div[2]"
        )[0].text
        country_of_registration_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'appDc-country')]/div[2]"
        )[0].text
        further_details_of_jurisdiction_of_parent_company = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentJurisdictionDetails')]/div[2]"
        )

        criminal_conduct_and_consent = dom.xpath(
            "//div[@class='appTabSelected']//div[contains (@class, 'Attribute-ParentCompanyConsentYn')]/div[2]"
        )[0].text
        parent_company = {
            "full_name_of_parent_company": full_name_of_parent_company,
            "address_of_parent_company": address_of_parent_company,
            "start_date": start_date,
            "commercial_registration_number_of_parent_company": commercial_registration_number_of_parent_company,
            "date_of_registration_of_parent_company": date_of_registration_of_parent_company,
            "country_of_registration_of_parent_company": country_of_registration_of_parent_company,
            "criminal_conduct_and_consent": criminal_conduct_and_consent,
        }
        if further_details_of_jurisdiction_of_parent_company:
            if not (
                further_details_of_jurisdiction_of_parent_company[0].text == "\u00a0"
            ):
                if not (
                    further_details_of_jurisdiction_of_parent_company[0].text == "0"
                ):
                    parent_company[
                        "further_details_of_jurisdiction_of_parent_company"
                    ] = further_details_of_jurisdiction_of_parent_company[0].text
        l.add_value("parent_company", parent_company)

    async def scrape_addresses(self, dom, l):
        # Scrapes addresses.
        addresses = {}
        historic_physical_office_addresses = {}
        historic_postal_office_addresses = {}

        # Scrapes physical registered office addresses.
        Physical_registered_office_address = dom.xpath(
            "//div[contains (@class, 'Current')]//div[contains (@class, 'appPhysicalAddress')]//div[contains (@class, 'appAttribute address')]/div[2]"
        )[0].text
        start_date = dom.xpath(
            "(//div[contains (@class, 'Current')]//div[contains (@class, 'StartDate')]/div[2])[1]"
        )[0].text
        physical_office_addresses = {
            "Physical_registered_office_address": Physical_registered_office_address,
            "start_date": start_date,
        }
        addresses["physical_office_addresses"] = physical_office_addresses

        # Scrapes historic office addresses.
        historic_addresses = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-addressesTab-roaBox-registeredOfficeAddressPhysicalBox')]//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')]"
        )
        for count in range(len(historic_addresses)):
            physical_registered_office_address = dom.xpath(
                f"//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')][{count + 1}]/div/div/div/div[2]"
            )[0].text
            start_date = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')][{count + 1}]/div/div/div/div/div/div[2])[1]"
            )[0].text
            end_date = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')][{count + 1}]/div/div/div/div/div/div[2])[2]"
            )[0].text

            entry = {
                "physical_registered_office_address": physical_registered_office_address,
                "start_date": start_date,
                "end_date": end_date,
            }
            historic_physical_office_addresses[str(count)] = entry
        addresses["historic_office_addresses"] = historic_physical_office_addresses

        # Scrapes postal office addresses.
        postal_registered_office_address = dom.xpath(
            f"//div[contains (@class, 'appPostalAddress')]/div/div/div[2]"
        )[0].text
        start_date = dom.xpath(
            f"//div[contains (@class, 'appPostalAddress')]/div/div[2]/div/div/div[2]"
        )[0].text
        contact_email = dom.xpath(
            f"//div[contains (@class, 'EntityEmailAddresses')]/div[2]"
        )[0].text
        contact_telephone_number = dom.xpath(
            f"//div[contains (@class, 'appPhoneNumber')]/div[2]"
        )[0].text
        postal_office_address = {
            "postal_registered_office_address": postal_registered_office_address,
            "start_date": start_date,
            "contact_email": contact_email,
            "contact_telephone_number": contact_telephone_number,
        }
        addresses["postal_office_address"] = postal_office_address

        # Scrapes historic postal office addresses.
        historic_postal_addresses = dom.xpath(
            "//div[contains (@class, 'brViewLocalCompany-tabsBox-addressesTab-roaBox-roaAdditionalAddressesBox-registeredOfficeAddressPostalBox-registeredOfficeAddressPostal-withPostalIsPhysical-withoutUpload-editAddress-categorizerBox')]//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')]"
        )
        for count in range(len(historic_postal_addresses)):
            postal_registered_office_address = dom.xpath(
                f"//div[@class='appCategory Historic']//div[contains (@class, 'brViewLocalCompany-tabsBox-addressesTab-roaBox-roaAdditionalAddressesBox-registeredOfficeAddressPostalBox-registeredOfficeAddressPostal-withPostalIsPhysical-withoutUpload-editAddress-categorizerBox-postalAddresses')]/div[@class='appDialogRepeaterContent']/div[{count + 1}]/div/div/div[1]/div[2]"
            )[0].text
            start_date = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'brViewLocalCompany-tabsBox-addressesTab-roaBox-roaAdditionalAddressesBox-registeredOfficeAddressPostalBox-registeredOfficeAddressPostal-withPostalIsPhysical-withoutUpload-editAddress-categorizerBox-postalAddresses')]/div[@class='appDialogRepeaterContent']/div[{count + 1}]/div/div/div[2]/div/div/div[2])[1]"
            )[0].text
            end_date = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'brViewLocalCompany-tabsBox-addressesTab-roaBox-roaAdditionalAddressesBox-registeredOfficeAddressPostalBox-registeredOfficeAddressPostal-withPostalIsPhysical-withoutUpload-editAddress-categorizerBox-postalAddresses')]/div[@class='appDialogRepeaterContent']/div[{count + 1}]/div/div/div[2]/div/div/div[2])[1]"
            )[0].text

            entry = {
                "postal_registered_office_address": postal_registered_office_address,
                "start_date": start_date,
                "end_date": end_date,
            }
            historic_postal_office_addresses[str(count)] = entry
        addresses["historic_postal_office_addresses"] = historic_postal_office_addresses

        l.add_value("addresses", addresses)

    async def scrape_directors(self, dom, l):
        # Scrapes current directors.
        directors = {}
        current_directors = {}
        number_of_directors = dom.xpath(
            "//div[@class='appCategory Current']//div[contains (@class, 'appDialogRepeaterRowContent')]"
        )
        for count in range(len(number_of_directors)):
            name_khmer = dom.xpath(
                f"(//div[@class='appTabSelected']//div[contains (@class, 'individualNameKhmer')]/div[2])[{count + 1}]"
            )[0].text
            name_english = dom.xpath(
                f"(//div[@class='appTabSelected']//div[contains (@class, 'individualNameEnglish')]/div[2])[{count + 1}]"
            )[0].text
            postal_registered_office_address = dom.xpath(
                f"(//div[@class='appTabSelected']//div[contains (@class, 'postalAddressRoot')]/div[2])[{count + 1}]"
            )[0].text
            telephone = dom.xpath(
                f"(//div[@class='appTabSelected']//div[contains (@class, 'appPhoneNumber')]/div[2])[{count + 1}]"
            )[0].text
            chairman_of_the_board_of_directors = dom.xpath(
                f"(//div[@class='appTabSelected']//div[contains (@class, 'ChairmanYn')]/div[2])[{count + 1}]"
            )[0].text
            director = {
                "name_khmer": name_khmer,
                "name_english": name_english,
                "postal_registered_office_address": postal_registered_office_address,
                "telephone": telephone,
                "chairman_of_the_board_of_directors": chairman_of_the_board_of_directors,
            }
            current_directors[str(count)] = director
        directors["current_directors"] = current_directors

        # Scrapes former directors.
        former_directors = {}
        number_of_former_directors = dom.xpath(
            f"//div[@class='appCategory Historic']//div[contains (@class, 'appDialogRepeaterRowContent')]"
        )
        for count in range(len(number_of_former_directors)):
            name_khmer = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'individualNameKhmer')]/div[2])[{count + 1}]"
            )[0].text
            name_english = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'individualNameEnglish')]/div[2])[{count + 1}]"
            )[0].text
            postal_registered_office_address = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'postalAddressRoot')]/div[2])[{count + 1}]"
            )[0].text
            telephone = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'appPhoneNumber')]/div[2])[{count + 1}]"
            )[0].text
            chairman_of_the_board_of_directors = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'ChairmanYn')]/div[2])[{count + 1}]"
            )[0].text
            ceased = dom.xpath(
                f"(//div[@class='appCategory Historic']//div[contains (@class, 'Attribute-CeasedDate')]/div[2])[{count + 1}]"
            )[0].text
            director = {
                "name_khmer": name_khmer,
                "name_english": name_english,
                "postal_registered_office_address": postal_registered_office_address,
                "telephone": telephone,
                "chairman_of_the_board_of_directors": chairman_of_the_board_of_directors,
                "ceased": ceased,
            }
            former_directors[str(count)] = director
        directors["former_directors"] = former_directors
        l.add_value("directors", directors)

    async def errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
