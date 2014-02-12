#!/usr/bin/python2.7

import hashlib
import urllib, urllib2
import os
import re
import json

import sys
import importlib

from fabric.api import *

def load_class(full_class_string):
    """ 
    dynamically load a class from a string
    """

    # to be able to load our modules, the current dir needs to be on path:
    if not '.' in sys.path:
        sys.path.append('.')

    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]
    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, class_str) 

def debug_run(cmd):
    """call the fabric run command, but print a timestamp before"""
    run("date '+%Y/%m/%d %H:%M:%S'")
    run(cmd)


class Notifier(object):
        
    def __init__(self, notify_url, site_id, token):
        self.site_id = site_id
        self.notify_url = notify_url
        self.token = token
        # @todo: cant_do_a_get_on($notify_url)
        #        raise Exception("Cannot access notify URL")

    def notify(self, status, title, data = None):
        """Sends a message with given status"""
        print("NOTIFY: %s\n" % title)
        jdata = ''
        if data:
            jdata = json.dumps(data)
        build_title = os.environ['BUILD_NUMBER']
        build_url = os.getenv('BUILD_URL', 'not-available')
        # We saw a situation when Jenkins did not export this envoronmet variable.
        # Using a default value to be safe.

        m = hashlib.md5()
        secretstring = "build_title:%s;build_url:%s;data:%s;site_id:%s;title:%s;type:%s;%s" \
                % (build_title, build_url, jdata, self.site_id, title, status, self.token)
        m.update(secretstring)
        signature = m.hexdigest()
        values = dict(build_title=build_title, build_url=build_url, data=jdata,
                site_id=self.site_id, title=title, type=status, signature=signature, 
                form_id='cyclone_notify_form')
        formdata = urllib.urlencode(values)
        req = urllib2.Request(self.notify_url, formdata)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
        except urllib2.URLError as e:
            print 'We failed to reach a server: %s' % self.notify_url
            print 'Reason: ', e.reason
        else:
            # everything is fine
            content = response.read()


class Builder(object):
    def __init__(self, provider):
        self.provider = provider
        if not provider:
            raise Exception("Provider is empty.")

    @staticmethod
    def load_sanitise_params(params):
        '''load the json with params, sanitise them, return them back as a dict()'''
        p = json.loads(params)

        # check all the required variables are present:
        if ('name' not in p) or ('email' not in p) or ('source' not in p): 
            raise Exception('params missing required variable')

        # insert all optional variables as empty strings, so we don't have the check their existence later:                                                           
        if 'aliases' not in p:  
            p['aliases'] = ''
        if 'user_name' not in p:
            p['user_name'] = ''
        if 'user_email' not in p:
            p['user_email'] = ''
        if 'user_role' not in p:
            p['user_role'] = ''


        # sanity checks
        if (p['user_name'] and not p['user_email']) or (p['user_email'] and not p['user_name']):
             raise Exception( "params: if user_name or user_email is defined, the other one needs to be defined as well.");

        return p

    @staticmethod
    def post_create_tasks(drush_alias, p):
        """Post create tasks common for each builder.
        It sets site_mail, site_name, generates uli.
        The caller of this function is expected to catch a possible exception.

        """
        data = dict()

        debug_run("drush @%s vset site_mail %s" % (drush_alias, p['email']))
        debug_run("drush @%s vset site_name '%s'" % (drush_alias, p['name']))
        # if user_name is defined, create that user and return the one time url for him/her
        if p['user_name']:
            debug_run("drush @%s user-create %s --mail=%s" % (drush_alias, p['user_name'], p['user_email']))
            login_url = run("drush @%s uli %s" % (drush_alias, p['user_name']), pty=True, combine_stderr=True)
        # otherwise return one time url for admin:
        else:
            login_url = run("drush @%s uli" % drush_alias, pty=True, combine_stderr=True)
        data['login_url'] = login_url

        return data


    @staticmethod
    def extend(extensions, drush_alias):
        """call all extensions, one by one"""
        if extensions:
            print("extensions: %s" % extensions)
            jsdict = json.loads(extensions)
            for ext_class in jsdict:
                ext_params = jsdict[ext_class]
                print('ext_class: %s\next_params: %s' % (ext_class, ext_params))
                extclass = load_class(ext_class)                                         
                ext = extclass(drush_alias) 
                ext.extend(ext_params)



class Extension(object):
    def __init__(self, drush_alias):
        self.drush_alias = drush_alias
        if not drush_alias:
            raise Exception("drush_alias is empty.")

