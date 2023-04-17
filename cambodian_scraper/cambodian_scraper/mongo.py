# https://github.com/VigilantePolitico/vigilante/raw/9935c2821e4ad17e083bf22ea237d379ffbda8cb/vigilante/pipelines/mongo.py
import logging
import pymongo
from mongoengine import connect
from itemadapter import ItemAdapter

logger = logging.getLogger("mongo")


class MongoDBPipeline(object):
    collection_name = "cambodian_companies"

    def __init__(self):
        self.ids_seen = set()

    @classmethod
    def open_spider(self, spider):
        logger.info("Connecting to mongodb://localhost:27017")
        self.client = pymongo.MongoClient("mongodb://localhost:27017")
        self.db = self.client["companies"]
        logger.debug("Connected")

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.collection_name].update_one(
            {"company_id": item["company_id"]}, {"$set": ItemAdapter(item)}, upsert=True
        )
        return item
