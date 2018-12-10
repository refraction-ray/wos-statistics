"""
some consts
"""
import aiohttp
import asyncio
import logging
logger = logging.getLogger('pywos')


class wosException(Exception):
    def __init__(self, message):
        self.args = (message,)

urls = {
    "indexurl": "https://www.webofknowledge.com",
    "posturl": "https://apps.webofknowledge.com/UA_GeneralSearch.do",
    "recordurl": "https://apps.webofknowledge.com/full_record.do?product=UA&search_mode=GeneralSearch&qid=",
    "citationrecordurl": "https://apps.webofknowledge.com/full_record.do?product=WOS&search_mode=CitingArticles&qid="
        }

http_error = (aiohttp.ClientOSError, asyncio.TimeoutError, aiohttp.client_exceptions.ServerDisconnectedError,
                 aiohttp.client_exceptions.ClientConnectorError)