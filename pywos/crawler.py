"""
crawler for wos data using aiohttp
"""

import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
import json
from pywos.cons import wosException
from pywos.cons import logger
from pywos.cons import urls, http_error


def construct_search(**query):
    '''
    simplified utility to construct query dict for the wos query post

    :param query: form AI="A-1234-5678", PY="2016-2018", etc.
    :return: the query dict as the input of WosQuery
    '''
    search_dict = {}
    i = 0
    for key, value in query.items():
        i += 1
        vi = "value(input" + str(i) + ")"
        vs = "value(select" + str(i) + ")"
        search_dict[vi] = value
        search_dict[vs] = key

    l = len(query)
    for i in range(l):
        for j in range(i + 1, l):
            vb = "value(bool_" + str(i + 1) + "_" + str(j + 1) + ")"
            search_dict[vb] = 'AND'
    search_dict['fieldCount'] = l
    return search_dict


class WosQuery:
    '''
    class for crawling papers on certain quey, the data is automatically export to file at the end

    :param querydict: dict to construct the form data of the query on web of science
    :param headers: dict of headers to add on the get or post
    '''

    def __init__(self, querydict, headers=None):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
        }
        if headers is not None:
            self.headers.update(headers)
        self.searchdict = {
            "fieldCount": 1,
            "action": "search",
            "product": "UA",
            "search_mode": "GeneralSearch",
            "max_field_count": 25,
            "formUpdated": "true",
            "value(input1)": "",
            "value(select1)": "",
        }
        self.searchdict.update(querydict)

    async def query(self):
        '''
        find the urlprefix for each paper satisifying the query, as well as the total number
        of papers, the two value are assigned with self.urlprefix and self.num_items
        '''
        logger.info("trying to get sid and open new session, it may takes several seconds...")
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(urls['indexurl']) as response:
                r = response

            self.sid = re.match(r'.*&SID=([a-zA-Z0-9]+)&.*', str(r.url)).group(1)
            self.searchdict["SID"] = self.sid
            logger.info("The data form of the post is composed as below")
            logger.info(self.searchdict)
            async with session.post(urls['posturl'],
                                    data=self.searchdict) as response:
                self.html = await response.text()

            so = BeautifulSoup(self.html, "lxml")
            if not so('value'):
                raise wosException('not correct page returned')
            contenturl = so("a", class_="smallV110 snowplow-full-record")[0].get("href")
            self.qid = re.match(r".*&qid=([0-9]+)&.*", contenturl).group(1)
            num_items = so.find("span", {"id": "footer_formatted_count"}).string
            self.num_items = int(re.subn(",", "", num_items)[0])
            logger.info('there are %s papers to be collected in total' % self.num_items)
            self.urlprefix = urls['recordurl'] + self.qid + "&SID=" + self.sid + "&doc="

    async def collect_papers(self, citedcheck=False, savebyeach=False, savepathprefix=None, limit=20,
                             masklist=None):
        '''
        collect metadata of all papers satisfying the query, all data are assigned with self.papers

        :param citedcheck: bool, if set to true, then all citation papers of given paper are also collected
        :param limit: int, the size of tcp connection pool, if set to be too large, there is high risk of
                    banning from the server
        :param savebyeach: bool, if set to true, metadata of each paper is saved immediately in files
        :param savepathprefix: string, the path prefix for data files of each paper
        :param masklist: list of int, if provided, for all numbers on the list, the corresponding task is canceled
        '''
        if not self.urlprefix:
            raise wosException('run query first')
        self.papers = []
        conn = aiohttp.TCPConnector(limit_per_host=limit)
        async with aiohttp.ClientSession(headers=self.headers, connector=conn) as session:
            if masklist is None:
                masklist = []
            self.papers = await asyncio.gather(
                *[self.parse_paper(session, self.urlprefix, count + 1, citedcheck=citedcheck,
                                   savebyeach=savebyeach, savepath=savepathprefix + "-" + str(count + 1) + ".json")
                  for count in range(self.num_items) if count + 1 not in masklist])

    async def parse_paper(self, session, prefix, count, citedcheck=False,
                          ocount=0, savebyeach=False, savepath=None):
        '''
        paser individual paper pages

        :param session: aiohttp.ClientSession from the caller
        :param prefix: string, the url prefix before finally doc=?
        :param count: int, the number of papers in the tasks
        :param citedcheck: bool, whether continually checking the citation papers of given paper
        :param ocount: int, 0 if it is the paper under query, and other int if it is the citation
                    paper of ocount paper under query
        :param savebyeach: bool, if set to true, metadata of the paper is saved immediately
        :param savepath: string, the full file path for the saved json
        :return: the parse_dict dictionary containing all metadata of the paper
        '''
        html2 = ""
        for tries in range(3):
            try:
                async with session.get(prefix + str(count)) as r:
                    html2 = await r.text()
                    break
            except http_error as e:
                if tries < 2:
                    pass
                else:
                    logger.warning("tried connection 3 times, all failed")
                    raise e

        if ocount == 0:
            logger.info("download paper %s in query" % count)
        else:
            logger.info("download cited paper no %s of %s paper" % (count, ocount))
        so2 = BeautifulSoup(html2, "lxml")
        parse_dict = parse_record(so2)

        if parse_dict.get('cited_link', None) and citedcheck:
            logger.info("try fetch cited paper of %s" % count)
            html3 = ""
            for tries in range(3):
                try:
                    async with session.get(parse_dict['cited_link']) as r:
                        html3 = await r.text()
                        break
                except http_error as e:
                    if tries < 2:
                        pass
                    else:
                        logger.warning("tried connection 3 times, all failed")
                        raise e

            so3 = BeautifulSoup(html3, 'lxml')
            contenturl = so3("a", class_="smallV110 snowplow-full-record")[0].get("href")
            qid = re.match(r".*&qid=([0-9]+)&.*", contenturl).group(1)
            num_cited_items = so3.find("span", {"id": "footer_formatted_count"}).string
            num_cited_items = int(re.subn(",", "", num_cited_items)[0])
            urlprefix = urls['citationrecordurl'] + qid + "&SID=" + self.sid + "&doc="

            parse_dict['cited_papers'] = await asyncio.gather(
                *[self.parse_paper(session, urlprefix, ccount + 1, citedcheck=False, ocount=count) for ccount in
                  range(num_cited_items)])

        if savebyeach and isinstance(savepath, str):
            with open(savepath, "w") as output:
                json.dump(parse_dict, output)
            logger.info("save the data of paper %s on %s" % (count, savepath))

        return parse_dict

    async def main(self, path, citedcheck=False, savebyeach=False, limit=20, masklist=None):
        '''
        the main function for crawling, from query to metadata in file

        :param path: string, the file path to save all data, and the path prefix to save data of
                    each paper if savebyeach is set to be true
        :param citedcheck: bool, if set to true, all citation papers are also tracked
        :param limit: int, the size of tcp connection pool, if set to be too large, there is high risk of
                    banning from the server
        :param savebyeach: bool, if set to true, metadata of each paper is saved immediately in files
        :param masklist: list of int, if provided, for all numbers on the list, the corresponding task is canceled
        '''
        await self.query()
        await self.collect_papers(citedcheck=citedcheck, limit=limit, savebyeach=savebyeach,
                                  savepathprefix=path, masklist=masklist)
        logger.info("all download tasks are finished")
        with open(path, "w") as output:
            json.dump(self.papers, output)
        logger.info("total data are written into json file: %s" % path)


