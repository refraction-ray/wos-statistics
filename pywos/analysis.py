"""
analysis the data with the special focus on the citation evaluation
"""
import pandas as pd
import json
from pywos.cons import logger

class Papers:
    def __init__(self, path):
        self.papers = []
        if isinstance(path, str):
            with open(path, "r") as file:
                self.papers = json.load(file)
        elif isinstance(path, list) or isinstance(path, tuple):
            for eachpath in path:
                with open(eachpath,"r") as file:
                    self.papers.append( json.load(file) )

    def export(self, path):
        with open(path, "w") as file:
            json.dump(file, self.papers)

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
            show_dict['mailautor'] = p.get('mailauthor', "unknown")
            if citedcheck:
                show_dict['citation_by_others'] = p.get('cited_count_total', (0,0))[1]
                show_dict['citation_by_self'] =  p.get('cited_count_total', (0,0))[0]
                show_dict['recent_citation_by_others'] = p.get('cited_count_recent',(0,0))[1]
                show_dict['recent_citation_by_self'] = p.get('cited_count_recent',(0,0))[0]
            else:
                show_dict['total_citation'] = p['cited_num']
            show_list.append(show_dict)
        df = pd.DataFrame(show_list)
        return df
