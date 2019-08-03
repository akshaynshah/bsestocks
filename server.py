import logging

import cherrypy

from processing import Home, Apiv1

logging.basicConfig(level=logging.INFO, filename="/var/log/bsestocks/app.log")

cherrypy.config.update("server.conf")

cherrypy.tree.mount(Home(), "/")
cherrypy.tree.mount(Apiv1(), "/apiv1")

cherrypy.engine.start()
cherrypy.engine.block()
