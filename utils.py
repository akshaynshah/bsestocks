import csv
from datetime import datetime
import io
import zipfile

import cherrypy
import requests
from bs4 import BeautifulSoup
from redisearch import Client, TextField, NumericField, Query
from redis.exceptions import ResponseError


BHAVCOPY_URL = "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx"
EQUITY_ID = "ContentPlaceHolder1_btnhylZip"
client = Client('stocks')


try:
    client.create_index(
        [
            TextField("name"),
            NumericField("open"),
            NumericField("high"),
            NumericField("low"),
            NumericField("close")
        ]
    )
except ResponseError as e:
    if str(e) != "Index already exists":
        raise ResponseError(e)


def download_latest_zip():
    response = requests.get(BHAVCOPY_URL)
    if response.status_code == 200:
        text = response.text
        tomato = BeautifulSoup(text, 'html.parser')
        latest_equity_url = tomato.find(id=EQUITY_ID).attrs.get("href")
        if latest_equity_url:
            r = requests.get(latest_equity_url)
            if r.status_code == 200:
                zip_bytes = r.content
                return zip_bytes


def csv_from_zip(zip_bytes):
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    for file in z.namelist():
        if file.endswith(".CSV"):
            csv_bytes = io.StringIO(z.read(file).decode())
            return csv_bytes


def load_data():
    zip_content = download_latest_zip()
    if not zip_content:
        return
    csv_content = csv_from_zip(zip_content)
    reader = csv.DictReader(csv_content)
    try:
        for row in reader:
            add_to_redis(
                code=row["SC_CODE"],
                name=row["SC_NAME"],
                open=row["OPEN"],
                high=row["HIGH"],
                low=row["LOW"],
                close=row["CLOSE"]
            )
        now = datetime.now().strftime("%d %b %y at %I:%M:%S %p")
    except ConnectionError:
        raise cherrypy.HTTPError(status=500, message="I got myself in trouble!")
    return now


def _sanitize(string):
    alphanumeric_string = "".join(c for c in string if c.isalnum() or c.isspace())
    words = [word+"*" for word in alphanumeric_string.split()]
    query_string = " ".join(words)
    if len(query_string) < 3:
        query_string = "*"
    return query_string


def add_to_redis(**kwargs):
    scrip_code = kwargs.pop("code", "")
    if not scrip_code:
        return
    client.add_document(doc_id=scrip_code, replace=True, **kwargs)


def search_redis(query_string, offset=0, maximum=10):
    stocks, count = [], 0
    query = Query(_sanitize(query_string)).sort_by("name").limit_fields("name").paging(offset, maximum)
    result = client.search(query)
    for doc in result.docs:
        count += 1
        stock = dict(
            serial_number=offset+count,
            code=doc.id,
            name=doc.name,
            open=doc.open,
            high=doc.high,
            low=doc.low,
            close=doc.close
        )
        stocks.append(stock)
    return result.total, stocks
