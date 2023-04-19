# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import TakeFirst


class CambodianCompanyItem(scrapy.Item):
    company_id = scrapy.Field(output_processor=TakeFirst())
    company_name_in_khmer = scrapy.Field(output_processor=TakeFirst())
    company_name_in_english = scrapy.Field(output_processor=TakeFirst())
    original_entity_identifier = scrapy.Field(output_processor=TakeFirst())
    company_status = scrapy.Field(output_processor=TakeFirst())
    incorporation_date = scrapy.Field(output_processor=TakeFirst())
    re_registration_date = scrapy.Field(output_processor=TakeFirst())
    tax_identification_number_tin = scrapy.Field(output_processor=TakeFirst())
    tax_registration_date = scrapy.Field(output_processor=TakeFirst())
    annual_return_last_filed_on = scrapy.Field(output_processor=TakeFirst())
    previous_names = scrapy.Field(output_processor=TakeFirst())

    business_activities = scrapy.Field(output_processor=TakeFirst())

    number_of_employees = scrapy.Field(output_processor=TakeFirst())

    addresses = scrapy.Field(output_processor=TakeFirst())

    directors = scrapy.Field(output_processor=TakeFirst())
