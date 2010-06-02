#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import web
from juicer.controllers.base import JSONController


class Index(JSONController):
    
    def GET(self):
        return self.output(True)
    
    def HEAD(self):
        return self.output(True)
    
    def POST(self):
        input = self.input()
        return self.output(True)
    
    def PUT(self):
        return self.output(True)
    
    def DELETE(self):
        return self.output(True)
    
    def TRACE(self):
        return self.output(True)
    
    def OPTIONS(self):
        return self.output(True)
    
    def CONNECT(self):
        return self.output(True)
    
# web.py application ----------------------------------------------------------

URLS = (
    '/.*', 'Index',
)

application = web.application(URLS, globals())