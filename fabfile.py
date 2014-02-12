#!/usr/bin/python2.7

import sys
import cyconst as cc
from cyclone import Notifier
from cyclone import load_class



def err_exit(errormessage):
    sys.stderr.write("ERROR: %s\n" % errormessage)
    sys.exit(1)
    

def cyclone1(type, method, site_id, target, provider, params, extensions, notify_url, token):
    """the main function called from jenkins"""

    try:
        notifier = Notifier(notify_url, site_id, token);
    except Exception as e:
        # Notifier probably cant find url. Serious. Fail early.
        err_exit('no notifier')


    # Check method
    if not method in cc.METHOD_OUTCOMES:
        notifier.notify('failure', 'Bad method.')
        err_exit('Bad method.')

    # Get the possible outcomes
    outcomes = cc.METHOD_OUTCOMES[method];
    (ok_status, fail_status) = outcomes;

    # Instantiate, call mathod, notify
    try:
        builderclass = load_class(type)
        builder = builderclass(provider) 
        # builder = AegirBuilder(provider)
        b_method = getattr(builder, method)
        data = b_method(site_id, target, params, extensions)
        notifier.notify(ok_status, "success", data);
        sys.exit(0)
    except Exception as e:
        notifier.notify(fail_status, 'task failed: %s' % str(e));
        err_exit(str(e))


