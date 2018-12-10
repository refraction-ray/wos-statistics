"""
analysis the data with the special focus on the citation evaluation
"""
import pandas as pd
import json
import re
from os import listdir, remove
from os.path import isfile, join
from pywos.cons import logger


class Papers:
    '''
    class to load data from file and analyzing citation statistics

    :param path: string or list of string, file path to load
    :param merge: bool, if set true, all path should be taken as the prefix before -,
                and all files with name starting with path-(num) would be loaded
    '''
    def __init__(self, path, merge=False):
        self.papers = []
        self.loadfile = []
        self.path = path
        if merge is False:
            if isinstance(path, str):
                with open(path, "r") as file:
                    self.papers = json.load(file)
                logger.info("load data from %s" % path)
                self.loadfile.append(path)
            elif isinstance(path, list) or isinstance(path, tuple):
                for eachpath in path:
                    with open(eachpath, "r") as file:
                        self.papers.append(json.load(file))
                    logger.info("load data from %s" % eachpath)
                    self.loadfile.append(eachpath)

        else:
            if isinstance(path, str):
                self.load_from_prefix(path)
            elif isinstance(path, list) or isinstance(path, tuple):
                for eachpath in path:
                    self.load_from_prefix(eachpath)

    def load_from_prefix(self, path):
        try:
            a = re.match(r"(^.*/)([^/]*$)", path)
            dirpath = a.group(1)
            namepath = a.group(2)
        except AttributeError:
            dirpath = "./"
            namepath = path
        self.namepath = namepath
        files = [f for f in listdir(dirpath) if isfile(join(dirpath, f))]
        patten = re.compile(namepath + r"-" + r".*")
        for file in files:
            if patten.match(file):
                with open(file, "r") as f:
                    self.papers.append(json.load(f))
                logger.info("load data from %s" % file)
                self.loadfile.append(join(dirpath, file))

    def export(self, path, clear=False):
        '''
        export dict data into one json file

        :param path: string, path of output json file
        :param clear: bool, default false, the true option is dangerous unless you know what you are doing!
                    if set to true, all files loaded for this object would be deleted!
        '''
        with open(path, "w") as file:
            json.dump(file, self.papers)
        logger.info("save all data in one file %s" % path)
        logger.warning("the input files would be deleted now!")
        for f in self.loadfile:
            remove(f)

    def generate_masklist(self, suffix):
        if isinstance(self.path, str):
            masklist = []
            patten = re.compile("^.*/"+self.namepath+"-"+"([0-9]*)"+suffix)
            for f in self.loadfile:
                masklist.append(int(patten.match(f).group(1)))
            return masklist


    def mailauthor(self, maillist):
        for i, p in enumerate(self.papers):
            papermail = p.get('email', None)
            if papermail:
                for mailadd in maillist:
                    if mailadd in papermail:
                        self.papers[i]['mailauthor'] = True
                        break
                else:
                    self.papers[i]['mailauthor'] = False

    def firstauthor(self, namelist):
        for i, p in enumerate(self.papers):
            authors = p.get('author', None)
            if authors:
                if authors[0][0] in namelist:
                    self.papers[i]['firstauthor'] = True
                else:
                    self.papers[i]['firstauthor'] = False

    def count_citation(self, namelist):
        for i, p in enumerate(self.papers):
            sc = 0
            oc = 0
            ex = 0  # exceptions
            scbyyear = {}
            ocbyyear = {}
            if p.get('cited_papers', None):
                for cp in p['cited_papers']:
                    if cp.get('author', None):
                        au = [a[0] for a in cp['author']]
                        for name in namelist:
                            if name in au:
                                sc += 1
                                if cp.get('date', None):
                                    year = cp['date'][-4:]
                                    scbyyear.setdefault(year, 0)
                                    scbyyear[year] += 1
                                else:
                                    scbyyear.setdefault('unknown', 0)
                                    scbyyear['unknown'] += 1
                                break
                        else:
                            oc += 1
                            if cp.get('date', None):
                                year = cp['date'][-4:]
                                ocbyyear.setdefault(year, 0)
                                ocbyyear[year] += 1
                            else:
                                ocbyyear.setdefault('unknown', 0)
                                ocbyyear['unknown'] += 1
                    else:
                        ex += 1
                self.papers[i]['cited_count_total'] = (sc, oc, ex)
                self.papers[i]['scited_byyear'] = scbyyear
                self.papers[i]['ocited_byyear'] = ocbyyear

    def count_recent_citation(self, years):
        for i, p in enumerate(self.papers):
            scr = 0
            ocr = 0
            if p.get('scited_byyear'):
                for y in years:
                    scr += p['scited_byyear'].get(y, 0)
            else:
                scr = 0
            if p.get('ocited_byyear'):
                for y in years:
                    ocr += p['ocited_byyear'].get(y, 0)
            else:
                ocr = 0
            self.papers[i]['cited_count_recent'] = (scr, ocr)

    def show(self, namelist, maillist, years=None, citedcheck=False):
        '''
        show the data on citations as a pandas dataframe, which is easy to be saved as other formats like csv

        :param namelist: list of strings, for the name of the author, be consitent with the form in metadata!
                    eg. ["last, first", "last, f."]
        :param maillist: list of strings, the email address of the author
        :param years: list of strings, the years considered as recent, eg. ['2016','2017','2018']
        :param citedcheck: bool, if true, check details of citations by year and by author,
                        need citedcheck be true in crawling process
        :return: pandas.DataFrame
        '''
        self.mailauthor(maillist)
        self.firstauthor(namelist)
        if citedcheck:
            logger.info("Run extra routine to classify the citations in detail")
            self.count_citation(namelist)
            self.count_recent_citation(years)
        show_list = []
        for p in self.papers:
            show_dict = {}
            show_dict['title'] = p['title']
            show_dict['journal'] = p['journal']
            show_dict['date'] = p['date'][-4:]
            show_dict['volume'] = p['volume']
            show_dict['number'] = p['number']
            show_dict['highlycited'] = p['highlycited']
            show_dict['hotpapers'] = p['hotpapers']
            show_dict['firstauthor'] = p.get('firstauthor', "unknown")
            show_dict['mailauthor'] = p.get('mailauthor', "unknown")
            if citedcheck:
                show_dict['citation_by_others'] = p.get('cited_count_total', (0, 0))[1]
                show_dict['citation_by_self'] = p.get('cited_count_total', (0, 0))[0]
                show_dict['recent_citation_by_others'] = p.get('cited_count_recent', (0, 0))[1]
                show_dict['recent_citation_by_self'] = p.get('cited_count_recent', (0, 0))[0]

            show_dict['total_citation'] = p['cited_num']
            show_list.append(show_dict)
        ## total line
        show_dict = {}
        show_dict['title'] = None
        show_dict['journal'] = None
        show_dict['date'] = 'Total'
        show_dict['volume'] = None
        show_dict['number'] = None
        show_dict['highlycited'] = sum([p['highlycited'] for p in show_list])
        show_dict['hotpapers'] = sum([p['hotpapers'] for p in show_list])
        show_dict['firstauthor'] = sum(p['firstauthor'] for p in show_list if isinstance(p['firstauthor'], bool))
        show_dict['mailauthor'] = sum(p['mailauthor'] for p in show_list if isinstance(p['mailauthor'], bool))
        if citedcheck:
            show_dict['citation_by_others'] = sum([p['citation_by_others'] for p in show_list])
            show_dict['citation_by_self'] = sum([p['citation_by_self'] for p in show_list])
            show_dict['recent_citation_by_others'] = sum([p['recent_citation_by_others'] for p in show_list])
            show_dict['recent_citation_by_self'] = sum([p['recent_citation_by_self'] for p in show_list])

        show_dict['total_citation'] = sum([p['total_citation'] for p in show_list])
        show_list.append(show_dict)
        if citedcheck:
            df = pd.DataFrame(show_list, columns=['date', 'journal', 'volume', 'number', 'firstauthor',
                                                  'mailauthor', 'total_citation', 'highlycited', 'hotpapers',
                                                  'recent_citation_by_others', 'recent_citation_by_self',
                                                  'citation_by_others', 'citation_by_self', 'title'])
        else:
            df = pd.DataFrame(show_list, columns=['date', 'journal', 'volume', 'number', 'firstauthor',
                                                  'mailauthor', 'total_citation', 'highlycited', 'hotpapers',
                                                  'title'])
        df.sort_values(['date'])
        return df
