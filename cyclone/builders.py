#!/usr/bin/python2.7

from fabric.api import *
import json
import re
from cyclone import Builder
from cyclone import debug_run
import time


class Aegir(Builder):
    def __init__(self, provider):
        pvd = json.loads(provider)
        if 'host_string' not in pvd:
            raise Exception("Aegir builder needs host_string parameter in the provider (e.g. aegir@example.com).")
        
        env.shell = '/bin/bash -c'
        env.host_string = pvd['host_string']

    def site_create(self, site_id, target, params, extensions):                                  

        # load the json with params, sanitise them, give it backad dict()
        p = self.load_sanitise_params(params)
        lst_action_source = p['source'].split(' ')
        action = lst_action_source[0]
        # get the rest of the action_source string (there can be more than 1 chunk):
        _source = p['source'][(len(action) + 1):]

        # It just happened that for Aegir, the target is also the alias
        drush_alias = target
        if action == 'clone':
            self.__site_create_clone(p, _source, target)
        elif action == 'install':
            self.__site_create_install(p, _source, target)
        else:
            raise Exception("Action not implemented: %s" % action)

        # code we need to run regardless of the create action taken:
        try:
            data = Builder.post_create_tasks(drush_alias, p)

        except SystemExit as e:
            raise Exception("Site %s create FAILED. Err: %s" % (target, str(e)))


        # extend
        if extensions:
            try:
                self.extend(extensions, drush_alias)
            except SystemExit as e:
                # NOT SURE what to do here is there is an error. Roll back the entire site?
                raise Exception("Site extensions for %s FAILED. Err: %s" % (drush_alias, str(e)))

        return data

    def __site_create_clone(self, p, clone_source, target):

        print("p: %s\nclone_source: %s\target: %s\n" % (p, clone_source, target))
        try:
            platform_line = run("grep @platform /var/aegir/.drush/%s.alias.drushrc.php" %
                    clone_source, pty=True, combine_stderr=True)
            m = re.search('@platform_(.+?)\'', platform_line)
            if m == None:
                raise Exception("Cannot find platform in alias file!")

            platform = m.group(1)
            run("drush @%s provision-clone @%s" % (clone_source, target))
            run("drush @hostmaster hosting-task --force @platform_%s verify" % platform)

        except SystemExit as e:
            raise Exception("Cloning of site failed. Err: %s" % str(e))


    def __site_create_install(self, p, create_source, target):
        """installs site from a profile"""
        _lst_platform_profile = create_source.split(' ')
        if len(_lst_platform_profile) != 2:
            raise Exception("Wrong create_source param: %s" % create_source)
        (platform_alias, profile) = _lst_platform_profile

        try:
            run("drush provision-save @%s --context_type=site --uri=%s --platform=@%s --profile=%s --db_server=@server_localhost --client_name=admin" % (target, target, platform_alias, profile))
            run("drush @%s provision-install" % target)
            run("drush @hostmaster hosting-task --force @%s verify" % platform_alias)

        except SystemExit as e:
            raise Exception("Installation of site failed. Err: %s" % str(e))


    def site_destroy(self, site_id, target, params, extensions):
        try:
            # this doesn't work, see https://drupal.org/node/1341698
            # run("drush @%s provision-delete" % target)
            print("drush @hostmaster hosting-task @%s delete" % target)
            run("drush @hostmaster hosting-task @%s delete" % target)
        except SystemExit as e:
            raise Exception(str(e))

        # extend
        if extensions:
            drush_alias = target
            try:
                self.extend(extensions, drush_alias)
            except SystemExit as e:
                raise Exception("Site extensions for %s FAILED. Err: %s" % (drush_alias, str(e)))