def parse_record(so2):
    if not so2('value'):
        logger.warning("error in the crawled page!")
        return None
    parse_dict = {}
    journal = so2("p", class_='sourceTitle')
    if journal:
        parse_dict['journal'] = journal[0].text.strip("\n")
    else:
        parse_dict['journal'] = ""
    title = so2("div", class_='title')
    if title:
        parse_dict['title'] = title[0].text.strip("\n")
    else:
        parse_dict['title'] = ""
    pages = so2.find(lambda tag: tag.name == "span" and "Pages" in tag.text)  # .next_sibling
    if not pages:
        pages = so2.find(lambda tag: tag.name == "span" and "Article Number" in tag.text)
    try:
        pages = pages.next_sibling
        if pages != '\n':
            parse_dict['number'] = pages.strip()
        else:
            parse_dict['number'] = pages.next_sibling.string.strip()
    except AttributeError:
        if len(so2('value')) > 5:
            parse_dict['number'] = so2('value')[4].string
        else:
            parse_dict['number'] = ""

    try:
        volume = so2.find(lambda tag: tag.name == "span" and "Volume" in tag.text).next_sibling
        if volume != '\n':
            parse_dict['volume'] = volume.strip()
        else:
            parse_dict['volume'] = volume.next_sibling.string.strip()
    except AttributeError:
        if len(so2('value')) > 3:
            parse_dict['volume'] = so2('value')[2].string
        else:
            parse_dict['volume'] = ""

    try:
        issue = so2.find(lambda tag: tag.name == "span" and "Issue" in tag.text)
        if issue:
            issue = issue.next_sibling
            if issue != '\n':
                parse_dict['issue'] = issue.strip()
            else:
                parse_dict['issue'] = issue.next_sibling.string.strip()
        else:
            parse_dict['issue'] = ""
    except AttributeError:
        if len(so2('value')) > 4:
            parse_dict['issue'] = so2('value')[3].string
        else:
            parse_dict['issue'] = ""

    try:
        date = so2.find(lambda tag: tag.name == "span" and "Date" in tag.text)  # .next_sibling
        if not date:
            date = so2.find(lambda tag: tag.name == "span" and "Published" in tag.text)
        date = date.next_sibling
        if date != '\n':
            parse_dict['date'] = date.strip()
        else:
            parse_dict['date'] = date.next_sibling.string.strip()
    except AttributeError:
        if len(so2('value')) > 7:
            parse_dict['date'] = so2('value')[6].string
        else:
            parse_dict['date'] = ""

    try:
        doi = so2.find(lambda tag: tag.name == "span" and "DOI" in tag.text).next_sibling
        if doi != '\n':
            parse_dict['doi'] = doi.strip()
        else:
            parse_dict['doi'] = doi.next_sibling.string.strip()
    except AttributeError:
        if len(so2('value')) > 6:
            parse_dict['doi'] = so2('value')[5].string
        else:
            parse_dict['doi'] = ""

    parse_dict['email'] = [a.text for a in so2('a', class_='snowplow-author-email-addresses')]
    parse_dict['fund'] = [(f('td')[0].string.strip(), [fd.string.strip() for fd in f('div')]) for f in
                          so2('tr', class_='fr_data_row')]
    parse_dict['keyword'] = [a.text for a in so2("a", class_="snowplow-kewords-plus-link")]
    authorinfo = so2('a', title="Find more records by this author")
    parse_dict['author'] = []
    for ai in authorinfo:
        auname = ai.next_sibling.strip().strip(",").strip(";").strip('(').strip(')')
        auinst = []
        if ai.next_sibling.next_sibling:
            for inst in ai.next_sibling.next_sibling('b')[1:]:
                if inst:
                    try:
                        auinst.append(int(inst.string))
                    except TypeError:
                        pass
        parse_dict['author'].append((auname, auinst))

    parse_dict['abstract'] = so2('div', class_='title3')[0].next_sibling.next_sibling.text
    parse_dict['cited_num'], parse_dict['referenced_num'] = [int(re.subn(",", "", n.text.strip())[0]) for n in
                                                             so2('span', class_='large-number')[0:2]]
    referenced = so2('a', class_='snowplow-citation-network-cited-reference-count-link')
    if referenced:
        parse_dict['referenced_link'] = "https://apps.webofknowledge.com/" + referenced[0].get("href")
    cited = so2('a', class_='snowplow-citation-network-times-cited-count-link')
    if cited:
        parse_dict['cited_link'] = "https://apps.webofknowledge.com/" + cited[0].get("href")
    inst = []
    instshort = []
    addlist = so2('td', class_='fr_address_row2')
    for address in addlist:
        if address('a'):
            l = address.text.split('\n')
            ldeno = re.sub(r"^\[ [0-9]+ \] ", "", l[0].strip())
            inst.append(ldeno)
            if len(l) == 3:
                instshort.append(l[-1].strip())
            elif len(l) == 4:
                instshort.append(l[-2].strip())
            else:
                instshort.append("")
    parse_dict['inst'] = inst
    parse_dict['instshort'] = instshort
    js = so2("div", class_='flex-row-partition2')
    parse_dict['hotpapers'] = False
    parse_dict['highlycited'] = False
    if js:
        js = js[0].contents[1]
        hc = re.search(r"'highlyCited': true", js.string[-100:])
        hp = re.search(r"'hotPaper': true", js.string[-100:])
        if hc:
            parse_dict['highlycited'] = True
        if hp:
            parse_dict['hotpapers'] = True

    parse_dict['cited_papers'] = []
    return parse_dict


'''
task = WosQuery(querydict={"value(input1)": "D-3202-2011", "fieldCount": 2,
                           "value(bool_1_2)": "AND", "value(input2)": "2018-2018",
                           "value(select2)": "PY"})

loop = asyncio.get_event_loop()

t = asyncio.ensure_future(task.main(path="data.json", citedcheck=True))

try:
    loop.run_until_complete(t)
except KeyboardInterrupt as e:
    asyncio.Task.all_tasks()
    asyncio.gather(*asyncio.Task.all_tasks()).cancel()
    loop.stop()
    loop.run_forever()
finally:
    loop.close()
'''
