import cherrypy
from jinja2 import Environment, FileSystemLoader

from utils import search_redis, load_data


class Home:
    @cherrypy.expose
    def index(self):
        env = Environment(loader=FileSystemLoader('templates'))
        homepage = env.get_template('index.html')
        date_time = load_data()
        if not date_time:
            raise cherrypy.HTTPError(status=500, message="I got myself in trouble!")
        return homepage.render(date=date_time)


class Apiv1:
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stocks(self, **kwargs):
        params = dict()
        for key, value in kwargs.items():
            params[key] = value

        start = int(params["start"])
        length = int(params["length"])
        search_query = params.get("search[value]", "")

        response = dict()
        response["draw"] = int(params["draw"])
        response["recordsFiltered"], stocks = search_redis(search_query, start, length)
        response["data"] = stocks

        return response

    @cherrypy.expose
    def reload(self):
        return load_data()
