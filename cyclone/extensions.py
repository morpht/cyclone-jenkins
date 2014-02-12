#!/usr/bin/python2.7

from fabric.api import *
import json
from cyclone import Extension

class Variables(Extension):

    def extend(self, ext_params):
        for evar in ext_params:
            evalue = ext_params[evar]
            print("extend: var: %s\nextend: val: %s\n" % (evar, evalue))

            try:
                run("date '+%Y/%m/%d %H:%M:%S'")
                run("drush @%s vset %s \"%s\"" % (self.drush_alias, evar, evalue))
            except SystemExit as e:
                raise Exception("vset FAILED. Err: %s" % str(e))
