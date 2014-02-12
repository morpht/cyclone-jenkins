# Cyclone Jenkins

This project is the Jenkins backend part of the [Drupal Cyclone module](https://drupal.org/project/cyclone).
It provisions (and deletes) Drupal websites. Currently supported hosting platforms are: [Aegir](http://community.aegirproject.org/) and [Pantheon](https://www.getpantheon.com/).

## Supported methods
These are the methods currently supported.

### Aegir
- `site_create clone` < src_site > < new_site >
- `site_create install` < platform_alias > < installation_profile > < new_site >
- `site_destroy` < site >

### Pantheon
- `site_create import` < drush_achive_url > < new_site >
- `site_create install` < pantheon_product_id > < installation_profile > < new_site >
- (in development) `site_create clone` < src_site > < new_site >
- `site_destroy` < site >
 

## Project setup

1. Install [Jenkins](http://jenkins-ci.org/) on a Linux server.
2. [Secure Jenkins](https://wiki.jenkins-ci.org/display/JENKINS/Securing+Jenkins) (e.g. use jenkins authentication, Apache proxy / HTTPS off-loader with basic auth, firewall).
3. Clone this code repository to the Jenkins server.
4. Create a jenkins job (details below), which executes the "cyclone.sh" wrapper in the root of the repo.
5. Generate a ssh key pair for the jenkins user and place the public key to the aegir or pantheon account you use.

### The jenkins job
1. Create a new job, select the "Build a free-style software project".
2. Name it (Project name): "cyclone-jenkins".
3. Select "This build is parameterized" and add the following parameters:
 - type
 - method
 - site_id
 - token
 - target
 - provider
 - params
 - extensions
 - notify_url
4. Under "Build", select "Add build step" - Execute shell and fill in:  
`your-path-to-the-repo-root/cyclone.sh`

## Connecting to your Hosted platform 
We currently support two drupal hosting platforms: [Aegir](http://community.aegirproject.org/) and [Pantheon](https://www.getpantheon.com/) (please [let us know](http://morpht.com/contact) if you would like us to add another platform).

### Disclaimer
Your jenkins user will be able to provision (and delete!) sites on your hosting platforms. That means everybody who can reach your jenkins server can potentially provision, delete and access your sites, including their code and data.
We recommend securing Jenkins very well. Even properly secured system can get compromised.
If your jenkins and/or your hosting server(s) get abused or compromised, you have been warned - it is YOUR responsibility. 

The steps below will guide you to provide your hosting platform credentials - proceed at your own risk.  

### Aegir
Copy the content of the jenkins' public ssh key to the authorized_key file of the aegir user on your Aegir server.
Become the jenkins user on your Jenkins server and open the fist ssh connection to the aegir user on the Aegir server, to verify it works and to add the server to the "known hosts".

### Pantheon
Set up a new user account on a linux server. It can be your jenkins server or a different one.
For example `pantheon-joe`.

Under this `pantheon-joe` account:

1. Install [drush](https://drupal.org/project/drush) / make sure it is available to this user.
2. Install [terminus](https://github.com/pantheon-systems/terminus), the Pantheon CLI.
3. Create a bin directory under the pantheon-joe user. We will create a script to authenticate against Pantheon:

        mkdir bin
        touch bin/pinit
        chmod 700 bin/pinit
        echo "drush pauth <your pantheon email addressl> --password=<your pantheon password>"

4. Create a ssh key pair.
5. Upload the public ssh key to your Pantheon hosting.
6. Configure ssh to allow connections to unknown hosts:  
`echo "StrictHostKeyChecking no" > .ssh/config`
7. Verify that you can authenticate against your Pantheon hosting:  
    `bin/pinit`  
    you want to see something like:

        Authenticating as joe@example.com      [ok]
        Success!                               [ok]

8. Set terminal to 140 columns in .bashrc.

## Credits
This project was developed by [Morpht](http://morpht.com/), a Drupal services company, http://morpht.com.