class Pantheon(Builder):
    def __init__(self, provider):
        pvd = json.loads(provider)
        if 'host_string' not in pvd:
            raise Exception("Pantheon builder needs host_string parameter in the provider (e.g. pantheon1@example.com).")
        
        env.shell = '/bin/bash -c'
        env.host_string = pvd['host_string']

    def site_create(self, site_id, target, params, extensions):                                  

        # load the json with params, sanitise them, give it backad dict()
        p = self.load_sanitise_params(params)

        # this could go to a simple function (to be shared from Aegir.site_create):
        # (action, source) = Builder.get_action_source(p)
        #
        lst_action_source = p['source'].split(' ')
        action = lst_action_source[0]
        # get the rest of the action_source string (there can be more than 1 chunk):
        _source = p['source'][(len(action) + 1):]

        drush_alias = None
        name = target.split('.')[0]
        drush_alias = 'pantheon.' + name + '.dev'
        if action == 'import':
            self.__site_create_import(name, _source)

        elif action == 'install':
            self.__site_create_install(name, _source, drush_alias)

        elif action == 'restore':
            raise Exception("Site restore not yet implemented")
        else:
            raise Exception("Action not implemented: %s" % action)

        try:
            data = Builder.post_create_tasks(drush_alias, p)
        except SystemExit as e:
            raise Exception("Site %s create FAILED. Err: %s" % (target, str(e)))


        # extend
        if extensions:
            try:
                self.extend(extensions, drush_alias)
            except SystemExit as e:
                # NOT SURE what to do here is there is an error. Roll back the entire site?
                raise Exception("Site extensions for %s FAILED. Err: %s" % (drush_alias, str(e)))

        return data

    def __site_create_import(self, name, source_archive):
        """Create a Pantheon site, importing it for a drush archive."""
        try:
            debug_run("bin/pinit")
            # yes, we are using the same label as the site name. label is actually
            # a mandatory parameter.
            # Full path to drush to avoid running a drush wrapper:
            debug_run("/usr/bin/drush psite-import --nopoll --label=%s %s %s" % (name, name, source_archive))
            debug_run("drush paliases")

            self.__wait_for_job_success(name, 'import_site_dev', delay=30, tries=36, loop_sleep=5)
        except SystemExit as e:
            raise Exception("Site import failed. Err: %s" % str(e))

    def __site_create_install(self, name, product_profile, drush_alias):
        """Create a Pantheon site, based on product ID."""
        (product, inst_profile) = product_profile.split(' ')
        try:
            # example: drush psite-create $SITE_NAME --label="$SITE_DESC" --product=21e1fada-199c-492b-97bd-0b36b53a9da0
            debug_run("bin/pinit")
            # Full path to drush to avoid the running a drush wrapper:
            debug_run("/usr/bin/drush psite-create %s --label='%s' --product=%s --nopoll" % (name, name, product))
            debug_run("drush paliases")
            self.__wait_for_job_success(name, 'create_site', delay=30, tries=36, loop_sleep=5)
            debug_run("drush -y @pantheon.%s.dev si --site-name='%s' %s" % (name, name, inst_profile))
        except SystemExit as e:
            raise Exception("Site create failed. Err: %s" % str(e))


    def __wait_for_job_success(self, name, jobname, delay = 30, tries = 36, loop_sleep = 5):
        """Waits for the jobname to finish, using terminus drush psite-jobs"""
        start = time.time()
        print("Waiting for %s seconds before starting polling." % delay)
        time.sleep(delay)
        try:
            uuid = run("drush psite-uuid %s --nocache" % name, pty=True, combine_stderr=True)
            for loop in range(1, tries+1):
                end = time.time()
                print("\n" + time.strftime("%d/%m/%Y %H:%M:%S"))
                print("Running psite-jobs for the %s time, it has been %d seconds so far." % (loop, end - start))
                # the below grep command requires terminal wider than 120 columns:
                job_line = run("drush psite-jobs %s | grep '%s' || :" % (uuid, jobname), 
                         pty=True, combine_stderr=True)
                m = re.search('SUCCESS', job_line)
                if m != None:
                    end = time.time()
                    print("We waited %d seconds and then needed %d loops, with %d second wait. Total elapsed time: %d seconds."
                        % (delay, loop, loop_sleep, end - start))
                    return
                time.sleep(loop_sleep)

        except SystemExit as e:
            raise Exception("Error while waiting for job to finish.Err: %s" % str(e))

        end = time.time()
        raise Exception("Site create didn't finish in time. Total elapsed time: %d seconds, max time %d seconds (%d + %d x %d)."
                % (end - start, tries * loop_sleep + delay, delay, tries, loop_sleep))



    def site_destroy(self, site_id, target, params, extensions):
        '''Destroy a pantheon site'''
        try:
            debug_run("bin/pinit")
            # We need to remove the domain from the FQDN passed in as target:
            name = target.split('.')[0]
            if not name:
                raise Exception("Wrong name to delete site")
            # carefull when debuggin delete:
            if name.find('marji') == -1 and name.find('sane') == -1:
                raise Exception("Deleting a non-test site disabled: %s" % name)
            run("drush psite-delete %s --yes" % name)
        except SystemExit as e:
            raise Exception(str(e))

        # extend
        if extensions:
            drush_alias = target
            try:
                self.extend(extensions, drush_alias)
            except SystemExit as e:
                raise Exception("Site extensions for %s FAILED. Err: %s" % (drush_alias, str(e)))
