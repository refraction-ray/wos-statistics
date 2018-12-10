# wos-statistics

Python library for collecting data from web of science and exporting summary in terms of all kinds of requirements on the citation statistics. The crawling part is implemented with aiohttp for a better speed.

## Installation

Python 3.6+ is supported.

## Quick Start

```python
from pywos.crawler import WosQuery, construct_search
from pywos.analysis import Papers
import asyncio

# get data
qd = construct_search(AI="D-3202-2011", PY="2014-2018") # construct the query for papers
wq = WosQuery(querydict=qd) # create the crawler object based on the query
loop = asyncio.get_event_loop()
task = asyncio.ensure_future(wq.main(path="data.json")) # use main function of the object to download paper metadata and save them in the path
loop.run_until_complete(task) # here we go

# analyse data
p = Papers("data.json") # fetch data from the path just now
p.show(['Last, First', 'Last, F.'],['flast@abcu.edu.cn'], ['2017','2018']) # generate the summary on citations in the form of pandas dataframe
```

## Usage

### query part

First, it based on a legitimate query on web of science to download metadata of papers. You should provide a query dict for the crawl class. `value(select[n])` corresponds the nth query conditions, eg. `AU` for author's name, `AI` for identifier of authors, `PY` for publication year range, etc. `value(input[n])` corresponds the nth query values, eg. the name of the author or the year range 2012-2018. If there are multiple conditions, `value(bool_[m]_[n])` should also be added, the values include `AND`, `OR`,`NOT` indicating how to combine different search conditions. Besides, `fieldCount` should be updated to the number of query conditions. A legitimate query looks like `{'fieldCount': 2, 'value(input1)': 'D-1234-5678', 'value(select1)': 'AI', 'value(input2)': '2014-2018', 'value(select2)': 'PY', 'value(bool_1_2)': 'AND'}`. There is a quick function provided to construct such query dictionary easily for AND-connecting queries.

```python
from pywos.crawler import construct_search
construct_search(AI="D-1234-5678", PY="2018-2018")
# return value below
{'fieldCount': 2,
 'value(bool_1_2)': 'AND',
 'value(input1)': 'D-1234-5678',
 'value(input2)': '2018-2018',
 'value(select1)': 'AI',
 'value(select2)': 'PY'}
```

### download part

Firstly, we should initialize the crawling object by providing the query dict and dict of headers for all http connections (optional, there is a default user-agent for headers).

```python
from pywos.crawler import WosQuery
wq = WosQuery(querydict = {'value(input1)': '',...}, headers= {'User-Agent':'blah-blah'})
```

The data collecting task is called by `WosQuery.main(path=)`. Parameters are all optional except `path`, which is the pathname to save output data. `citedcheck` is a bool, if set to be true, all citation papers of the query paper are also collected. And this is the basis for detailed analysis on citations, like citations by years and citations by others. Otherwise, the default value for `citedcheck` is false, in this case only total citation number of each query paper can be obtained. `limit` option gives the max number of connections in the http connection pool. The default number is 20. A larger number implies faster speed but also implies higher risk of connection failure due to the restriction by web of science. `limit=30` is tested successfully without connection failure, and such speed is enough to handle 1000 papers in around 1 minute. If the query task is too large, the better practice is turning on the parameter `savebyeach=True`, such that every paper within the query will be saved immediately after downloading. Therefore, when meeting connection failure, we can recover the task without fetching all data again. This is determined by the `masklist` paramter of main function. If `masklist` is provided, for all int number in this list, the corresponding paper is omitted to avoid repeating work. In sum, for a large task, we have the following parameters.

```python
import asyncio
task = asyncio.ensure_future(wq.main(path="prefix", citedcheck=True, savebyeach=True, limit=30))
```

To actually run the task is a thing on asyncio, see below.

```python
loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(task)
    
except KeyboardInterrupt as e:
    asyncio.Task.all_tasks()
    asyncio.gather(*asyncio.Task.all_tasks()).cancel()
    loop.stop()
    loop.run_forever()

finally:
    loop.close()
```

If one would like to see the progress of the downloading, switch on the logging module.

```python
import logging
logger = logging.getLogger('pywos')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)
```

### analysis part

The `Papers()` class is designed for analysis on metadata of the papers. To initialize the object, provide a path of the metadata we saved using `WosQuery.main(path)`. One can also provide a list of pathes, such that all data of these jsons are imported. Besides, one can turn on `merge=True`, such that all files with the prefix `path-` will automatically imported, this is specifically suitable for data files saved using `WosQuery.main(path, savebyeach=True)`.

Generate the table of citation analysis by running `Papers.show(namelist, maillist, years)`. These lists are used for checking whether one is the first/correspondence author of the paper and count citations within `years` as recent citations, respectively. One can turn on `citedcheck=True` if the data to be analysed is obtained from `WosQuery.main(citedcheck=True)`. This includes further classification on citations in terms of years (recent citation) and authors (citation by others/self). The return object of `Papers.show()` is `pandas.DataFrame`, which can be easily transformed into other formats, including csv, html, tables in database and so on.

In sum, 

```python
from pywos.analysis import Papers
p = Papers("path-prefix", merge=True)
p.show(["Last, First"], ["mail@server"], ["2018"], citedcheck=True)
```

